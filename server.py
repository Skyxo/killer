import os
import json
import sys
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, send_from_directory
from flask_session import Session
import gspread
from google.oauth2 import service_account

# Chargement des contournements pare-feu et SSL
try:
    # Essayer de charger le contournement de pare-feu en premier
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'firewall_bypass.py')):
        print("Chargement du contournement pare-feu...")
        sys.path.insert(0, os.path.dirname(__file__))
        import firewall_bypass
except Exception as e:
    print(f"Remarque: Contournement pare-feu non chargé: {str(e)}")

# Tenter de charger la configuration proxy si elle existe
try:
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'proxy_config.py')):
        print("Chargement de la configuration proxy...")
        sys.path.insert(0, os.path.dirname(__file__))
        import proxy_config
except Exception as e:
    print(f"Remarque: Configuration proxy non chargée: {str(e)}")

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
        
        print(f"Tentative de connexion avec le fichier: {service_account_file}")
        print(f"Chemin absolu du fichier: {os.path.abspath(service_account_file)}")
        
        if not os.path.exists(service_account_file):
            print(f"AVERTISSEMENT: Le fichier {service_account_file} est introuvable.")
            print(f"Répertoire courant: {os.getcwd()}")
            print(f"Liste des fichiers dans le répertoire courant: {os.listdir('.')}")
            if os.path.exists("service_account_example.json"):
                print(f"Conseil: Copiez service_account_example.json vers {service_account_file} "
                      f"et remplissez-le avec vos informations d'identification Google.")
            return None
        
        print(f"Lecture du fichier de credentials: {service_account_file}")
        # Tenter de lire le contenu du fichier pour vérifier qu'il est accessible et valide
        try:
            with open(service_account_file, 'r') as f:
                service_account_content = f.read()
                print(f"Fichier service_account.json lu avec succès ({len(service_account_content)} caractères)")
        except Exception as file_error:
            print(f"ERREUR lors de la lecture du fichier {service_account_file}: {str(file_error)}")
            return None
            
        print("Création des credentials...")
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=scope
        )
        
        print("Autorisation avec gspread...")
        # Augmenter les timeouts pour les environnements avec connexion limitée
        import socket
        # Augmenter le timeout socket par défaut à 60 secondes (par défaut: ~20 secondes)
        socket.setdefaulttimeout(60)
        
        # Initialiser le client avec des timeouts plus longs
        client = gspread.authorize(credentials)
        
        print("Credentials créées et client autorisé avec succès")
        sheet_id = os.environ.get("SHEET_ID")
        print(f"ID de la feuille à ouvrir: {sheet_id}")
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
        import socket
        error_msg = str(e)
        
        if "APIError" in error_msg and ("API has not been used" in error_msg or "is disabled" in error_msg):
            print("\n=== AVERTISSEMENT: PROBLÈME D'API GOOGLE SHEETS ===")
            print("L'API Google Sheets n'est pas activée pour ce projet.")
            print("1. Allez sur Google Cloud Console: https://console.cloud.google.com/apis/library")
            print("2. Sélectionnez votre projet")
            print("3. Recherchez et activez 'Google Sheets API'")
            print("4. Attendez quelques minutes pour que l'activation soit prise en compte")
            print("===================================\n")
            print("Le serveur continue de démarrer malgré cette erreur.")
            return None
        elif "timed out" in error_msg.lower() or isinstance(e, (socket.timeout, socket.error)):
            print("\n=== AVERTISSEMENT: PROBLÈME DE CONNECTIVITÉ RÉSEAU ===")
            print("La connexion à l'API Google a échoué en raison d'un problème réseau.")
            print("Sur certains serveurs, comme Zomro, les connexions sortantes peuvent être limitées.")
            print("Solutions possibles:")
            print("1. Vérifiez que votre serveur autorise les connexions sortantes vers les domaines Google")
            print("2. Contactez votre hébergeur pour autoriser les domaines suivants:")
            print("   - sheets.googleapis.com")
            print("   - oauth2.googleapis.com")
            print("   - www.googleapis.com")
            print("3. Vérifiez la configuration du pare-feu ou proxy du serveur")
            print("4. Si vous utilisez un VPN, assurez-vous qu'il ne bloque pas les connexions")
            print("===================================\n")
            print("Le serveur continue de démarrer malgré cette erreur, mais les fonctionnalités Google Sheets ne fonctionneront pas.")
            return None
        elif "SSLError" in error_msg or "CERTIFICATE_VERIFY_FAILED" in error_msg:
            print("\n=== AVERTISSEMENT: PROBLÈME DE CERTIFICATS SSL ===")
            print("La connexion à l'API Google a échoué en raison d'un problème de certificats SSL.")
            print("Cela peut se produire sur des serveurs avec des configurations SSL personnalisées ou obsolètes.")
            print("Solutions possibles:")
            print("1. Mettez à jour les certificats CA du système")
            print("   Exécutez: sudo update-ca-certificates")
            print("2. Mettez à jour OpenSSL")
            print("3. Vérifiez la date système (les certificats expirent si la date est incorrecte)")
            print("===================================\n")
            print("Le serveur continue de démarrer malgré cette erreur.")
            return None
        else:
            print(f"\n=== AVERTISSEMENT: ERREUR LORS DE LA CONNEXION À GOOGLE SHEETS ===")
            print(f"Type d'erreur: {type(e).__name__}")
            print(f"Message d'erreur: {error_msg}")
            print(f"Détails de l'erreur: {traceback.format_exc()}")
            print("Solutions possibles:")
            print("1. Vérifiez que votre fichier service_account.json est correctement formaté")
            print("2. Vérifiez que le compte de service a accès au Google Sheet")
            print("3. Vérifiez que l'API Google Sheets est activée pour ce projet")
            print("===================================\n")
            print("Le serveur continue de démarrer malgré cette erreur.")
            return None
    except Exception as e:
        import traceback
        print(f"AVERTISSEMENT: Erreur lors de la connexion à Google Sheets: {str(e)}")
        print(f"Détails de l'erreur: {traceback.format_exc()}")
        print("Le serveur continue de démarrer malgré cette erreur.")
        return None

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
        print(f"AVERTISSEMENT: Erreur lors de l'initialisation de la colonne État: {e}")
        print("Le serveur continue de démarrer malgré cette erreur.")
    except Exception as e:
        print(f"AVERTISSEMENT: Erreur lors de l'initialisation de la colonne État: {e}")
        print("Le serveur continue de démarrer malgré cette erreur.")

