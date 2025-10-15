import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, send_from_directory
from flask_session import Session
import gspread
from google.oauth2 import service_account

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__, static_folder='client')

# Configuration des sessions
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "default_secret_key_for_development")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # Session d'une heure
Session(app)

# Configuration des colonnes de la Google Sheet
SHEET_COLUMNS = {
    "NAME": 0,        # Nom
    "FIRSTNAME": 1,   # Prénom
    "YEAR": 2,        # Année
    "NICKNAME": 3,    # Surnom du tueur
    "PASSWORD": 4,    # Mot de passe
    "TARGET": 5,      # Surnom de sa cible
    "ACTION": 6,      # Action à réaliser
    "STATUS": 7       # État (ajouté pour la gestion alive/dead)
}

# Connexion à l'API Google Sheets
def get_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json"),
        scopes=scope
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(os.environ.get("SHEET_ID")).sheet1
    return sheet

# Fonction pour initialiser la colonne "État" si elle n'existe pas
def initialize_status_column():
    try:
        sheet = get_sheet_client()
        headers = sheet.row_values(1)
        
        # Vérifier si la colonne STATUS existe déjà
        if len(headers) <= SHEET_COLUMNS["STATUS"]:
            # Ajouter l'en-tête de colonne
            sheet.update_cell(1, SHEET_COLUMNS["STATUS"] + 1, "État")
            
            # Initialiser tous les joueurs comme "alive"
            data = sheet.get_all_values()
            for i in range(1, len(data)):  # Commencer à la deuxième ligne (après les en-têtes)
                sheet.update_cell(i + 1, SHEET_COLUMNS["STATUS"] + 1, "alive")
            
            print("Colonne 'État' initialisée avec succès")
        else:
            print("La colonne 'État' existe déjà")
            
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la colonne État: {e}")

# Appeler l'initialisation au démarrage
initialize_status_column()

# Fonction auxiliaire pour obtenir les données d'un joueur par son surnom
def get_player_by_nickname(nickname):
    sheet = get_sheet_client()
    data = sheet.get_all_values()
    
    # Ignorer la ligne d'en-tête
    for i, row in enumerate(data[1:], 2):
        if row[SHEET_COLUMNS["NICKNAME"]] == nickname:
            player = {
                "row": i,
                "name": row[SHEET_COLUMNS["NAME"]],
                "firstname": row[SHEET_COLUMNS["FIRSTNAME"]],
                "year": row[SHEET_COLUMNS["YEAR"]],
                "nickname": row[SHEET_COLUMNS["NICKNAME"]],
                "password": row[SHEET_COLUMNS["PASSWORD"]],
                "target": row[SHEET_COLUMNS["TARGET"]],
                "action": row[SHEET_COLUMNS["ACTION"]],
                "status": row[SHEET_COLUMNS["STATUS"]] if len(row) > SHEET_COLUMNS["STATUS"] else "alive"
            }
            return player
    
    return None

# Fonction pour obtenir la cible d'un joueur
def get_target_info(target_nickname):
    return get_player_by_nickname(target_nickname)

# Fonction récursive pour trouver la prochaine cible vivante
def find_next_alive_target(nickname, visited=None):
    if visited is None:
        visited = []
    
    if nickname in visited:
        # Circuit détecté, aucun joueur vivant trouvé
        return None
    
    visited.append(nickname)
    player = get_player_by_nickname(nickname)
    
    if not player or not player["target"]:
        return None
    
    target = get_player_by_nickname(player["target"])
    
    if not target:
        return None
    
    if target["status"].lower() == "alive":
        return target
    
    # Si la cible est morte, chercher la cible de cette cible
    return find_next_alive_target(target["target"], visited)

# Routes pour servir les fichiers statiques
@app.route("/")
def index():
    return send_from_directory('client', 'index.html')

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory('client', path)

# API Endpoints
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    nickname = data.get("nickname")
    password = data.get("password")
    
    if not nickname or not password:
        return jsonify({"success": False, "message": "Surnom et mot de passe requis"}), 400
    
    player = get_player_by_nickname(nickname)
    
    if not player:
        return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
    
    if player["password"] != password:
        return jsonify({"success": False, "message": "Mot de passe incorrect"}), 401
    
    # Stocker l'ID du joueur dans la session
    session["nickname"] = nickname
    
    # Récupérer les informations de la cible
    target_info = None
    if player["target"]:
        target = get_player_by_nickname(player["target"])
        
        # Si la cible est morte, trouver la prochaine cible vivante
        if target and target["status"].lower() == "dead":
            next_target = find_next_alive_target(player["target"])
            
            if next_target:
                # Mettre à jour la cible dans la feuille
                sheet = get_sheet_client()
                sheet.update_cell(player["row"], SHEET_COLUMNS["TARGET"] + 1, next_target["nickname"])
                sheet.update_cell(player["row"], SHEET_COLUMNS["ACTION"] + 1, next_target["action"])
                
                # Mettre à jour l'info du joueur
                player["target"] = next_target["nickname"]
                player["action"] = next_target["action"]
                
                target = next_target
            else:
                target = None
        
        if target:
            target_info = {
                "name": target["name"],
                "firstname": target["firstname"],
                "year": target["year"],
                "nickname": target["nickname"],
                "action": player["action"]  # L'action à réaliser est stockée dans la ligne du joueur
            }
    
    # Préparer la réponse avec le profil du joueur et sa cible
    response = {
        "success": True,
        "player": {
            "name": player["name"],
            "firstname": player["firstname"],
            "year": player["year"],
            "nickname": player["nickname"]
        },
        "target": target_info
    }
    
    return jsonify(response)

