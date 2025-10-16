import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, send_from_directory
from flask_session import Session
import gspread
from google.oauth2 import service_account

# Charger les variables d'environnement
load_dotenv()
print("Environnement chargé:")
print(f"SERVICE_ACCOUNT_FILE: {os.environ.get('SERVICE_ACCOUNT_FILE')}")
print(f"SHEET_ID: {os.environ.get('SHEET_ID')}")

app = Flask(__name__, static_folder='client')

# Configuration des sessions
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "default_secret_key_for_development")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # Session d'une heure
Session(app)

# Configuration des colonnes de la Google Sheet
SHEET_COLUMNS = {
    "TIMESTAMP": 0,   # Horodateur
    "NICKNAME": 1,    # Surnom (le VRAI, pour pouvoir vous identifier)
    "PASSWORD": 2,    # Votre mot de passe
    "PERSON_PHOTO": 3,# Une photo de vous neuillesque
    "FEET_PHOTO": 4,  # une photo de vos pieds
    "KRO_ANSWER": 5,  # Combien y a t il de cars dans une kro ?
    "BEFORE_ANSWER": 6, # Est-ce que c'était mieux avant ?
    "MESSAGE_ANSWER": 7, # Un petit mot pour vos brasseurs adorés
    "CHALLENGE_IDEAS": 8, # Idées de défis
    "INITIAL_TARGET": 9,  # Cible initiale
    "CURRENT_TARGET": 10, # Cible actuelle
    "INITIAL_ACTION": 11, # Action initiale
    "CURRENT_ACTION": 12, # Action actuelle
    "STATUS": 13      # État (alive/dead/gaveup)
}

# Connexion à l'API Google Sheets
def get_sheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
        
        if not os.path.exists(service_account_file):
            if os.path.exists("service_account_example.json"):
                raise FileNotFoundError(
                    f"Le fichier {service_account_file} est introuvable. "
                    f"Veuillez copier service_account_example.json vers {service_account_file} "
                    f"et remplir avec vos informations d'identification Google."
                )
            else:
                raise FileNotFoundError(
                    f"Le fichier {service_account_file} est introuvable. "
                    f"Veuillez créer ce fichier avec vos informations d'identification Google."
                )
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=scope
        )
        client = gspread.authorize(credentials)
        sheet_id = os.environ.get("SHEET_ID")
        if not sheet_id:
            print("AVERTISSEMENT: SHEET_ID manquant dans les variables d'environnement.")
            print("Tentative d'utilisation du premier spreadsheet disponible...")
            try:
                # Try to use the first spreadsheet if SHEET_ID is not provided
                sheet = client.open("Killer Game").sheet1  # Use a default name or try to list spreadsheets
                print(f"Utilisation du spreadsheet: {sheet.spreadsheet.title}")
                return sheet
            except Exception as sheet_error:
                available_sheets = [s.title for s in client.openall()]
                if available_sheets:
                    print(f"Spreadsheets disponibles: {', '.join(available_sheets)}")
                    raise ValueError(f"SHEET_ID manquant. Veuillez spécifier l'un des spreadsheets disponibles: {', '.join(available_sheets)}")
                else:
                    raise ValueError("SHEET_ID manquant dans les variables d'environnement et aucun spreadsheet n'est disponible.")
        try:
            sheet = client.open_by_key(sheet_id).sheet1
            return sheet
        except Exception as sheet_error:
            raise ValueError(f"Erreur lors de l'ouverture du spreadsheet: {str(sheet_error)}. Vérifiez que l'ID est correct et que le service account a les permissions nécessaires.")
    except Exception as e:
        import traceback
        error_msg = str(e)
        
        if "APIError" in error_msg and ("API has not been used" in error_msg or "is disabled" in error_msg):
            print("\n=== ERREUR D'API GOOGLE SHEETS ===")
            print("L'API Google Sheets n'est pas activée pour ce projet.")
            print("1. Allez sur Google Cloud Console: https://console.cloud.google.com/apis/library")
            print("2. Sélectionnez votre projet")
            print("3. Recherchez et activez 'Google Sheets API'")
            print("4. Attendez quelques minutes pour que l'activation soit prise en compte")
            print("===================================\n")
            raise ValueError("L'API Google Sheets n'est pas activée. Voir instructions dans la console.")
        else:
            print(f"Erreur lors de la connexion à Google Sheets: {error_msg}")
            print(f"Détails de l'erreur: {traceback.format_exc()}")
            raise
    except Exception as e:
        import traceback
        print(f"Erreur lors de la connexion à Google Sheets: {str(e)}")
        print(f"Détails de l'erreur: {traceback.format_exc()}")
        raise

