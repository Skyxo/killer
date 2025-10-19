import os
import socket
import threading
import time
from typing import Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

import gunicorn.app.base

from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, send_from_directory
from flask_session import Session
import gspread
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

try:
    import requests
except ImportError:  # pragma: no cover - requests est une dépendance de gspread
    requests = None


def _env_flag_is_true(env_value: Optional[str]) -> bool:
    """Retourne True si la valeur d'environnement représente un booléen vrai."""

    if not env_value:
        return False
    return env_value.strip().lower() in {"1", "true", "yes", "on"}


def check_google_connectivity() -> None:
    """Teste la connectivité aux principaux domaines Google utilisés par l'app."""

    if _env_flag_is_true(os.environ.get("SKIP_CONNECTIVITY_CHECK")):
        print("Vérification de la connectivité Google ignorée (SKIP_CONNECTIVITY_CHECK activé).")
        return

    print("\n=== VÉRIFICATION DE LA CONNECTIVITÉ AUX SERVEURS GOOGLE ===")

    targets = {
        "sheets.googleapis.com": "https://sheets.googleapis.com/$discovery/rest?version=v4",
        "oauth2.googleapis.com": "https://oauth2.googleapis.com/.well-known/openid-configuration",
        "www.googleapis.com": "https://www.googleapis.com/discovery/v1/apis",
    }

    timeout_seconds = int(os.environ.get("GOOGLE_CONNECTIVITY_TIMEOUT", "10"))
    ssl_context = None
    if _env_flag_is_true(os.environ.get("GOOGLE_CONNECTIVITY_SKIP_SSL_VERIFY")):
        try:
            import ssl

            ssl_context = ssl._create_unverified_context()
            print("Avertissement: la vérification SSL est désactivée pour ce test.")
        except Exception as ssl_error:  # pragma: no cover - très improbable
            print(f"Impossible de désactiver la vérification SSL: {ssl_error}")

    problems_detected = False

    for domain, test_url in targets.items():
        # Test DNS
        try:
            ip_address = socket.gethostbyname(domain)
            print(f"✓ DNS pour {domain}: OK ({ip_address})")
        except socket.gaierror as dns_error:
            problems_detected = True
            print(f"✗ DNS pour {domain}: ÉCHEC ({dns_error})")
            ip_address = None

        # Test HTTPS
        try:
            request = urllib_request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
            if ssl_context is None:
                with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                    status_code = response.getcode()
            else:
                with urllib_request.urlopen(request, timeout=timeout_seconds, context=ssl_context) as response:
                    status_code = response.getcode()

            print(f"✓ HTTPS pour {domain}: OK (statut {status_code})")
        except HTTPError as http_error:
            status_code = http_error.code
            if status_code < 500:
                # L'appel a abouti mais la ressource renvoie une erreur fonctionnelle (ex: 401, 404)
                print(f"✓ HTTPS pour {domain}: OK (statut {status_code})")
            else:
                problems_detected = True
                print(f"✗ HTTPS pour {domain}: ÉCHEC ({http_error})")
        except URLError as url_error:
            problems_detected = True
            reason = getattr(url_error, "reason", url_error)
            print(f"✗ HTTPS pour {domain}: ÉCHEC ({reason})")
        except Exception as unexpected_error:  # pragma: no cover - garde-fou
            problems_detected = True
            print(f"✗ HTTPS pour {domain}: ÉCHEC ({unexpected_error})")

    if problems_detected:
        print("\n✗ PROBLÈMES DE CONNECTIVITÉ DÉTECTÉS!")
        print("Solutions possibles:")
        print("1. Vérifiez que votre serveur autorise les connexions sortantes vers les domaines Google")
        print("2. Contactez votre hébergeur pour autoriser les domaines requis")
        print("3. Vérifiez la configuration du pare-feu ou proxy du serveur")
    else:
        print("\n✓ CONNECTIVITÉ AUX SERVEURS GOOGLE : OK")

    print("==================================================\n")

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
app.config["SESSION_USE_SIGNER"] = False  # Évite les incompatibilités bytes/str avec Flask 3+
session_directory = os.environ.get("SESSION_FILE_DIR") or os.path.join(os.getcwd(), "flask_session")
os.makedirs(session_directory, exist_ok=True)
app.config["SESSION_FILE_DIR"] = session_directory
Session(app)
if getattr(app.session_interface, "use_signer", False):
    app.session_interface.use_signer = False