@app.route("/api/me", methods=["GET"])
def get_me():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    
    player = get_player_by_nickname(session["nickname"])
    
    if not player:
        # Cas où le joueur a été supprimé pendant la session
        session.clear()
        return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
    
    # Récupérer les informations de la cible
    target_info = None
    if player["target"]:
        target = get_player_by_nickname(player["target"])
        
        # Si la cible est morte, trouver la prochaine cible vivante
        if target and target["status"].lower() == "dead":
            next_target = find_next_alive_target(player["target"])
            
            if next_target:
                # Mettre à jour la cible dans la feuille
                sheet = get_sheet_client()
                sheet.update_cell(player["row"], SHEET_COLUMNS["TARGET"] + 1, next_target["nickname"])
                sheet.update_cell(player["row"], SHEET_COLUMNS["ACTION"] + 1, next_target["action"])
                
                # Mettre à jour l'info du joueur
                player["target"] = next_target["nickname"]
                player["action"] = next_target["action"]
                
                target = next_target
            else:
                target = None
        
        if target:
            target_info = {
                "name": target["name"],
                "firstname": target["firstname"],
                "year": target["year"],
                "nickname": target["nickname"],
                "action": player["action"]  # L'action à réaliser est stockée dans la ligne du joueur
            }
    
    # Préparer la réponse avec le profil du joueur et sa cible
    response = {
        "success": True,
        "player": {
            "name": player["name"],
            "firstname": player["firstname"],
            "year": player["year"],
            "nickname": player["nickname"]
        },
        "target": target_info
    }
    
    return jsonify(response)

@app.route("/api/kill", methods=["POST"])
def kill():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    
    sheet = get_sheet_client()
    
    try:
        # Récupérer le joueur (killer)
        killer = get_player_by_nickname(session["nickname"])
        
        if not killer:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
        
        if not killer["target"]:
            return jsonify({"success": False, "message": "Vous n'avez pas de cible active"}), 400
        
        # Récupérer la victime
        victim = get_player_by_nickname(killer["target"])
        
        if not victim:
            return jsonify({"success": False, "message": "Cible non trouvée"}), 404
        
        if victim["status"].lower() == "dead":
            return jsonify({"success": False, "message": "Cette cible est déjà morte"}), 400
        
        # Récupérer la cible de la victime (nouvelle cible du killer)
        next_target_nickname = victim["target"]
        next_target_action = victim["action"]
        
        # Si la prochaine cible est déjà morte, trouver la prochaine cible vivante
        next_target = get_player_by_nickname(next_target_nickname)
        
        if next_target and next_target["status"].lower() == "dead":
            alive_target = find_next_alive_target(next_target_nickname)
            
            if alive_target:
                next_target_nickname = alive_target["nickname"]
                next_target_action = alive_target["action"]
            else:
                # Aucune cible vivante trouvée, fin du jeu possible
                next_target_nickname = ""
                next_target_action = ""
        
        # 1. Mettre à jour le killer avec la nouvelle cible
        sheet.update_cell(killer["row"], SHEET_COLUMNS["TARGET"] + 1, next_target_nickname)
        sheet.update_cell(killer["row"], SHEET_COLUMNS["ACTION"] + 1, next_target_action)
        
        # 2. Marquer la victime comme morte et supprimer sa cible
        sheet.update_cell(victim["row"], SHEET_COLUMNS["STATUS"] + 1, "dead")
        sheet.update_cell(victim["row"], SHEET_COLUMNS["TARGET"] + 1, "")
        sheet.update_cell(victim["row"], SHEET_COLUMNS["ACTION"] + 1, "")
        
        # Récupérer les infos de la nouvelle cible pour la réponse
        new_target_info = None
        if next_target_nickname:
            new_target = get_player_by_nickname(next_target_nickname)
            if new_target:
                new_target_info = {
                    "name": new_target["name"],
                    "firstname": new_target["firstname"],
                    "year": new_target["year"],
                    "nickname": new_target["nickname"],
                    "action": next_target_action
                }
        
        response = {
            "success": True,
            "message": "Cible tuée avec succès",
            "target": new_target_info
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Erreur lors du kill: {e}")
        return jsonify({"success": False, "message": f"Erreur lors du kill: {str(e)}"}), 500

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Déconnecté avec succès"})

@app.route("/api/debug", methods=["GET"])
def debug():
    # Endpoint de débogage - à commenter ou protéger en production
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    
    try:
        sheet = get_sheet_client()
        data = sheet.get_all_values()
        
        # Convertir les données en format plus lisible
        headers = data[0]
        result = []
        
        for row in data[1:]:
            player = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    player[header] = row[i]
            result.append(player)
        
        return jsonify({"success": True, "data": result})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