# Fonction pour initialiser la colonne "État" si elle n'existe pas
def initialize_status_column():
    try:
        sheet = get_sheet_client()
        headers = sheet.row_values(1)
        
        # Vérifier si les colonnes nécessaires existent déjà
        # Initialisation des colonnes manquantes
        if len(headers) <= SHEET_COLUMNS["CURRENT_TARGET"]:
            sheet.update_cell(1, SHEET_COLUMNS["CURRENT_TARGET"] + 1, "Cible actuelle")
        
        if len(headers) <= SHEET_COLUMNS["CURRENT_ACTION"]:
            sheet.update_cell(1, SHEET_COLUMNS["CURRENT_ACTION"] + 1, "Action actuelle")
            
        if len(headers) <= SHEET_COLUMNS["STATUS"]:
            sheet.update_cell(1, SHEET_COLUMNS["STATUS"] + 1, "État")
        
        # Vérifier si les données des joueurs doivent être initialisées
        data = sheet.get_all_values()
        for i in range(1, len(data)):  # Commencer à la deuxième ligne (après les en-têtes)
            row = data[i]
            
            # Initialiser la cible actuelle si elle est vide
            if len(row) <= SHEET_COLUMNS["CURRENT_TARGET"] or not row[SHEET_COLUMNS["CURRENT_TARGET"]]:
                if len(row) > SHEET_COLUMNS["INITIAL_TARGET"] and row[SHEET_COLUMNS["INITIAL_TARGET"]]:
                    sheet.update_cell(i + 1, SHEET_COLUMNS["CURRENT_TARGET"] + 1, row[SHEET_COLUMNS["INITIAL_TARGET"]])
            
            # Initialiser l'action actuelle si elle est vide
            if len(row) <= SHEET_COLUMNS["CURRENT_ACTION"] or not row[SHEET_COLUMNS["CURRENT_ACTION"]]:
                if len(row) > SHEET_COLUMNS["INITIAL_ACTION"] and row[SHEET_COLUMNS["INITIAL_ACTION"]]:
                    sheet.update_cell(i + 1, SHEET_COLUMNS["CURRENT_ACTION"] + 1, row[SHEET_COLUMNS["INITIAL_ACTION"]])
            
            # Initialiser l'état si vide
            if len(row) <= SHEET_COLUMNS["STATUS"] or not row[SHEET_COLUMNS["STATUS"]]:
                sheet.update_cell(i + 1, SHEET_COLUMNS["STATUS"] + 1, "alive")
        
        print("Colonnes et états initialisés avec succès")
            
    except ValueError as e:
        if "L'API Google Sheets n'est pas activée" in str(e):
            print(f"Erreur lors de l'initialisation de la colonne État: {e}")
        else:
            print(f"Erreur lors de l'initialisation de la colonne État: {e}")
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
        # Comparaison insensible à la casse pour le surnom
        if len(row) > SHEET_COLUMNS["NICKNAME"] and row[SHEET_COLUMNS["NICKNAME"]].lower() == nickname.lower():
            player = {
                "row": i,
                "nickname": row[SHEET_COLUMNS["NICKNAME"]],
                "password": row[SHEET_COLUMNS["PASSWORD"]] if len(row) > SHEET_COLUMNS["PASSWORD"] else "",
                "person_photo": extract_google_drive_id(row[SHEET_COLUMNS["PERSON_PHOTO"]]) if len(row) > SHEET_COLUMNS["PERSON_PHOTO"] else "",
                "feet_photo": extract_google_drive_id(row[SHEET_COLUMNS["FEET_PHOTO"]]) if len(row) > SHEET_COLUMNS["FEET_PHOTO"] else "",
                "kro_answer": row[SHEET_COLUMNS["KRO_ANSWER"]] if len(row) > SHEET_COLUMNS["KRO_ANSWER"] else "",
                "before_answer": row[SHEET_COLUMNS["BEFORE_ANSWER"]] if len(row) > SHEET_COLUMNS["BEFORE_ANSWER"] else "",
                "message": row[SHEET_COLUMNS["MESSAGE_ANSWER"]] if len(row) > SHEET_COLUMNS["MESSAGE_ANSWER"] else "",
                "challenge_ideas": row[SHEET_COLUMNS["CHALLENGE_IDEAS"]] if len(row) > SHEET_COLUMNS["CHALLENGE_IDEAS"] else "",
                "initial_target": row[SHEET_COLUMNS["INITIAL_TARGET"]] if len(row) > SHEET_COLUMNS["INITIAL_TARGET"] and row[SHEET_COLUMNS["INITIAL_TARGET"]] else "",
                "target": row[SHEET_COLUMNS["CURRENT_TARGET"]] if len(row) > SHEET_COLUMNS["CURRENT_TARGET"] and row[SHEET_COLUMNS["CURRENT_TARGET"]] else "",
                "initial_action": row[SHEET_COLUMNS["INITIAL_ACTION"]] if len(row) > SHEET_COLUMNS["INITIAL_ACTION"] and row[SHEET_COLUMNS["INITIAL_ACTION"]] else "",
                "action": row[SHEET_COLUMNS["CURRENT_ACTION"]] if len(row) > SHEET_COLUMNS["CURRENT_ACTION"] and row[SHEET_COLUMNS["CURRENT_ACTION"]] else "",
                "status": row[SHEET_COLUMNS["STATUS"]] if len(row) > SHEET_COLUMNS["STATUS"] and row[SHEET_COLUMNS["STATUS"]] else "alive"
            }
            return player
    
    return None

