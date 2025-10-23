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
import unicodedata

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
    "YEAR": 2,        # Année (0A, 2A, 3A, etc.)
    "GENDER": 3,      # Sexe (H/F)
    "PASSWORD": 4,    # Votre mot de passe
    "PERSON_PHOTO": 5,# Une photo de vous neuillesque
    "FEET_PHOTO": 6,  # une photo de vos pieds
    "KRO_ANSWER": 7,  # Combien y a t il de cars dans une kro ?
    "BEFORE_ANSWER": 8, # Est-ce que c'était mieux avant ?
    "MESSAGE_ANSWER": 9, # Un petit mot pour vos brasseurs adorés
    "CHALLENGE_IDEAS": 10, # Idées de défis
    "CURRENT_TARGET": 11, # Cible actuelle
    "STATUS": 12,     # État (alive/dead/gaveup)
    "KILLED_BY": 13,  # Tué par (surnom du killer)
    "ELIMINATION_ORDER": 14, # Ordre d'élimination (-1=ne joue pas, 0=en jeu, >0=éliminé)
    "KILL_COUNT": 15, # Nombre de kills
    "ADMIN_FLAG": 16, # Indique si le joueur est administrateur (True/False)
    "PHONE": 17,      # Téléphone
}

_sheet_cache_lock = threading.Lock()
_cached_sheet = None
_cached_sheet_timestamp = 0.0

# Cache pour les données des joueurs
_players_cache = None
_players_cache_timestamp = 0.0
_players_cache_ttl = 5.0  # 5 secondes de cache pour les données joueurs

# Cache pour la feuille 2 (mapping Surnom -> Défi ciblé)
_actions_map_cache = None
_actions_map_cache_timestamp = 0.0
_actions_map_cache_ttl = 5.0


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


def _get_cached_actions_map(ttl_seconds: float):
    global _actions_map_cache, _actions_map_cache_timestamp
    now = time.time()
    if _actions_map_cache is not None and (now - _actions_map_cache_timestamp) < ttl_seconds:
        return _actions_map_cache
    return None


def _store_actions_map_in_cache(actions_map: dict):
    global _actions_map_cache, _actions_map_cache_timestamp
    _actions_map_cache = actions_map
    _actions_map_cache_timestamp = time.time()


def invalidate_players_cache():
    """Invalide le cache des joueurs après une modification"""
    global _players_cache, _players_cache_timestamp
    with _sheet_cache_lock:
        _players_cache = None
        _players_cache_timestamp = 0.0


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


def _parse_admin_flag(value: Optional[str]) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    cleaned = str(value).strip().lower()
    if not cleaned:
        return False
    return cleaned in {"1", "true", "yes", "on"}


