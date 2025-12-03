#lescript.py

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
import json

load_dotenv()

#Formats de prompt
class BaseDonneeReponse(BaseModel):
    procedeCreationEnSQL: str
    message: str
    nomBD: str
    nombreTables: int
    tablesParNom: list[str]
    #Les tables auront un nom ainsi qu'une liste de colonnes avec leur nom et le type de valeur, donc il faut un tuple
    #Cette source m'a aidé à imaginer les tuples et à les formatter: https://typing.python.org/en/latest/spec/tuples.html
    #DONC! Nos tables sont représentées par une liste, qui est composé de plusieurs données par enregistrement:
        #Le nom de la table
        #Une liste de colonnes par nom et type de données de la colonne (décrite en string)
        #^ pour chaque table de la BD ^
    tables: list[tuple[str, list[tuple[str, str]]]]
    scriptCreationBDEtTablesSQL: str
    listeColonnesAvecTypesDesTables: list[list[str]]

class GuidePromptReponse(BaseModel): 
    requeteSQL: str
    explication: str
    suggestionAmelioration: str

class VerificationRequeteReponse(BaseModel):
    requete_fonctionne: bool
    explications_derriere_correction: str
    ameliorations_possibles: str
    


llm = ChatAnthropic(model="claude-3-5-haiku-latest")
parserBD = PydanticOutputParser(pydantic_object=BaseDonneeReponse)
parserPrompt = PydanticOutputParser(pydantic_object=GuidePromptReponse)
parserVerification = PydanticOutputParser(pydantic_object=VerificationRequeteReponse)


#Source pour le formattage de ChatPromptTemplate: https://python.langchain.com/api_reference/core/prompts/langchain_core.prompts.chat.ChatPromptTemplate.html
promptBD = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                Vous êtes un assistant de gestion de base de données MYSQL venant en aide à un utilisateur dans le besoin.
                Lorsque vous répondez à la requête de l'utilisateur, je vous prie de répondre avec le format ci-dessous,
                le message étant une description courte de la base de donnée s'il y a lieu, sans autre texte hormis ce qui est inscrit dans le format, tout en respectant le type des variables montré dans le format dans ta réponse.
                Voici le format:\n{format_instructions}\n
                Il est important que la variable représentant les tables soit formattée de façon similaire à ceci: [['Livres', [['Titre', 'VARCHAR(100)'], ['auteur', 'VARCHAR(100)']]], ['Employe', [['nom', 'VARCHAR(100)']]]].
                Il est aussi important que la variable contenant le script de création de la BD et de ses tables soit complet pour être recopié plus tard dans un fichier SQL.
            """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}")
    ]
).partial(format_instructions=parserBD.get_format_instructions())


promptContreAnalyse = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                Vous êtes un analyste utilisant une base de données de test afin de vous assurer que la requête de votre client fonctionne sans soucis.
                Vous avez accès à la structure de la base de données grâce au client, mais vous devrez faire les tests en imaginant des données dans celle-ci.
                Voici le format dans lequel vous devrez répondre au client:\n{format_instructions}
            """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "Voici ma requête SQL: \n{requete}\n, ainsi que ma base de données dans un format lisible: \n{formatBD}"),
        ("placeholder", "{agent_scratchpad}")
    ]
).partial(format_instructions=parserPrompt.get_format_instructions())