# Extraire l'ID de Google Drive à partir d'une URL
def extract_google_drive_id(url):
    if not url:
        return ""
    
    if "id=" in url:
        # Format: https://drive.google.com/file/d/ID/view?usp=sharing
        parts = url.split("id=")
        if len(parts) > 1:
            return parts[1].split("&")[0]
    elif "open?id=" in url:
        # Format: https://drive.google.com/open?id=ID
        parts = url.split("open?id=")
        if len(parts) > 1:
            return parts[1].split("&")[0]
    elif "/d/" in url:
        # Format: https://drive.google.com/file/d/ID/view
        parts = url.split("/d/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
    
    return url

# Fonction pour obtenir la cible d'un joueur
def get_target_info(target_nickname):
    return get_player_by_nickname(target_nickname)

# Fonction récursive pour trouver la prochaine cible vivante
def find_next_alive_target(nickname, visited=None):
    if visited is None:
        visited = []
    
    # Conversion en minuscule pour la comparaison
    if nickname and any(v and v.lower() == nickname.lower() for v in visited):
        # Circuit détecté, aucun joueur vivant trouvé
        return None
    
    if nickname:
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
    
    try:
        player = get_player_by_nickname(nickname)
        
        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
    except FileNotFoundError as e:
        return jsonify({"success": False, "message": str(e)}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Erreur de serveur: {str(e)}"}), 500
    
    if player["password"].lower() != password.lower():
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
                sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, next_target["nickname"])
                sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, next_target["action"])
                
                # Mettre à jour l'info du joueur
                player["target"] = next_target["nickname"]
                player["action"] = next_target["action"]
                
                target = next_target
            else:
                target = None
        
        if target:
            target_info = {
                "nickname": target["nickname"],
                "person_photo": target["person_photo"],
                "feet_photo": target["feet_photo"],
                "action": player["action"]  # L'action à réaliser est stockée dans la ligne du joueur
            }
    
    # Préparer la réponse avec le profil du joueur et sa cible
    response = {
        "success": True,
        "player": {
            "nickname": player["nickname"],
            "person_photo": player["person_photo"],
            "feet_photo": player["feet_photo"],
            "status": player["status"]
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
                sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, next_target["nickname"])
                sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, next_target["action"])
                
                # Mettre à jour l'info du joueur
                player["target"] = next_target["nickname"]
                player["action"] = next_target["action"]
                
                target = next_target
            else:
                target = None
        
        if target:
            target_info = {
                "nickname": target["nickname"],
                "person_photo": target["person_photo"],
                "feet_photo": target["feet_photo"],
                "action": player["action"]  # L'action à réaliser est stockée dans la ligne du joueur
            }
    
    # Préparer la réponse avec le profil du joueur et sa cible
    response = {
        "success": True,
        "player": {
            "nickname": player["nickname"],
            "person_photo": player["person_photo"],
            "feet_photo": player["feet_photo"],
            "status": player["status"]
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
        sheet.update_cell(killer["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, next_target_nickname)
        sheet.update_cell(killer["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, next_target_action)
        
        # 2. Marquer la victime comme morte et vider sa cible actuelle
        sheet.update_cell(victim["row"], SHEET_COLUMNS["STATUS"] + 1, "dead")
        sheet.update_cell(victim["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, "")
        sheet.update_cell(victim["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, "")
        
        # Récupérer les infos de la nouvelle cible pour la réponse
        new_target_info = None
        if next_target_nickname:
            new_target = get_player_by_nickname(next_target_nickname)
            if new_target:
                new_target_info = {
                    "nickname": new_target["nickname"],
                    "person_photo": new_target["person_photo"],
                    "feet_photo": new_target["feet_photo"],
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

@app.route("/api/killed", methods=["POST"])
def killed():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    
    sheet = get_sheet_client()
    
    try:
        # Récupérer le joueur qui déclare avoir été tué
        player = get_player_by_nickname(session["nickname"])
        
        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
        
        if player["status"].lower() == "dead":
            return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 400
        
        # 1. Marquer le joueur comme mort
        sheet.update_cell(player["row"], SHEET_COLUMNS["STATUS"] + 1, "dead")
        
        # 2. Si le joueur a une cible, il faut la réaffecter à son assassin
        if player["target"]:
            # Trouver l'assassin du joueur (celui qui a ce joueur comme cible)
            all_players = get_all_players()
            assassin = None
            
            for p in all_players:
                if p["target"] and player["nickname"] and p["target"].lower() == player["nickname"].lower():
                    assassin = p
                    break
            
            # Si on a trouvé l'assassin, lui donner la cible du joueur tué
            if assassin:
                sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, player["target"])
                sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, player["action"])
        
        # 3. Garder la cible du joueur mort (ne pas vider les champs)
        
        return jsonify({
            "success": True,
            "message": "Vous avez été marqué comme éliminé"
        })
        
    except Exception as e:
        print(f"Erreur lors de la déclaration de mort: {e}")
        return jsonify({"success": False, "message": f"Erreur lors de la déclaration: {str(e)}"}), 500

@app.route("/api/giveup", methods=["POST"])
def give_up():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    
    sheet = get_sheet_client()
    
    try:
        # Récupérer le joueur qui abandonne
        player = get_player_by_nickname(session["nickname"])
        
        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
        
        if player["status"].lower() == "dead":
            return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 400
        
        # 1. Marquer le joueur comme abandonnant (statut spécial)
        sheet.update_cell(player["row"], SHEET_COLUMNS["STATUS"] + 1, "gaveup")
        
        # 2. Si le joueur a une cible, il faut la réaffecter à son assassin
        if player["target"]:
            # Trouver l'assassin du joueur (celui qui a ce joueur comme cible)
            all_players = get_all_players()
            assassin = None
            
            for p in all_players:
                if p["target"] and player["nickname"] and p["target"].lower() == player["nickname"].lower():
                    assassin = p
                    break
            
            # Si on a trouvé l'assassin, lui donner la cible du joueur qui abandonne
            if assassin:
                sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, player["target"])
                sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, player["action"])
        
        # 3. Vider la cible actuelle du joueur qui abandonne
        sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, "")
        sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, "")
        
        return jsonify({
            "success": True,
            "message": "Vous avez abandonné le jeu"
        })
        
    except Exception as e:
        print(f"Erreur lors de l'abandon: {e}")
        return jsonify({"success": False, "message": f"Erreur lors de l'abandon: {str(e)}"}), 500

# Fonction utilitaire pour récupérer tous les joueurs
def get_all_players():
    sheet = get_sheet_client()
    data = sheet.get_all_values()
    
    players = []
    # Ignorer la ligne d'en-tête
    for i, row in enumerate(data[1:], 2):
        if len(row) <= SHEET_COLUMNS["NICKNAME"]:
            continue  # Ignorer les lignes incomplètes
            
        status = "alive"
        if len(row) > SHEET_COLUMNS["STATUS"]:
            status = row[SHEET_COLUMNS["STATUS"]] if row[SHEET_COLUMNS["STATUS"]] else "alive"
            
        players.append({
            "row": i,
            "nickname": row[SHEET_COLUMNS["NICKNAME"]],
            "password": row[SHEET_COLUMNS["PASSWORD"]] if len(row) > SHEET_COLUMNS["PASSWORD"] else "",
            "person_photo": extract_google_drive_id(row[SHEET_COLUMNS["PERSON_PHOTO"]]) if len(row) > SHEET_COLUMNS["PERSON_PHOTO"] else "",
            "feet_photo": extract_google_drive_id(row[SHEET_COLUMNS["FEET_PHOTO"]]) if len(row) > SHEET_COLUMNS["FEET_PHOTO"] else "",
            "kro_answer": row[SHEET_COLUMNS["KRO_ANSWER"]] if len(row) > SHEET_COLUMNS["KRO_ANSWER"] else "",
            "before_answer": row[SHEET_COLUMNS["BEFORE_ANSWER"]] if len(row) > SHEET_COLUMNS["BEFORE_ANSWER"] else "",
            "message": row[SHEET_COLUMNS["MESSAGE_ANSWER"]] if len(row) > SHEET_COLUMNS["MESSAGE_ANSWER"] else "",
            "challenge_ideas": row[SHEET_COLUMNS["CHALLENGE_IDEAS"]] if len(row) > SHEET_COLUMNS["CHALLENGE_IDEAS"] else "",
            "initial_target": row[SHEET_COLUMNS["INITIAL_TARGET"]] if len(row) > SHEET_COLUMNS["INITIAL_TARGET"] and row[SHEET_COLUMNS["INITIAL_TARGET"]] else "",
            "target": row[SHEET_COLUMNS["CURRENT_TARGET"]] if len(row) > SHEET_COLUMNS["CURRENT_TARGET"] and row[SHEET_COLUMNS["CURRENT_TARGET"]] else "",
            "initial_action": row[SHEET_COLUMNS["INITIAL_ACTION"]] if len(row) > SHEET_COLUMNS["INITIAL_ACTION"] and row[SHEET_COLUMNS["INITIAL_ACTION"]] else "",
            "action": row[SHEET_COLUMNS["CURRENT_ACTION"]] if len(row) > SHEET_COLUMNS["CURRENT_ACTION"] and row[SHEET_COLUMNS["CURRENT_ACTION"]] else "",
            "status": status
        })
    
    return players

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
        
        # Ajouter des informations sur les photos pour le débogage
        player = get_player_by_nickname(session["nickname"])
        photo_debug = {
            "nickname": player["nickname"],
            "person_photo_raw": sheet.cell(player["row"], SHEET_COLUMNS["PERSON_PHOTO"] + 1).value if player else "",
            "person_photo_extracted": player["person_photo"] if player else "",
            "feet_photo_raw": sheet.cell(player["row"], SHEET_COLUMNS["FEET_PHOTO"] + 1).value if player else "",
            "feet_photo_extracted": player["feet_photo"] if player else "",
            "url_preview": f"https://drive.google.com/uc?export=view&id={player['person_photo']}" if player and player["person_photo"] else ""
        }
        
        return jsonify({
            "success": True, 
            "data": result,
            "photo_debug": photo_debug,
            "columns": SHEET_COLUMNS
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)