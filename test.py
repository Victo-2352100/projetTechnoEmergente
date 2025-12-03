from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
import json

load_dotenv()
    

class BaseDonneeReponse(BaseModel):
    procede_creation: str
    message: str
    nomBD: str
    nombreTables: int
    tablesParNom: list[str]
    #Les tables auront un nom ainsi qu'une liste de colonnes avec leur nom et le type de valeur, donc il faut un tuple
    #Cette source m'a aidé à imaginer les tuples et à les formatter: https://typing.python.org/en/latest/spec/tuples.html
    #DONC! Nos tables sont représentées par une liste, qui est composé de plusieurs données par enregistrement:
        #Le nom de la table
        #Une liste de colonnes par nom et type de données de la colonne (décrite en string)
    tables: list[tuple[str, list[tuple[str, str]]]]

llm = ChatAnthropic(model="claude-3-5-haiku-latest")
parserBD = PydanticOutputParser(pydantic_object=BaseDonneeReponse)

promptBD = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                Vous êtes un assistant de gestion de base de données MYSQL venant en aide à un utilisateur dans le besoin.
                Lorsque vous répondez à la requête de l'utilisateur, je vous prie de répondre avec le format ci-dessous,
                le message étant une description courte de la base de donnée s'il y a lieu, sans autre texte hormis ce qui est inscrit dans le format.
                Voici le format:\n{format_instructions}
            """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}")
    ]
).partial(format_instructions=parserBD.get_format_instructions())



agent = create_tool_calling_agent(
    llm=llm,
    prompt=promptBD,
    tools=[]
)
variable = "prison" #Selon le test ici, agent_executor.invoke() peut prendre un

agent_executor = AgentExecutor(agent=agent, tools = [], verbose=True)
reponse_pre = agent_executor.invoke(
    {
        "query": f"""
                    Je veux créer une base de donnée du nom de '{variable}' et que tu imagine une base de donnée très simple à partir de ce nom.
                    La sections tables contient plusieurs tables avec plusieurs colonnes, qui ont des noms et des types de variables
                """
    }
)
#Pour avoir la référence de la réponse de l'IA que je veux utiliser
tableau_tables_pre = reponse_pre.get("output")[0]["text"]
#Source: https://www.geeksforgeeks.org/python/json-loads-in-python pour permettre de décoder un tableau de JSON en python
#Pouvoir "déballer" le giga tableau JSON qu'est tableau_tables_pre
donnesRaffinees = json.loads(tableau_tables_pre)
#Ici c'est pour avoir mes tables
tables_pre = donnesRaffinees["tables"] #Me retourne juste une table.
tables = ""
print (tables_pre)
#Boucle for pour filtrer les tables en un string pour l'affichage!
for nom, colonnes in tables_pre:
    tables += "Table: " + nom + "\n"
    tables += "Colonnes: \n"
    for nom_colonne, type_colonne in colonnes:
        tables += f"Nom: {nom_colonne} | Type: {type_colonne}\n"
    tables+= "\n"

print(tables)