try:
    session_permissions_value = os.stat(session_directory).st_mode & 0o777
    session_dir_permissions = format(session_permissions_value, "03o")
    print(f"Répertoire des sessions: {session_directory}")
    print(f"Permissions du répertoire des sessions: {session_dir_permissions}")
except OSError as session_dir_error:
    print(f"AVERTISSEMENT: Impossible de lire les permissions du répertoire des sessions ({session_dir_error})")

check_google_connectivity()

print(f"Working directory: {os.getcwd()}")
print(f"SERVICE_ACCOUNT_FILE: {os.environ.get('SERVICE_ACCOUNT_FILE')}")
print(f"SHEET_ID: {os.environ.get('SHEET_ID')}")

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
    "STATUS": 13,     # État (alive/dead/gaveup)
    "KILL_COUNT": 14, # Nombre de kills réalisés
}

_sheet_cache_lock = threading.Lock()
_cached_sheet = None
_cached_sheet_timestamp = 0.0


class AuthorizedSessionWithTimeout(AuthorizedSession):
    """Session autorisée Google avec timeout par défaut."""

    def __init__(self, credentials, default_timeout: Optional[float]):
        super().__init__(credentials)
        self._default_timeout = default_timeout

    def request(self, method, url, data=None, headers=None, timeout=None, **kwargs):
        effective_timeout = timeout or self._default_timeout
        return super().request(
            method,
            url,
            data=data,
            headers=headers,
            timeout=effective_timeout,
            **kwargs,
        )


def _get_cached_sheet(ttl_seconds: float):
    global _cached_sheet, _cached_sheet_timestamp
    now = time.time()
    if _cached_sheet is not None and (now - _cached_sheet_timestamp) < ttl_seconds:
        return _cached_sheet
    return None


def _store_sheet_in_cache(sheet):
    global _cached_sheet, _cached_sheet_timestamp
    _cached_sheet = sheet
    _cached_sheet_timestamp = time.time()


def _parse_int(value: Optional[str], default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        cleaned = str(value).strip()
        if not cleaned:
            return default
        return int(float(cleaned))
    except (ValueError, TypeError):
        return default


def _ensure_kill_count_header(sheet):
    try:
        headers = sheet.row_values(1)
    except Exception as header_error:
        print(f"AVERTISSEMENT: Impossible de lire les en-têtes de la feuille: {header_error}")
        return

    needs_header = len(headers) <= SHEET_COLUMNS["KILL_COUNT"]
    if not needs_header and SHEET_COLUMNS["KILL_COUNT"] < len(headers):
        current_header = headers[SHEET_COLUMNS["KILL_COUNT"]].strip()
        needs_header = current_header == ""

    if needs_header:
        try:
            sheet.update_cell(1, SHEET_COLUMNS["KILL_COUNT"] + 1, "Kills")
        except Exception as update_error:
            print(f"AVERTISSEMENT: Impossible de garantir la colonne 'Kills': {update_error}")


# Connexion à l'API Google Sheets
def get_sheet_client():
    try:
        cache_ttl = float(os.environ.get("SHEET_CACHE_TTL", "60"))
        sheet = _get_cached_sheet(cache_ttl)
        if sheet is not None:
            return sheet

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
        
        if not os.path.exists(service_account_file):
            print(f"AVERTISSEMENT: Le fichier {service_account_file} est introuvable.")
            if os.path.exists("service_account_example.json"):
                print(f"Conseil: Copiez service_account_example.json vers {service_account_file} "
                      f"et remplissez-le avec vos informations d'identification Google.")
            return None
        
        timeout_seconds = float(os.environ.get("GOOGLE_REQUEST_TIMEOUT", "15"))
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=scope
        )
        session_timeout = timeout_seconds if timeout_seconds > 0 else None
        client = gspread.authorize(credentials)

        # Remplace la session utilisée par gspread pour bénéficier d'un timeout par défaut.
        client.session = AuthorizedSessionWithTimeout(credentials, session_timeout)
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
            with _sheet_cache_lock:
                cached_sheet = _get_cached_sheet(cache_ttl)
                if cached_sheet is not None:
                    return cached_sheet

                sheet = client.open_by_key(sheet_id).sheet1
                _store_sheet_in_cache(sheet)
            return sheet
        except Exception as sheet_error:
            raise ValueError(f"Erreur lors de l'ouverture du spreadsheet: {str(sheet_error)}. Vérifiez que l'ID est correct et que le service account a les permissions nécessaires.")
    except Exception as e:
        import traceback
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
        else:
            print(f"AVERTISSEMENT: Erreur lors de la connexion à Google Sheets: {error_msg}")
            print(f"Détails de l'erreur: {traceback.format_exc()}")
            if requests is not None and isinstance(e, requests.exceptions.Timeout):
                print("Détails: Timeout lors de l'appel à l'API Google Sheets. Réessayera au prochain appel.")
            print("Le serveur continue de démarrer malgré cette erreur.")
            return None
    except Exception as e:
        import traceback
        print(f"AVERTISSEMENT: Erreur lors de la connexion à Google Sheets: {str(e)}")
        print(f"Détails de l'erreur: {traceback.format_exc()}")
        print("Le serveur continue de démarrer malgré cette erreur.")
        return None

