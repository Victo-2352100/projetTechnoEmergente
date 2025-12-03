from lescript import creation_table, verification_bd
from flask import Flask, render_template, request, url_for, redirect
from lescript import creation_table, faire_requete_bd, verification_bd
app = Flask(__name__)
#Source pour la gestion de l'interface: https://bd2.profinfo.ca/python/flask/#execution-de-lapplication
# Merci Étienne!

tables = ()

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        #À noter que c'est le name qui est important ici, et non l'ID
        nomdeBD = request.form['nomBD']
        return redirect(url_for('gererBD', nomBD=nomdeBD))
    return render_template("index.html")

@app.route('/gererBD/<nomBD>', methods=['GET','POST'])
def gererBD(nomBD):
    #Il réussit à changer de route
    valeurs = creation_table(nomBD=nomBD)
    nomDeBD = valeurs[0]
    tablesBD = valeurs[1]
    nombresTables = valeurs[2]
    tablesParNoms = valeurs[3]
    tablesEnSQL = valeurs[4]
    if (nomBD != "Erreur" and int(nombresTables) > 0 and tablesParNoms != ""): #Ici, je traque l'input particulier que j'ai mis à ma fonction en cas d'erreur grave.
        return render_template('gererBD.html', nomBD = nomDeBD, tablesDeBD = tablesBD, nbrTables=nombresTables, nomsTables=tablesParNoms, tablesSQL=tablesEnSQL)
    else:
        return render_template('erreurGenerationBD.html')
        

@app.route('/requete/donnees', methods=['GET', 'POST'])
def requeteDonneesBD():
    if request.method == 'POST':
        tablesDeBD = request.form.get("tablesBD")
        typeRequete = request.form.get("typeRequete")
        tableChoisie = request.form.get("tableChoisie")
        nomsVariables = request.form.getlist("variable[]")
        valeursVariables = request.form.getlist("valeur[]")
        donnee = dict(zip(nomsVariables, valeursVariables))
        faire_requete_bd(typeRequete=typeRequete, nomTable=tableChoisie, tablesBD=tablesDeBD, donnees=donnee)

@app.route('/requete/tables', methods=['GET', 'POST'])
def requeteTablesBD():
    if request.method == 'POST':
        tableChoisie = request.form.get("tableChoisie")
        return render_template("reponseRequete.html")
    else:
        return render_template('erreurGenerationBD.html')
    

if __name__ == '__main__':
    app.run(debug=True)