promptRequete = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                Vous êtes un assistant de gestion de base de données MYSQL venant en aide à un utilisateur souhaitant faire une requête.
                Le raisonnement est votre train de pensée derrière la requête que vous proposerez à l'utilisateur.
                Lorsque vous répondez à la requête de l'utilisateur, faites-le avec ce format:\n{format_instructions}
            """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}")
    ]
).partial(format_instructions=parserPrompt.get_format_instructions())



compteurG = 0
#Fonction qui crée une table selon le nom de la BD donné par l'utilisateur.
#Peut prendre un tuple représentant une table d'exemple pour la base de données
#Source pour les arguments optionels: https://www.geeksforgeeks.org/python/how-to-pass-optional-parameters-to-a-function-in-python
def creation_table(
        nomBD
):
    #Adapter l'agent à la méthode présente
    agent = create_tool_calling_agent(
        llm = llm,
        prompt=promptBD,
        tools = []
    )
    agent_executor = AgentExecutor(agent=agent, tools = [], verbose=True)

    reponseBrute = agent_executor.invoke(
        {
            "query": f"""
            Je veux créer une base de donnée du nom de '{nomBD}' et que tu m'en donne un exemple en structure écrite et bien indentée pour ce qui est des tables.
            Cela dit, tu peux lier les tables avec des clés étrangères si tu juge cela nécessaire.
            """
        }
    )
    #La réponse est dans la catégorie "output", et le format qu'on a choisi est dans le premier espace, dans le "text".
    reponseIA = reponseBrute.get("output")[0]["text"]
    donneesReponse = ""
    global compteurG #Déclarer que c'est une variable hors de la fonction. Source: https://realpython.com/python-use-global-variable-in-function/#:~:text=Inside%20a%20function%2C%20you%20can,creating%20a%20new%20local%20one.
    try:
        donneesReponse = json.loads(reponseIA)
        tables = ""
        tablesBD = donneesReponse["tables"]
        #print(f"{tablesBD}") Ceci réparait un bug qui avait rapport avec le for
        nombreTables = f"{donneesReponse["nombreTables"]}"
        tablesParNom = donneesReponse["tablesParNom"]
        tablesEnSQL = donneesReponse["scriptCreationBDEtTablesSQL"]
        for nom, colonnes in tablesBD:
            tables += "Table: " + nom + "\n"
            tables += "Colonnes: \n"
            for nom_colonne, type_colonne in colonnes:
                tables += f"Nom: {nom_colonne} | Type: {type_colonne}\n"
            tables+= "\n"
        nomBD = f"{donneesReponse["nomBD"]}"
    except ValueError:
        compteurG +=1
        if (compteurG <5):
            return creation_table(nomBD)
        else:
            #On va s'arranger pour que l'usager comprenne ce qu'il se passe
            return ["Erreur ", "Veuillez relancer la page (F5) ou demander au développeur de vérifier la réponse de l'IA.", "0", "", "Le programme a eu une erreur."]
    except UnboundLocalError:
        compteurG +=1
        if (compteurG <5):
            return creation_table(nomBD)
        else:
            #On va s'arranger pour que l'usager comprenne ce qu'il se passe
            return ["Erreur", "Veuillez relancer la page (F5) ou demander au développeur de vérifier la réponse de l'IA.", "0", "", "Le programme a eu une erreur."]
    
    if (donneesReponse == ""): #Juste au cas où d'une manière ou une autre, il réussise à continuer après le except.
        if (compteurG <5):
            return creation_table(nomBD)
        else:
            #On va s'arranger pour que l'usager comprenne ce qu'il se passe
            return ["Erreur ", "Veuillez relancer la page (F5) ou demander au développeur de vérifier la réponse de l'IA.", "0", "", "Le programme a eu une erreur."]
    print(compteurG) #Pour voir le nombre d'erreur 
    compteurG = 0
    #C'est pas mal toutes les mêmes types de valeurs, donc ce serait plus facile si on retourne un tableau!
    return [nomBD, tables, nombreTables, tablesParNom, tablesEnSQL] #tablesParNom pourrait permettre de sélectionner une table dans le formulaire jsp


def faire_requete_bd(
        typeRequete,
        nomTable,
        tablesBD,
        donnees
):
    
    #Adapter l'agent à la méthode utilisée
    agent = create_tool_calling_agent(
        llm=llm,
        prompt=promptRequete,
        tools=[]
    )
    agent_executor= AgentExecutor(agent=agent, tools=[], verbose=True)
    if typeRequete == "ajout d'une table":
        reponseBrute = agent_executor.invoke({
            "query": f"""
            Voici ce que j'aimerais faire dans ma base de données: \n{typeRequete}.
            \nJe veux que tu prenne en compte de ma base de données ci-dessous:
            \n {tablesBD}\n 
            Je veux donc que tu 'traduise' ce que je souhaite faire en requête MySQL, puis que tu m'explique chaque étape de la requête.
            Voici les données de l'ajout de table (par nom de colonne et type). Si certaines données manquent de clarification, je t'invite à les inventer et à en informer brièvement l'utilisateur dans l'explication.
            """
        })
    elif typeRequete == "suppression d'une table":
        reponseBrute = agent_executor.invoke({
            "query": f"""
            Voici ce que j'aimerais faire dans ma base de données: \n{typeRequete}. Voici le nom de la table à supprimer: {nomTable}
            \nJe veux que tu prenne en compte de ma base de données ci-dessous:
            \n {tablesBD}\n Tu peux inventer un enregistrement dans la table avec l'identifiant correspondant.
            Je veux donc que tu 'traduise' ce que je souhaite faire en requête MySQL, puis que tu m'explique chaque étape de la requête.
            """
        })
    else:
        reponseBrute = agent_executor.invoke({
            "query": f"""
            Voici ce que j'aimerais faire dans ma table: \n{typeRequete}. Ma table s'appelle {nomTable}. Les informations de la base de données vont suivre.
            \nJe veux que tu prenne en compte de ma base de données ci-dessous:
            \n {tablesBD}\n 
            Je veux donc que tu 'traduise' ce que je souhaite faire en requête MySQL, puis que tu m'explique chaque étape de la requête.
            Voici les données associées à la requête. Voici les données par nom de colonne et valeur: \n{donnees}\n Si certaines données manquent, aviser l'utilisateur dans l'explication et inventer des valeurs pour celles-ci.
            """
        })

    reponseIA = reponseBrute.get("output")[0]["text"]
    donneesReponses = json.loads(reponseIA)
    laRequete = donneesReponses["requeteSQL"]
    raisonnementDerriere = donneesReponses["explication"]
    ameliorationsPossibles = donneesReponses["suggestionAmelioration"]
    return [laRequete, raisonnementDerriere, ameliorationsPossibles]
    
    


# Fonction qui prends les paramètres pour le contexte dans lequel la requête n'a pas fonctionné.
# Retourne les paramètres structures de l'IA qui va corriger la requête selon ce qu'elle a vu.
def verification_bd(
        requete,
        nomBD,
        tablesBD
):
    #Adapter l'agent à la méthode présente
    agent = create_tool_calling_agent(
        llm = llm,
        prompt=promptContreAnalyse,
        tools = []
    )
    agent_executor = AgentExecutor(agent=agent, tools = [], verbose=True)
    reponseBrute = agent_executor.invoke({
        "query", f"""
        Je veux que tu contre-vérifie cette requête (t'assurer qu'elle fonctionne comme voulu selon le contexte):\n {requete}\n
        et que tu me la corrige. C'est une requête dans ma base de donnée du nom de: {nomBD}. Voici ses tables formattées en texte: \n{tablesBD}
        """
    })
    reponseIA = reponseBrute.get("output")[0]["text"]
    donneesReponses = json.loads(reponseIA)
    requeteCorrigee = donneesReponses["requete"]
    raisonnement = donneesReponses["explications_derriere_correction"]
    autresOptions = donneesReponses["ameliorations_possibles"]
    return [requeteCorrigee, raisonnement, autresOptions]

def exporter_bd(
        nomBD,
        tablesBD
):
    agent= create_tool_calling_agent(
        llm=llm,
        prompt=promptBD, #À CORRIGER DÈS QUE POSSIBLE
        tools = []
    )