# Fournit un accès obligatoire à la feuille ou lève une erreur contrôlée
def require_sheet_client():
    sheet = get_sheet_client()
    if sheet is None:
        raise ConnectionError(
            "Connexion à Google Sheets indisponible. Vérifiez la connectivité réseau et les identifiants."
        )
    return sheet


def _status_is_admin(status_value: Optional[str]) -> bool:
    if not status_value:
        return False
    return status_value.strip().lower() == "admin"

# Fonction pour initialiser la colonne "État" si elle n'existe pas
def initialize_status_column():
    try:
        sheet = require_sheet_client()
        headers = sheet.row_values(1)
        
        # Vérifier si les colonnes nécessaires existent déjà
        # Initialisation des colonnes manquantes
        if len(headers) <= SHEET_COLUMNS["CURRENT_TARGET"]:
            sheet.update_cell(1, SHEET_COLUMNS["CURRENT_TARGET"] + 1, "Cible actuelle")
        
        if len(headers) <= SHEET_COLUMNS["CURRENT_ACTION"]:
            sheet.update_cell(1, SHEET_COLUMNS["CURRENT_ACTION"] + 1, "Action actuelle")
            
        if len(headers) <= SHEET_COLUMNS["STATUS"]:
            sheet.update_cell(1, SHEET_COLUMNS["STATUS"] + 1, "État")

        if len(headers) <= SHEET_COLUMNS["KILL_COUNT"]:
            sheet.update_cell(1, SHEET_COLUMNS["KILL_COUNT"] + 1, "Kills")
        
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

            if len(row) <= SHEET_COLUMNS["KILL_COUNT"] or not str(row[SHEET_COLUMNS["KILL_COUNT"]]).strip():
                sheet.update_cell(i + 1, SHEET_COLUMNS["KILL_COUNT"] + 1, "0")
        
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
    sheet = require_sheet_client()
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
                "status": row[SHEET_COLUMNS["STATUS"]] if len(row) > SHEET_COLUMNS["STATUS"] and row[SHEET_COLUMNS["STATUS"]] else "alive",
                "kill_count": _parse_int(
                    row[SHEET_COLUMNS["KILL_COUNT"]] if len(row) > SHEET_COLUMNS["KILL_COUNT"] else 0,
                    default=0,
                ),
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

@app.route("/favicon.ico")
def favicon():
    return send_from_directory('client', 'img/Killer.png', mimetype='image/png')

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
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
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
                sheet = require_sheet_client()
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
            "status": player["status"],
            "kill_count": player.get("kill_count", 0),
            "is_admin": _status_is_admin(player.get("status")),
        },
        "target": target_info
    }
    
    return jsonify(response)

@app.route("/api/me", methods=["GET"])
def get_me():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    
    try:
        player = get_player_by_nickname(session["nickname"])
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    
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
                sheet = require_sheet_client()
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
            "status": player["status"],
            "is_admin": _status_is_admin(player.get("status")),
        },
        "target": target_info
    }
    
    return jsonify(response)