# Appeler l'initialisation au démarrage (désactivé pour éviter les problèmes de connexion)
# initialize_status_column()

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
        # Mode de secours pour l'admin si Google Sheets est inaccessible
        if nickname.lower() == "admin" and password.lower() == "killer2025":
            session["nickname"] = "admin"
            session["is_admin"] = True
            return jsonify({
                "success": True,
                "player": {
                    "nickname": "ADMIN",
                    "person_photo": "",
                    "feet_photo": "",
                    "status": "alive"
                },
                "target": {
                    "nickname": "Mode maintenance",
                    "person_photo": "",
                    "feet_photo": "",
                    "action": "Résoudre les problèmes de connexion à Google Sheets"
                }
            })
        
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

def check_google_connectivity():
    """
    Vérifie la connectivité aux serveurs Google nécessaires pour l'API Sheets
    """
    import socket
    import ssl
    import requests
    from urllib.request import Request, urlopen
    import json
    
    # Endpoints d'API Google à vérifier (URLs valides pour tester)
    api_endpoints = {
        "sheets.googleapis.com": "https://sheets.googleapis.com/$discovery/rest?version=v4",
        "oauth2.googleapis.com": "https://oauth2.googleapis.com/token",
        "www.googleapis.com": "https://www.googleapis.com/discovery/v1/apis"
    }
    
    results = {}
    
    print("\n=== VÉRIFICATION DE LA CONNECTIVITÉ AUX SERVEURS GOOGLE ===")
    
    for domain, url in api_endpoints.items():
        try:
            # Tenter une résolution DNS
            try:
                ip = socket.gethostbyname(domain)
                dns_ok = True
                print(f"✓ DNS pour {domain}: OK ({ip})")
            except socket.gaierror as e:
                dns_ok = False
                print(f"✗ DNS pour {domain}: ÉCHEC ({str(e)})")
            
            # Tenter une connexion HTTPS avec une requête GET valide
            try:
                # Utiliser requests au lieu de urllib pour plus de robustesse
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=15, verify=True)
                # 2xx ou 3xx sont des codes réussis
                https_ok = 200 <= response.status_code < 400
                print(f"✓ HTTPS pour {domain}: OK (status {response.status_code})")
            except requests.exceptions.SSLError as e:
                https_ok = False
                print(f"✗ HTTPS pour {domain}: ÉCHEC SSL ({str(e)})")
                print("  Conseil: Le serveur peut avoir des problèmes de certificats SSL ou utiliser un proxy qui interfère.")
            except requests.exceptions.ConnectionError as e:
                https_ok = False
                print(f"✗ HTTPS pour {domain}: ÉCHEC DE CONNEXION ({str(e)})")
                print("  Conseil: Le serveur peut bloquer les connexions sortantes. Vérifiez le pare-feu.")
            except requests.exceptions.Timeout as e:
                https_ok = False
                print(f"✗ HTTPS pour {domain}: TIMEOUT ({str(e)})")
                print("  Conseil: La connexion est trop lente ou bloquée.")
            except Exception as e:
                https_ok = False
                print(f"✗ HTTPS pour {domain}: ÉCHEC ({str(e)})")
                
            results[domain] = {"dns": dns_ok, "https": https_ok}
        except Exception as e:
            print(f"✗ Test pour {domain}: ERREUR GÉNÉRALE ({str(e)})")
            results[domain] = {"dns": False, "https": False}
    
    # Évaluation globale
    all_ok = all(all(result.values()) for result in results.values())
    
    if all_ok:
        print("\n✓ CONNECTIVITÉ AUX API GOOGLE: OK")
    else:
        print("\n✗ PROBLÈMES DE CONNECTIVITÉ DÉTECTÉS!")
        print("Solutions possibles:")
        print("1. Vérifiez que votre serveur autorise les connexions sortantes vers les domaines Google")
        print("2. Contactez votre hébergeur pour autoriser les domaines requis")
        print("3. Vérifiez la configuration du pare-feu ou proxy du serveur")
        
    print("==================================================\n")
    
    return all_ok