def _normalize_name(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        # Normalisation Unicode + trim + minuscule insensible à la casse
        text = unicodedata.normalize("NFKC", str(value)).strip()
        # Retirer les espaces insécables/zero-width
        text = "".join(ch for ch in text if not unicodedata.category(ch) in {"Cf"})
        return text.casefold()
    except Exception:
        return str(value).strip().lower()


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

                workbook = client.open_by_key(sheet_id)
                sheet1 = workbook.sheet1
                _store_sheet_in_cache(sheet1)
            return sheet1
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


def get_actions_map():
    """Lit la feuille 2 et retourne un dict {nickname_lower: action_str}."""
    cache_ttl = _actions_map_cache_ttl
    cached = _get_cached_actions_map(cache_ttl)
    if cached is not None:
        return cached

    # Accès au classeur puis à la deuxième feuille
    sheet = get_sheet_client()
    if sheet is None:
        return {}
    try:
        workbook = sheet.spreadsheet
        # Chercher la feuille "defis" par nom
        try:
            actions_ws = workbook.worksheet("defis")
        except Exception:
            # Fallback sur la 2e feuille par index
            worksheets = workbook.worksheets()
            if len(worksheets) < 2:
                print("[ACTIONS_MAP] Aucune feuille 'defis' trouvée et moins de 2 feuilles")
                _store_actions_map_in_cache({})
                return {}
            actions_ws = worksheets[1]
            print(f"[ACTIONS_MAP] Utilisation de la feuille par index: {actions_ws.title}")
        
        values = actions_ws.get_all_values()
        print(f"[ACTIONS_MAP] Feuille '{actions_ws.title}' - {len(values)} lignes")
        actions_map = {}
        # Attendu: en-têtes ["Surnom", "Défi ciblé"]
        for row in values[1:]:
            if not row:
                continue
            nickname = (row[0] or "").strip()
            if not nickname:
                continue
            action = (row[1] if len(row) > 1 else "").strip()
            actions_map[nickname.lower()] = action
            # Log seulement les actions non vides pour réduire le spam
            if action and action != "...":
                print(f"[ACTIONS_MAP] Mapping: '{nickname}' -> '{action}'")
        
        print(f"[ACTIONS_MAP] Total mappings: {len(actions_map)}")
        _store_actions_map_in_cache(actions_map)
        return actions_map
    except Exception:
        # En cas d'erreur on renvoie un mapping vide pour ne pas casser l'app
        import traceback
        print(f"[ACTIONS_MAP] Erreur lors de la lecture: {traceback.format_exc()}")
        return {}


def get_action_for_target(target_nickname: Optional[str]) -> str:
    if not target_nickname:
        return ""
    actions = get_actions_map()
    if not isinstance(actions, dict):
        return ""
    return actions.get((target_nickname or "").strip().lower(), "")


# Fonction pour initialiser la colonne "État" si elle n'existe pas
def initialize_status_column():
    try:
        sheet = require_sheet_client()
        headers = sheet.row_values(1)
        
        # Vérifier si les colonnes nécessaires existent déjà
        # Initialisation des colonnes manquantes
        if len(headers) <= SHEET_COLUMNS["CURRENT_TARGET"]:
            sheet.update_cell(1, SHEET_COLUMNS["CURRENT_TARGET"] + 1, "Cible actuelle")
            
        if len(headers) <= SHEET_COLUMNS["STATUS"]:
            sheet.update_cell(1, SHEET_COLUMNS["STATUS"] + 1, "État")

        if len(headers) <= SHEET_COLUMNS["ADMIN_FLAG"]:
            sheet.update_cell(1, SHEET_COLUMNS["ADMIN_FLAG"] + 1, "Admin")
        
        # Vérifier si les données des joueurs doivent être initialisées
        data = sheet.get_all_values()
        for i in range(1, len(data)):  # Commencer à la deuxième ligne (après les en-têtes)
            row = data[i]
            
            # Initialiser la cible actuelle si elle est vide (plus de colonnes initiales)
            # On ne peut plus copier depuis une colonne initiale supprimée.
            
            # Initialiser l'état si vide
            if len(row) <= SHEET_COLUMNS["STATUS"] or not row[SHEET_COLUMNS["STATUS"]]:
                sheet.update_cell(i + 1, SHEET_COLUMNS["STATUS"] + 1, "alive")

            if len(row) <= SHEET_COLUMNS["ADMIN_FLAG"] or not str(row[SHEET_COLUMNS["ADMIN_FLAG"]]).strip():
                sheet.update_cell(i + 1, SHEET_COLUMNS["ADMIN_FLAG"] + 1, "False")
        
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

    target_nickname = _normalize_name(nickname)

    # Ignorer la ligne d'en-tête
    for i, row in enumerate(data[1:], 2):
        if len(row) <= SHEET_COLUMNS["NICKNAME"]:
            continue

        sheet_nickname_raw = row[SHEET_COLUMNS["NICKNAME"]] or ""
        sheet_nickname = sheet_nickname_raw.strip()

        # Comparaison insensible à la casse pour le surnom
        if _normalize_name(sheet_nickname) == target_nickname:
            password = row[SHEET_COLUMNS["PASSWORD"]] if len(row) > SHEET_COLUMNS["PASSWORD"] else ""
            status_value = row[SHEET_COLUMNS["STATUS"]] if len(row) > SHEET_COLUMNS["STATUS"] else "alive"
            admin_flag_value = row[SHEET_COLUMNS["ADMIN_FLAG"]] if len(row) > SHEET_COLUMNS["ADMIN_FLAG"] else "False"

            player = {
                "row": i,
                "nickname": sheet_nickname,
                "gender": (row[SHEET_COLUMNS["GENDER"]] or "").strip() if len(row) > SHEET_COLUMNS["GENDER"] else "",
                "password": password.strip() if isinstance(password, str) else password,
                "person_photo": extract_google_drive_id(row[SHEET_COLUMNS["PERSON_PHOTO"]]) if len(row) > SHEET_COLUMNS["PERSON_PHOTO"] else "",
                "feet_photo": extract_google_drive_id(row[SHEET_COLUMNS["FEET_PHOTO"]]) if len(row) > SHEET_COLUMNS["FEET_PHOTO"] else "",
                "kro_answer": (row[SHEET_COLUMNS["KRO_ANSWER"]] or "").strip() if len(row) > SHEET_COLUMNS["KRO_ANSWER"] else "",
                "before_answer": (row[SHEET_COLUMNS["BEFORE_ANSWER"]] or "").strip() if len(row) > SHEET_COLUMNS["BEFORE_ANSWER"] else "",
                "message": (row[SHEET_COLUMNS["MESSAGE_ANSWER"]] or "").strip() if len(row) > SHEET_COLUMNS["MESSAGE_ANSWER"] else "",
                "challenge_ideas": (row[SHEET_COLUMNS["CHALLENGE_IDEAS"]] or "").strip() if len(row) > SHEET_COLUMNS["CHALLENGE_IDEAS"] else "",
                "target": (row[SHEET_COLUMNS["CURRENT_TARGET"]] or "").strip() if len(row) > SHEET_COLUMNS["CURRENT_TARGET"] else "",
                # action désormais dérivée de la feuille 2
                "action": get_action_for_target((row[SHEET_COLUMNS["CURRENT_TARGET"]] or "").strip() if len(row) > SHEET_COLUMNS["CURRENT_TARGET"] else ""),
                "status": _normalize_status(status_value),
                "is_admin": _parse_admin_flag(admin_flag_value),
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
def find_next_alive_target(nickname, visited=None, all_players=None):
    if visited is None:
        visited = []
    
    # Charger tous les joueurs une seule fois si pas déjà fourni
    if all_players is None:
        all_players = get_all_players()
    
    # Conversion en minuscule pour la comparaison
    if nickname and any(v and v.lower() == nickname.lower() for v in visited):
        # Circuit détecté, aucun joueur vivant trouvé
        return None
    
    if nickname:
        visited.append(nickname)
    
    # Trouver le joueur dans la liste
    player = next((p for p in all_players if p["nickname"].lower() == nickname.lower()), None)
    
    if not player or not player["target"]:
        return None
    
    # Trouver la cible dans la liste
    target = next((p for p in all_players if p["nickname"].lower() == player["target"].lower()), None)
    
    if not target:
        return None
    
    if target["status"].lower() == "alive":
        return target
    
    # Si la cible est morte, chercher la cible de cette cible
    return find_next_alive_target(target["target"], visited, all_players)

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
    raw = request.get_json(silent=True)
    if raw is None:
        # Flask MultiDict -> dict
        if request.form:
            raw = request.form.to_dict(flat=True)
        elif request.args:
            raw = request.args.to_dict(flat=True)
        else:
            raw = {}
    data = raw if isinstance(raw, dict) else {}

    # Alias tolérés côté client
    nickname = data.get("nickname") or data.get("pseudo") or data.get("username") or data.get("login")
    password = data.get("password") or data.get("mdp") or data.get("pass")
    
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
                },
                "hunter": None
            })
        
        player = get_player_by_nickname(nickname)
        
        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except FileNotFoundError as e:
        return jsonify({"success": False, "message": str(e)}), 500
    except Exception as e:
        import traceback
        print(f"[LOGIN] Erreur: {e}. Payload: {data}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur de serveur: {str(e)}"}), 500
    
    if player["password"].lower() != password.lower():
        return jsonify({"success": False, "message": "Mot de passe incorrect"}), 401
    
    # Stocker l'ID du joueur dans la session
    session["nickname"] = nickname
    
    # Charger tous les joueurs une seule fois pour optimiser les recherches
    try:
        all_players = get_all_players()
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500
    
    # Récupérer les informations de la cible
    target_info = None
    if player["target"]:
        # Trouver la cible dans la liste chargée
        target = next((p for p in all_players if p["nickname"].lower() == player["target"].lower()), None)
        
        # Si la cible est morte, trouver la prochaine cible vivante
        if target and target["status"].lower() == "dead":
            next_target = find_next_alive_target(player["target"], None, all_players)
            
            if next_target:
                # Mettre à jour la cible dans la feuille
                sheet = require_sheet_client()
                sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, next_target["nickname"])
                
                # Mettre à jour l'info du joueur
                player["target"] = next_target["nickname"]
                player["action"] = get_action_for_target(next_target["nickname"])            
                
                target = next_target
            else:
                target = None
        
        if target:
            target_info = {
                "nickname": target["nickname"],
                "person_photo": target["person_photo"],
                "feet_photo": target["feet_photo"],
                "action": player["action"]
            }
    
    # Calculer le chasseur (celui qui a ce joueur comme cible)
    hunter_info = None
    hunter_player = next((p for p in all_players if p.get("target") and player.get("nickname") and p["target"].lower() == player["nickname"].lower()), None)
    if hunter_player:
        hunter_info = {
            "nickname": hunter_player.get("nickname", ""),
            "action": get_action_for_target(player.get("nickname"))
        }
    
    # Préparer la réponse avec le profil du joueur et sa cible
    response = {
        "success": True,
        "player": {
            "nickname": player["nickname"],
            "person_photo": player["person_photo"],
            "feet_photo": player["feet_photo"],
            "status": player["status"],
            "is_admin": bool(player.get("is_admin")),
        },
        "target": target_info,
        "hunter": hunter_info
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
                
                # Mettre à jour l'info du joueur
                player["target"] = next_target["nickname"]
                player["action"] = get_action_for_target(next_target["nickname"])            
                
                target = next_target
            else:
                target = None
        
        if target:
            target_info = {
                "nickname": target["nickname"],
                "person_photo": target["person_photo"],
                "feet_photo": target["feet_photo"],
                "action": player["action"]
            }
    
    # Calculer le chasseur (celui qui a ce joueur comme cible)
    all_players = get_all_players()
    hunter_info = None
    hunter_player = next((p for p in all_players if p.get("target") and player.get("nickname") and p["target"].lower() == player["nickname"].lower()), None)
    if hunter_player:
        hunter_info = {
            "nickname": hunter_player.get("nickname", ""),
            "action": get_action_for_target(player.get("nickname"))
        }
    
    # Préparer la réponse avec le profil du joueur et sa cible
    response = {
        "success": True,
        "player": {
            "nickname": player["nickname"],
            "person_photo": player["person_photo"],
            "feet_photo": player["feet_photo"],
            "status": player["status"],
            "is_admin": bool(player.get("is_admin")),
        },
        "target": target_info,
        "hunter": hunter_info
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
        
        # 1. Incrémenter le nombre de kills du killer
        killer_kills = killer.get("kill_count", 0)
        sheet.update_cell(killer["row"], SHEET_COLUMNS["KILL_COUNT"] + 1, str(killer_kills + 1))
        
        # 2. Mettre à jour le killer avec la nouvelle cible
        sheet.update_cell(killer["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, next_target_nickname)
        # plus d'écriture d'action dans la feuille 1
        
        # 3. Marquer la victime comme morte et vider sa cible actuelle
        sheet.update_cell(victim["row"], SHEET_COLUMNS["STATUS"] + 1, "dead")
        sheet.update_cell(victim["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, "")
        # plus d'écriture d'action dans la feuille 1
        
        # Récupérer les infos de la nouvelle cible pour la réponse
        new_target_info = None
        if next_target_nickname:
            new_target = get_player_by_nickname(next_target_nickname)
            if new_target:
                new_target_info = {
                    "nickname": new_target["nickname"],
                    "person_photo": new_target["person_photo"],
                    "feet_photo": new_target["feet_photo"],
                    "action": get_action_for_target(new_target["nickname"]) or next_target_action
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
        # Récupérer le joueur qui déclare avoir été tué
        player = get_player_by_nickname(session["nickname"])
        
        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404
        
        if player["status"].lower() == "dead":
            return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 400
        
        # Compter combien de joueurs actifs (elimination_order >= 0) sont déjà morts
        all_players = get_all_players()
        active_players = [p for p in all_players if _parse_int(p.get("elimination_order", "0"), 0) >= 0]
        dead_active_count = sum(1 for p in active_players if p.get("status", "").lower() == "dead")
        elimination_order = dead_active_count + 1
        
        print(f"[KILLED] Joueur {player['nickname']} éliminé. Ordre: {elimination_order} (morts actifs actuels: {dead_active_count})")
        
        # 1. Marquer le joueur comme mort et enregistrer l'ordre d'élimination
        sheet.update_cell(player["row"], SHEET_COLUMNS["STATUS"] + 1, "dead")
        sheet.update_cell(player["row"], SHEET_COLUMNS["ELIMINATION_ORDER"] + 1, str(elimination_order))
        
        # Invalider le cache pour forcer le rechargement
        invalidate_players_cache()
        
        # 2. Si le joueur a une cible, il faut la réaffecter à son assassin
        # Trouver l'assassin du joueur (celui qui a ce joueur comme cible)
        assassin = None
        
        for p in all_players:
            if p["target"] and player["nickname"] and p["target"].lower() == player["nickname"].lower():
                assassin = p
                break
        
        # Si on a trouvé l'assassin, lui donner la cible du joueur tué et incrémenter son score
        if assassin:
            new_target = player.get("target") or ""
            new_action = get_action_for_target(new_target) or ""
            sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, new_target)
            # plus d'écriture d'action dans la feuille 1
            
            # Incrémenter le nombre de kills de l'assassin
            assassin_kills = assassin.get("kill_count", 0)
            sheet.update_cell(assassin["row"], SHEET_COLUMNS["KILL_COUNT"] + 1, str(assassin_kills + 1))
            
            # Enregistrer qui a tué le joueur
            sheet.update_cell(player["row"], SHEET_COLUMNS["KILLED_BY"] + 1, assassin["nickname"])
            
            print(f"[KILLED] Assassin {assassin['nickname']} a maintenant {assassin_kills + 1} kills")
        
        # 3. Garder la cible du joueur mort (ne pas vider les champs)
        # (on ne touche pas à l'action car elle n'existe plus dans la feuille 1)
        
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

        if (player.get("status") or "").lower() == "dead":
            return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 400

        # 1. Marquer le joueur comme abandonnant (statut spécial)
        sheet.update_cell(player["row"], SHEET_COLUMNS["STATUS"] + 1, "gaveup")

        # 1b. Enregistrer un ordre d'élimination unique pour l'abandon.
        # Utiliser le maximum des ordres existants + 1 pour garantir unicité.
        all_players = get_all_players()
        existing_orders = [ _parse_int(p.get("elimination_order", ""), 0) for p in all_players if str(p.get("elimination_order", "")).strip() != "" ]
        max_order = max(existing_orders) if existing_orders else 0
        elimination_order = max_order + 1
        sheet.update_cell(player["row"], SHEET_COLUMNS["ELIMINATION_ORDER"] + 1, str(elimination_order))

        # Invalider le cache pour forcer le rechargement
        invalidate_players_cache() 

        # 2. Si le joueur a une cible, il faut la réaffecter à son assassin
        if player.get("target"):
            # Trouver l'assassin du joueur (celui qui a ce joueur comme cible)
            assassin = None
            for p in all_players:
                if p.get("target") and player.get("nickname") and p.get("target").lower() == player.get("nickname").lower():
                    assassin = p
                    break

            # Si on a trouvé l'assassin, lui donner la cible du joueur qui abandonne
            # NB: on NE DOIT PAS incrémenter le compteur de kills de l'assassin
            # pour un abandon. On transfère seulement la cible et l'action.
            if assassin:
                sheet.update_cell(assassin["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, player.get("target", ""))
                # plus d'écriture d'action dans la feuille 1

        # 3. Vider la cible actuelle du joueur qui abandonne
        sheet.update_cell(player["row"], SHEET_COLUMNS["CURRENT_TARGET"] + 1, "")
        # plus d'écriture d'action dans la feuille 1

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

    if not current_player.get("is_admin"):
        return jsonify({"success": False, "message": "Accès refusé"}), 403

    players = get_all_players()
    overview = []
    for player in players:
        overview.append(
            {
                "nickname": player.get("nickname", ""),
                "status": (player.get("status") or "alive"),
                "target": player.get("target") or "",
                "action": get_action_for_target(player.get("target")) or "",
                "initial_target": player.get("initial_target") or "",
                "initial_action": "",
                "is_admin": bool(player.get("is_admin")),
            }
        )

    return jsonify({"success": True, "players": overview})

@app.route("/api/podium", methods=["GET"])
def get_podium():
    """Retourne le podium des 3 derniers joueurs (vainqueurs potentiels)"""
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    try:
        players = get_all_players()
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503

    # Filtrer seulement les joueurs actifs (elimination_order >= 0, excluant ceux avec -1 ET les admins)
    active_players = [p for p in players if _parse_int(p.get("elimination_order", "0"), 0) >= 0 and not p.get("is_admin")]
    
    # Filtrer seulement les joueurs vivants parmi les actifs
    alive_players = [p for p in active_players if (p.get("status") or "alive").lower() == "alive"]
    
    # Vérifier si le jeu est terminé (1 ou moins de joueurs vivants actifs)
    game_over = len(alive_players) <= 1
    
    if not game_over:
        return jsonify({"success": True, "game_over": False, "podium": []})
    
    # Le jeu est terminé, créer le podium
    # Podium = les 3 derniers joueurs actifs éliminés (ordre inversé)
    # On prend d'abord les joueurs vivants (gagnants), puis les morts par ordre décroissant d'élimination
    
    dead_active_players = [p for p in active_players if (p.get("status") or "alive").lower() == "dead"]
    
    # Séparer les joueurs morts avec ordre d'élimination valide (> 0)
    dead_with_order = []
    dead_without_order = []
    
    for p in dead_active_players:
        order_str = p.get("elimination_order", "")
        try:
            order_num = int(order_str) if order_str else 0
        except (ValueError, TypeError):
            order_num = 0
        
        if order_num > 0:
            dead_with_order.append(p)
        else:
            dead_without_order.append(p)
    
    # Trier les joueurs morts avec ordre par ordre décroissant (les derniers morts en premier)
    dead_with_order_sorted = sorted(
        dead_with_order,
        key=lambda p: int(p.get("elimination_order", 0) or 0),
        reverse=True
    )
    
    # Créer le podium : vivants d'abord, puis morts avec ordre, puis morts sans ordre
    podium_players = alive_players + dead_with_order_sorted + dead_without_order
    
    # Prendre les 3 premiers pour le podium
    podium = []
    for i, player in enumerate(podium_players[:3]):
        kill_count = player.get("kill_count", 0)
        # S'assurer que kill_count est un entier
        if isinstance(kill_count, str):
            kill_count = _parse_int(kill_count, 0)
        
        podium.append({
            "rank": i + 1,
            "nickname": player.get("nickname", ""),
            "person_photo": player.get("person_photo", ""),
            "feet_photo": player.get("feet_photo", ""),
            "year": player.get("year", ""),
            "status": player.get("status", "alive"),
            "elimination_order": player.get("elimination_order", ""),
            "kill_count": int(kill_count) if kill_count else 0
        })
    
    return jsonify({"success": True, "game_over": True, "podium": podium})

@app.route("/api/podium/kills", methods=["GET"])
def get_kills_podium():
    """Retourne le podium des 3 joueurs avec le plus de kills"""
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    try:
        players = get_all_players()
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503

    # Filtrer seulement les joueurs actifs (elimination_order >= 0)
    active_players = [p for p in players if _parse_int(p.get("elimination_order", "0"), 0) >= 0]
    
    # Filtrer seulement les joueurs vivants parmi les actifs
    alive_players = [p for p in active_players if (p.get("status") or "alive").lower() == "alive"]
    
    # Vérifier si le jeu est terminé
    game_over = len(alive_players) <= 1
    
    if not game_over:
        return jsonify({"success": True, "game_over": False, "podium": []})
    
    # Trier tous les joueurs actifs par nombre de kills décroissant
    players_by_kills = sorted(
        active_players,
        key=lambda p: p.get("kill_count", 0),
        reverse=True
    )
    
    # Grouper par nombre de kills pour attribuer les médailles
    # On prend les 3 groupes de kills différents (or, argent, bronze)
    kill_counts = []
    for player in players_by_kills:
        kill_count = player.get("kill_count", 0)
        if kill_count not in kill_counts:
            kill_counts.append(kill_count)
    
    # Prendre tous les joueurs qui ont l'un des 3 meilleurs scores
    top_3_kill_counts = kill_counts[:3]
    
    podium = []
    for player in players_by_kills:
        kill_count = player.get("kill_count", 0)
        if kill_count in top_3_kill_counts:
            # Déterminer le rang (1=or, 2=argent, 3=bronze) selon le groupe de kills
            rank = top_3_kill_counts.index(kill_count) + 1
            podium.append({
                "rank": rank,
                "nickname": player.get("nickname", ""),
                "person_photo": player.get("person_photo", ""),
                "feet_photo": player.get("feet_photo", ""),
                "year": player.get("year", ""),
                "kill_count": kill_count,
                "status": player.get("status", "alive")
            })
    
    return jsonify({"success": True, "game_over": True, "podium": podium})

# Fonction utilitaire pour récupérer tous les joueurs
def get_all_players():
    """Récupère tous les joueurs avec un cache de 5 secondes"""
    global _players_cache, _players_cache_timestamp
    
    # Vérifier le cache
    now = time.time()
    with _sheet_cache_lock:
        if _players_cache is not None and (now - _players_cache_timestamp) < _players_cache_ttl:
            return _players_cache
    
    try:
        sheet = require_sheet_client()
        data = sheet.get_all_values()
    except Exception as e:
        print(f"[GET_ALL_PLAYERS] Erreur accès sheet: {e}")
        raise ConnectionError(f"Impossible d'accéder au Google Sheet: {str(e)}")
    
    players = []
    # Ignorer la ligne d'en-tête
    for i, row in enumerate(data[1:], 2):
        try:
            if len(row) <= SHEET_COLUMNS["NICKNAME"]:
                continue  # Ignorer les lignes incomplètes

            nickname_raw = row[SHEET_COLUMNS["NICKNAME"]] or ""
            nickname = (nickname_raw or "").strip()

            # Ignorer les lignes sans surnom valide
            if not nickname:
                continue

            status_raw = row[SHEET_COLUMNS["STATUS"]] if len(row) > SHEET_COLUMNS["STATUS"] else "alive"
            status = _normalize_status(status_raw)
            admin_flag_value = row[SHEET_COLUMNS["ADMIN_FLAG"]] if len(row) > SHEET_COLUMNS["ADMIN_FLAG"] else "False"

            year_raw = (row[SHEET_COLUMNS["YEAR"]] or "").strip() if len(row) > SHEET_COLUMNS["YEAR"] else ""
            year = year_raw.upper() if year_raw else ""

            gender = (row[SHEET_COLUMNS["GENDER"]] or "").strip() if len(row) > SHEET_COLUMNS["GENDER"] else ""
            phone = (row[SHEET_COLUMNS["PHONE"]] or "").strip() if len(row) > SHEET_COLUMNS["PHONE"] else ""
            killed_by = (row[SHEET_COLUMNS["KILLED_BY"]] or "").strip() if len(row) > SHEET_COLUMNS["KILLED_BY"] else ""

            elimination_order = (row[SHEET_COLUMNS["ELIMINATION_ORDER"]] or "").strip() if len(row) > SHEET_COLUMNS["ELIMINATION_ORDER"] else ""

            kill_count_raw = (row[SHEET_COLUMNS["KILL_COUNT"]] or "").strip() if len(row) > SHEET_COLUMNS["KILL_COUNT"] else "0"
            kill_count = _parse_int(kill_count_raw, 0)
        except Exception as e:
            print(f"[GET_ALL_PLAYERS] Erreur parsing ligne {i} ({nickname_raw if 'nickname_raw' in locals() else '?'}): {e}")
            import traceback
            traceback.print_exc()
            continue

        players.append({
            "row": i,
            "nickname": nickname,
            "gender": gender,
            "year": year,
            "password": (row[SHEET_COLUMNS["PASSWORD"]] or "").strip() if len(row) > SHEET_COLUMNS["PASSWORD"] else "",
            "person_photo": extract_google_drive_id(row[SHEET_COLUMNS["PERSON_PHOTO"]]) if len(row) > SHEET_COLUMNS["PERSON_PHOTO"] else "",
            "feet_photo": extract_google_drive_id(row[SHEET_COLUMNS["FEET_PHOTO"]]) if len(row) > SHEET_COLUMNS["FEET_PHOTO"] else "",
            "kro_answer": (row[SHEET_COLUMNS["KRO_ANSWER"]] or "").strip() if len(row) > SHEET_COLUMNS["KRO_ANSWER"] else "",
            "before_answer": (row[SHEET_COLUMNS["BEFORE_ANSWER"]] or "").strip() if len(row) > SHEET_COLUMNS["BEFORE_ANSWER"] else "",
            "message": (row[SHEET_COLUMNS["MESSAGE_ANSWER"]] or "").strip() if len(row) > SHEET_COLUMNS["MESSAGE_ANSWER"] else "",
            "challenge_ideas": (row[SHEET_COLUMNS["CHALLENGE_IDEAS"]] or "").strip() if len(row) > SHEET_COLUMNS["CHALLENGE_IDEAS"] else "",
            "target": (row[SHEET_COLUMNS["CURRENT_TARGET"]] or "").strip() if len(row) > SHEET_COLUMNS["CURRENT_TARGET"] else "",
            # action désormais dérivée de la feuille 2
            "action": get_action_for_target((row[SHEET_COLUMNS["CURRENT_TARGET"]] or "").strip() if len(row) > SHEET_COLUMNS["CURRENT_TARGET"] else ""),
            "status": status,
            "killed_by": killed_by,
            "is_admin": _parse_admin_flag(admin_flag_value),
            "phone": phone,
            "elimination_order": elimination_order,
            "kill_count": kill_count,
        })

    # Mettre en cache les résultats
    with _sheet_cache_lock:
        _players_cache = players
        _players_cache_timestamp = time.time()
    
    return players


def _normalize_status(status_value: Optional[str]) -> str:
    if not status_value:
        return "alive"
    normalized = status_value.strip().lower()
    if normalized in {"alive", "dead", "gaveup"}:
        return normalized
    # Ancienne valeur "admin" ou autres variantes
    return "alive"


def _trombi_entry(player: dict, viewer_nickname: Optional[str], include_status: bool, all_players: list = None) -> dict:
    nickname = player.get("nickname", "") or ""
    normalized_status = _normalize_status(player.get("status"))
    person_photo_id = player.get("person_photo", "") or ""
    year = player.get("year", "") or ""
    phone = player.get("phone", "") or ""
    is_admin = bool(player.get("is_admin"))
    
    # Trouver qui a ce joueur comme cible (hunter) et l'action associée
    hunter = ""
    hunter_action = ""
    if include_status and all_players and nickname:
        for p in all_players:
            target = (p.get("target") or "").strip()
            if target and target.lower() == nickname.lower():
                hunter = p.get("nickname", "") or ""
                hunter_action = get_action_for_target(nickname) if include_status else ""
                break
    
    # Si le joueur est mort, chercher l'action que son killer devait faire
    killer_action = ""
    if include_status and normalized_status in {"dead", "gaveup"} and player.get("killed_by"):
        killed_by_name = (player.get("killed_by") or "").strip().lower()
        if killed_by_name:
            killer_action = get_action_for_target(nickname)
    
    return {
        "nickname": nickname,
        "gender": player.get("gender", "") or "",
        "year": year,
        "person_photo": person_photo_id,
        "feet_photo": player.get("feet_photo", "") or "",
        "status": normalized_status if include_status else None,
        "is_self": bool(viewer_nickname and nickname and nickname.lower() == viewer_nickname.lower()),
        "is_admin": is_admin,
        "phone": phone,
        "kro_answer": player.get("kro_answer", "") or "",
        "before_answer": player.get("before_answer", "") or "",
        "target": player.get("target", "") or "" if include_status else "",
        "action": (get_action_for_target(player.get("target")) if include_status else ""),
        "hunter": hunter if include_status else "",
        "hunter_action": hunter_action if include_status else "",
        "killed_by": player.get("killed_by", "") or "" if include_status else "",
        "killer_action": killer_action if include_status else "",
        "kill_count": player.get("kill_count", 0) if include_status else 0,
        "elimination_order": player.get("elimination_order", "") or "" if include_status else "",
        "password": player.get("password", "") or "" if include_status else "",
    }


def _viewer_can_see_status(viewer_status: Optional[str], is_admin: bool, all_players: list = None) -> bool:
    """
    Détermine si le viewer peut voir les statuts et infos détaillées.
    - Les admins peuvent toujours voir
    - Les non-admins peuvent voir si la partie est terminée (1 ou moins de joueurs vivants)
    """
    if is_admin:
        return True
    
    # Vérifier si la partie est terminée (1 ou moins de joueurs non-admin vivants)
    if all_players:
        alive_count = sum(
            1 for p in all_players 
            if not p.get("is_admin") and _normalize_status(p.get("status")) == "alive"
        )
        if alive_count <= 1:
            return True
    
    return False


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Retourne le top 10 des joueurs avec le plus de kills (sans révéler leur statut)"""
    try:
        players = get_all_players()
        
        # Filtrer seulement les joueurs actifs (elimination_order >= 0 ET non-admins)
        active_players = [p for p in players if _parse_int(p.get("elimination_order", "0"), 0) >= 0 and not p.get("is_admin")]
        
        leaderboard = []
        for player in active_players:
            leaderboard.append(
                {
                    "nickname": player.get("nickname", ""),
                    "kill_count": player.get("kill_count", 0),
                    "year": player.get("year", ""),
                    "person_photo": player.get("person_photo", ""),
                    "status": player.get("status", ""),
                    "is_admin": player.get("is_admin", False),
                }
            )

        leaderboard.sort(key=lambda entry: (-entry["kill_count"], entry["nickname"].lower()))

        # Renvoyer tous les joueurs (le frontend fera le tri pour l'affichage)
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
        print(f"[TROMBI] Erreur de connexion get_player_by_nickname: {e}")
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"[TROMBI] Erreur inattendue get_player_by_nickname: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500

    if not viewer:
        session.clear()
        return jsonify({"success": False, "message": "Joueur non trouvé"}), 404

    try:
        players = get_all_players()
    except ConnectionError as e:
        print(f"[TROMBI] Erreur de connexion get_all_players: {e}")
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"[TROMBI] Erreur inattendue get_all_players: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500

    include_status = _viewer_can_see_status(viewer.get("status"), viewer.get("is_admin"), players)

    # Filtrer les joueurs qui participent (elimination_order != -1)
    # Les admins sont inclus même avec elimination_order = -1
    participating_players = [
        p for p in players 
        if bool(p.get("is_admin")) or _parse_int(p.get("elimination_order", "0"), 0) != -1
    ]

    entries = [_trombi_entry(player, viewer.get("nickname"), include_status, players) for player in participating_players]
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
            "is_admin": bool(viewer.get("is_admin")),
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