@app.route("/api/kill", methods=["POST"])
def kill():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    try:
        sheet = require_sheet_client()
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
            "target": new_target_info,
        }

        return jsonify(response)
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"Erreur lors du kill: {e}")
        return jsonify({"success": False, "message": f"Erreur lors du kill: {str(e)}"}), 500

@app.route("/api/killed", methods=["POST"])
def killed():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    try:
        sheet = require_sheet_client()
        _ensure_kill_count_header(sheet)
        # Récupérer le joueur qui déclare avoir été tué
        player = get_player_by_nickname(session["nickname"])
        
        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
        
        if player["status"].lower() == "dead":
            return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 400
        
        # 1. Marquer le joueur comme mort
        sheet.update_cell(player["row"], SHEET_COLUMNS["STATUS"] + 1, "dead")
        
        # 2. Si le joueur a une cible, il faut la réaffecter à son assassin
        # Trouver l'assassin du joueur (celui qui a ce joueur comme cible)
        all_players = get_all_players()
        assassin = None
        
        for p in all_players:
            if p["target"] and player["nickname"] and p["target"].lower() == player["nickname"].lower():
                assassin = p
                break
        
        # Si on a trouvé l'assassin, lui donner la cible du joueur tué et incrémenter son score
        if assassin:
            new_target = player.get("target") or ""
            new_action = player.get("action") or ""
            sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, new_target)
            sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_ACTION"] + 1, new_action)
            current_assassin_kills = _parse_int(assassin.get("kill_count", 0), 0)
            sheet.update_cell(
                assassin["row"],
                SHEET_COLUMNS["KILL_COUNT"] + 1,
                str(current_assassin_kills + 1),
            )
        
        # 3. Garder la cible du joueur mort (ne pas vider les champs)
        
        return jsonify({
            "success": True,
            "message": "Vous avez été marqué comme éliminé"
        })
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"Erreur lors de la déclaration de mort: {e}")
        return jsonify({"success": False, "message": f"Erreur lors de la déclaration: {str(e)}"}), 500

@app.route("/api/giveup", methods=["POST"])
def give_up():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    try:
        sheet = require_sheet_client()
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
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"Erreur lors de l'abandon: {e}")
        return jsonify({"success": False, "message": f"Erreur lors de l'abandon: {str(e)}"}), 500


@app.route("/api/admin/overview", methods=["GET"])
def admin_overview():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    try:
        current_player = get_player_by_nickname(session["nickname"])
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503

    if not current_player:
        return jsonify({"success": False, "message": "Joueur non trouvé"}), 404

    if not _status_is_admin(current_player.get("status")):
        return jsonify({"success": False, "message": "Accès refusé"}), 403

    players = get_all_players()
    overview = []
    for player in players:
        overview.append(
            {
                "nickname": player.get("nickname", ""),
                "status": (player.get("status") or "alive"),
                "target": player.get("target") or "",
                "action": player.get("action") or "",
                "initial_target": player.get("initial_target") or "",
                "initial_action": player.get("initial_action") or "",
            }
        )

    return jsonify({"success": True, "players": overview})

# Fonction utilitaire pour récupérer tous les joueurs
def get_all_players():
    sheet = require_sheet_client()
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
            "status": status,
            "kill_count": _parse_int(
                row[SHEET_COLUMNS["KILL_COUNT"]] if len(row) > SHEET_COLUMNS["KILL_COUNT"] else 0,
                default=0,
            ),
        })
    
    return players


def _normalize_status(status_value: Optional[str]) -> str:
    if not status_value:
        return "alive"
    return status_value.strip().lower()


def _trombi_entry(player: dict, viewer_nickname: Optional[str], include_status: bool) -> dict:
    nickname = player.get("nickname", "") or ""
    normalized_status = _normalize_status(player.get("status"))
    person_photo_id = player.get("person_photo", "") or ""
    return {
        "nickname": nickname,
        "person_photo": person_photo_id,
        "status": normalized_status if include_status else None,
        "is_self": bool(viewer_nickname and nickname and nickname.lower() == viewer_nickname.lower()),
        "is_admin": _status_is_admin(player.get("status")),
    }