@app.get("/check-connectivity")
def api_check_connectivity():
    """Endpoint pour vérifier la connectivité aux API Google"""
    result = check_google_connectivity()
    sheet = get_sheet_client()
    
    return jsonify({
        "connectivity": result,
        "sheet_client": sheet is not None,
        "environment": {
            "working_directory": os.getcwd(),
            "service_account_file": os.environ.get("SERVICE_ACCOUNT_FILE"),
            "service_account_exists": os.path.exists(os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")),
            "sheet_id": os.environ.get("SHEET_ID")
        }
    })

if __name__ == "__main__":
    # Vérifier la connectivité avant de démarrer le serveur
    check_google_connectivity()
    
    # Vérifier les variables d'environnement essentielles
    print(f"Working directory: {os.getcwd()}")
    print(f"SERVICE_ACCOUNT_FILE: {os.environ.get('SERVICE_ACCOUNT_FILE', 'Non défini')}")
    print(f"SHEET_ID: {os.environ.get('SHEET_ID', 'Non défini')}")
    
    # Démarrer le serveur
    # Utiliser le port spécifié dans l'environnement ou 8080 par défaut au lieu de 5000
    port = int(os.environ.get("PORT", 8080))
    print(f"Démarrage du serveur sur le port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)  # OK: seulement en debug local

@app.get("/health")
def health():
    return "ok", 200