def _viewer_can_see_status(viewer_status: Optional[str]) -> bool:
    normalized = _normalize_status(viewer_status)
    if normalized == "dead":
        return True
    return normalized == "admin"


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    try:
        players = get_all_players()
        leaderboard = []
        for player in players:
            leaderboard.append(
                {
                    "nickname": player.get("nickname", ""),
                    "kill_count": _parse_int(player.get("kill_count", 0), 0),
                    "status": (player.get("status") or "alive").lower(),
                    "is_admin": (player.get("status") or "").strip().lower() == "admin",
                    "target": player.get("target") or "",
                    "action": player.get("action") or "",
                }
            )

        leaderboard.sort(key=lambda entry: (-entry["kill_count"], entry["nickname"].lower()))

        return jsonify({"success": True, "leaderboard": leaderboard})
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"Erreur lors de la récupération du leaderboard: {e}")
        return jsonify({"success": False, "message": "Erreur interne lors du calcul du leaderboard"}), 500


@app.route("/api/trombi", methods=["GET"])
def get_trombi():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    try:
        viewer = get_player_by_nickname(session["nickname"])
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503

    if not viewer:
        session.clear()
        return jsonify({"success": False, "message": "Joueur non trouvé"}), 404

    include_status = _viewer_can_see_status(viewer.get("status"))

    try:
        players = get_all_players()
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503

    entries = [_trombi_entry(player, viewer.get("nickname"), include_status) for player in players]
    entries.sort(key=lambda entry: (
        0 if entry.get("is_admin") else 1,
        (entry.get("nickname") or "").lower(),
    ))

    return jsonify({
        "success": True,
        "players": entries,
        "viewer": {
            "nickname": viewer.get("nickname"),
            "status": _normalize_status(viewer.get("status")),
            "can_view_status": include_status,
        },
    })

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
        sheet = require_sheet_client()
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

@app.get("/health")
def health():
    return "ok", 200


def _coerce_positive_int(value: Optional[str], default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _default_worker_count() -> int:
    try:
        import multiprocessing

        cpu_count = multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):  # pragma: no cover - environ exotiques
        cpu_count = 1
    return max(1, cpu_count * 2 + 1)


def _build_gunicorn_options() -> dict:
    host = os.environ.get("HOST", os.environ.get("BIND", "0.0.0.0"))
    port = _coerce_positive_int(os.environ.get("PORT"), 5000)
    workers = _coerce_positive_int(
        os.environ.get("GUNICORN_WORKERS"), _default_worker_count()
    )
    timeout = _coerce_positive_int(os.environ.get("GUNICORN_TIMEOUT"), 60)
    keepalive = _coerce_positive_int(os.environ.get("GUNICORN_KEEPALIVE"), 5)

    return {
        "bind": f"{host}:{port}",
        "workers": workers,
        "timeout": timeout,
        "keepalive": keepalive,
        "accesslog": os.environ.get("GUNICORN_ACCESS_LOG", "-"),
        "errorlog": os.environ.get("GUNICORN_ERROR_LOG", "-"),
        "loglevel": os.environ.get("GUNICORN_LOGLEVEL", "info"),
        "worker_tmp_dir": os.environ.get("GUNICORN_WORKER_TMP_DIR"),
    }


def run_gunicorn():
    try:
        from gunicorn.app.base import BaseApplication
    except ImportError as exc:
        print("\nERREUR: Gunicorn n'est pas installé (module introuvable).")
        print("Installez les dépendances avec: pip install -r requirements.txt")
        print("Démarrage du serveur de développement Flask en mode secours.\n")
        app.run(host="0.0.0.0", port=_coerce_positive_int(os.environ.get("PORT"), 5000), debug=True)
        return

    class StandaloneGunicornApplication(BaseApplication):
        def __init__(self, application, options=None):
            self.application = application
            self.options = options or {}
            super().__init__()

        def load_config(self):
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    options = _build_gunicorn_options()
    print("Démarrage de l'application avec Gunicorn")
    for key, value in options.items():
        if value is not None:
            print(f"  {key}: {value}")

    StandaloneGunicornApplication(app, options).run()


if __name__ == "__main__":
    run_gunicorn()
