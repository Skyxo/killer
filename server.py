import os
import urllib.parse
import socket
import threading
import time
from typing import Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
import csv
import io
from PIL import Image
import tempfile

import gunicorn.app.base
import warnings

# Réduire le bruit des avertissements de dépréciation dans la console
warnings.filterwarnings("ignore", category=DeprecationWarning)

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

# Contrôle de verbosité des logs ACTIONS_MAP
ACTIONS_VERBOSE = _env_flag_is_true(os.environ.get("VERBOSE_ACTIONS_LOG"))

# Fichiers CSV locaux
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PLAYERS_FILE = os.path.join(BASE_DIR, "data", "players.csv")
CSV_DEFIS_FILE = os.path.join(BASE_DIR, "data", "defis.csv")
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")

# Auto-détection des exports Google Form si players.csv/defis.csv absents
_data_dir = os.path.join(BASE_DIR, "data")
if not os.path.exists(CSV_PLAYERS_FILE):
    try:
        for fname in os.listdir(_data_dir):
            if fname.endswith(".csv") and ("Réponses au formulaire" in fname or fname == "formulaire.csv"):
                if fname == "formulaire.csv":
                    CSV_PLAYERS_FILE = os.path.join(_data_dir, fname)
                    break
                CSV_PLAYERS_FILE = os.path.join(_data_dir, fname)
    except Exception:
        pass
if not os.path.exists(CSV_DEFIS_FILE):
    try:
        for fname in os.listdir(_data_dir):
            if fname.endswith(".csv") and "defis" in fname.lower():
                CSV_DEFIS_FILE = os.path.join(_data_dir, fname)
                break
    except Exception:
        pass

# Détection du dossier des fichiers uploadés
# Schéma final: data/images/{tetes,pieds}
UPLOADS_ROOT_DIR = os.path.join(_data_dir, "images")
os.makedirs(os.path.join(UPLOADS_ROOT_DIR, "tetes"), exist_ok=True)
os.makedirs(os.path.join(UPLOADS_ROOT_DIR, "pieds"), exist_ok=True)

PHOTOS_LINKS_CSV = os.path.join(_data_dir, "photos_links.csv")

# Créer les répertoires nécessaires
os.makedirs(os.path.dirname(CSV_PLAYERS_FILE), exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Verrous pour l'accès aux CSV
_csv_players_lock = threading.Lock()
_csv_defis_lock = threading.Lock()

# Cache pour mapping lien->nom de fichier drive
_photos_link_to_name = None

def _load_photos_links_map():
    global _photos_link_to_name
    if _photos_link_to_name is not None:
        return _photos_link_to_name
    mapping = {}
    try:
        if os.path.exists(PHOTOS_LINKS_CSV):
            with open(PHOTOS_LINKS_CSV, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    plink = (row.get('person_photo_link') or '').strip()
                    pname = (row.get('person_photo_name') or '').strip()
                    flink = (row.get('feet_photo_link') or '').strip()
                    fname = (row.get('feet_photo_name') or '').strip()
                    if plink and pname:
                        mapping[plink] = pname
                    if flink and fname:
                        mapping[flink] = fname
    except Exception:
        mapping = {}
    _photos_link_to_name = mapping
    return mapping

def _find_local_upload_by_basename(base_name: str, prefer_feet: bool) -> str:
    if not UPLOADS_ROOT_DIR or not base_name:
        return ""
    name_wo_ext = os.path.splitext(base_name)[0]
    # Normalisation simple pour comparaison tolérante
    def _norm(s: str) -> str:
        try:
            return unicodedata.normalize("NFKC", s or "").casefold()
        except Exception:
            return (s or "").lower()
    name_norm = _norm(name_wo_ext)
    # Collect subdirs
    subdirs = []
    try:
        for sub in os.listdir(UPLOADS_ROOT_DIR):
            full = os.path.join(UPLOADS_ROOT_DIR, sub)
            if os.path.isdir(full):
                subdirs.append(sub)
    except Exception:
        return ""
    # Prioritize subdirs by type
    prioritized = []
    for sub in subdirs:
        low = sub.lower()
        if prefer_feet and ("pieds" in low):
            prioritized.insert(0, sub)
        elif (not prefer_feet) and ("tetes" in low or "tête" in low or "tetes" in low or "neuillesque" in low or "jeu" in low):
            prioritized.insert(0, sub)
        else:
            prioritized.append(sub)
    # Search files
    for sub in prioritized:
        try:
            for fname in os.listdir(os.path.join(UPLOADS_ROOT_DIR, sub)):
                file_base = os.path.splitext(fname)[0]
                if name_norm and (name_norm in _norm(file_base)):
                    return f"{sub}/{fname}"
        except Exception:
            continue
    return ""

def _resolve_local_photo_url(original_link: str, prefer_feet: bool) -> str:
    if not original_link:
        return ""
    mapping = _load_photos_links_map()
    drive_name = mapping.get(original_link, "")
    candidate_rel = _find_local_upload_by_basename(drive_name, prefer_feet)
    if candidate_rel:
        # Encoder l'URL pour gérer espaces/accents/parenthèses
        return f"/uploads/{urllib.parse.quote(candidate_rel)}"
    return ""

# Helper: sanitize nickname to basename used by renaming
def _sanitize_basename(nickname: str) -> str:
    try:
        s = unicodedata.normalize("NFKC", (nickname or "").strip())
    except Exception:
        s = (nickname or "").strip()
    s = s.replace("/", "-").replace("\\", "-")
    s = "_".join(s.split())
    return s[:200]

def _choose_uploads_subdir(prefer_feet: bool) -> str:
    if not UPLOADS_ROOT_DIR:
        return ""
    try:
        subdirs = [d for d in os.listdir(UPLOADS_ROOT_DIR) if os.path.isdir(os.path.join(UPLOADS_ROOT_DIR, d))]
    except Exception:
        subdirs = []
    chosen = ""
    for sub in subdirs:
        low = sub.lower()
        if prefer_feet and ("pieds" in low):
            return sub
        if (not prefer_feet) and ("tetes" in low or "tête" in low or "neuillesque" in low or "jeu" in low):
            chosen = sub
    if not chosen and subdirs:
        chosen = subdirs[0]
    return chosen

def _expected_local_photo_url(nickname: str, prefer_feet: bool) -> str:
    if not UPLOADS_ROOT_DIR:
        return ""
    base = _sanitize_basename(nickname)
    filename = f"{base}_pieds.jpg" if prefer_feet else f"{base}.jpg"
    sub = _choose_uploads_subdir(prefer_feet)
    if not sub:
        return ""
    fpath = os.path.join(UPLOADS_ROOT_DIR, sub, filename)
    if os.path.exists(fpath):
        return f"/uploads/{urllib.parse.quote(sub + '/' + filename)}"
    return ""

# Helper to fetch CSV values by multiple possible keys
def _get_csv_value(row: dict, keys: list) -> str:
    for k in keys:
        try:
            v = row.get(k)
        except Exception:
            v = None
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""

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
_players_cache_ttl = 30.0  # 30 secondes de cache pour les données joueurs (optimisé pour charge)

# Cache pour la feuille 2 (mapping Surnom -> Défi ciblé)
_actions_map_cache = None
_actions_map_cache_timestamp = 0.0
_actions_map_cache_ttl = 30.0  # 30 secondes pour réduire les appels API

# ========== FONCTIONS CSV LOCALES ==========

def read_csv_players():
    """Lit le fichier CSV des joueurs et retourne une liste de dictionnaires"""
    if not os.path.exists(CSV_PLAYERS_FILE):
        return []
    
    with _csv_players_lock:
        with open(CSV_PLAYERS_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            return list(reader)

def write_csv_players(players_data):
    """Écrit la liste de joueurs dans le fichier CSV"""
    if not players_data:
        return
    
    with _csv_players_lock:
        with open(CSV_PLAYERS_FILE, 'w', encoding='utf-8', newline='') as f:
            # Utiliser les clés du premier élément comme en-têtes
            fieldnames = list(players_data[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players_data)

def update_csv_player(row_index, updates):
    """Met à jour un joueur spécifique dans le CSV (row_index est 1-based, 1=première ligne de données)"""
    players = read_csv_players()
    if 0 < row_index <= len(players):
        for key, value in updates.items():
            players[row_index - 1][key] = str(value)
        write_csv_players(players)

def update_csv_player_by_nickname(nickname, updates):
    """Met à jour un joueur par son surnom dans le CSV"""
    players = read_csv_players()
    nickname_lower = nickname.lower()
    
    for i, player in enumerate(players):
        player_nickname = player.get("Surnom (le VRAI, pour pouvoir vous identifier)", "").strip()
        if _normalize_name(player_nickname) == _normalize_name(nickname):
            for key, value in updates.items():
                players[i][key] = str(value)
            write_csv_players(players)
            return True
    return False

def batch_update_csv_players(updates_list):
    """Met à jour plusieurs joueurs en une seule opération
    updates_list: liste de tuples (nickname, updates_dict)
    """
    players = read_csv_players()
    
    for nickname, updates in updates_list:
        for i, player in enumerate(players):
            player_nickname = player.get("Surnom (le VRAI, pour pouvoir vous identifier)", "").strip()
            if _normalize_name(player_nickname) == _normalize_name(nickname):
                for key, value in updates.items():
                    players[i][key] = str(value)
                break
    
    write_csv_players(players)

def read_csv_defis():
    """Lit le fichier CSV des défis et retourne un dictionnaire {nickname_lower: action}"""
    if not os.path.exists(CSV_DEFIS_FILE):
        return {}
    
    with _csv_defis_lock:
        with open(CSV_DEFIS_FILE, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            actions_map = {}
            for row in reader:
                nickname = (row.get('Surnom') or '').strip()
                action = (row.get('Défi ciblé') or '').strip()
                if nickname:
                    actions_map[nickname.lower()] = action
            return actions_map

def write_csv_defis(actions_map):
    """Écrit le mapping des défis dans le fichier CSV"""
    with _csv_defis_lock:
        with open(CSV_DEFIS_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Surnom', 'Défi ciblé'])
            writer.writeheader()
            for nickname, action in actions_map.items():
                writer.writerow({'Surnom': nickname, 'Défi ciblé': action})

def download_and_compress_image(drive_id, nickname):
    """Télécharge une image depuis Google Drive et la compresse"""
    if not drive_id:
        return None
    
    try:
        # URL de téléchargement Google Drive
        url = f"https://drive.google.com/uc?export=download&id={drive_id}"
        
        # Télécharger l'image
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"Erreur lors du téléchargement de l'image {drive_id}: {response.status_code}")
            return None
        
        # Ouvrir l'image avec PIL
        img = Image.open(io.BytesIO(response.content))
        
        # Convertir en RGB si nécessaire
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Redimensionner l'image (max 800x800)
        max_size = 800
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Sauvegarder l'image compressée
        filename = f"{nickname}_{drive_id}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        img.save(filepath, 'JPEG', quality=85, optimize=True)
        
        return filename
    
    except Exception as e:
        print(f"Erreur lors de la compression de l'image {drive_id}: {e}")
        return None

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
    """Lit le CSV des défis et retourne un dict {nickname_lower: action_str}. (CSV uniquement)"""
    cache_ttl = _actions_map_cache_ttl
    cached = _get_cached_actions_map(cache_ttl)
    if cached is not None:
        return cached

    actions_map = read_csv_defis() or {}

    if ACTIONS_VERBOSE:
        print(f"[ACTIONS_MAP] Total mappings depuis CSV: {len(actions_map)}")

    _store_actions_map_in_cache(actions_map)
    return actions_map


def get_action_for_target(target_nickname: Optional[str]) -> str:
    if not target_nickname:
        return ""
    actions = get_actions_map()
    if not isinstance(actions, dict):
        return ""
    return actions.get((target_nickname or "").strip().lower(), "")


# Fonction auxiliaire pour obtenir les données d'un joueur par son surnom
def get_player_by_nickname(nickname):
    # Utiliser get_all_players qui a le fallback CSV
    all_players = get_all_players()

    target_nickname = _normalize_name(nickname)

    # Chercher le joueur dans la liste
    for player in all_players:
        if _normalize_name(player.get("nickname", "")) == target_nickname:
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

@app.route("/images/<path:filename>")
def serve_image(filename):
    """Sert les images compressées depuis le répertoire local"""
    return send_from_directory(IMAGES_DIR, filename)

@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    """Sert les fichiers issus des 'File responses' (si présents)."""
    if not UPLOADS_ROOT_DIR:
        return jsonify({"success": False, "message": "Uploads non configurés"}), 404
    # Décoder l'URL pour gérer les accents/espaces
    decoded = urllib.parse.unquote(filename)
    response = send_from_directory(UPLOADS_ROOT_DIR, decoded)
    # Ajouter headers anti-cache pour éviter les problèmes de cache navigateur
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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
                # Mettre à jour la cible dans le CSV
                update_csv_player_by_nickname(player["nickname"], {
                    "Cible actuelle": next_target["nickname"]
                })
                
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
                # Mettre à jour la cible dans le CSV avec verrou
                with _csv_players_lock:
                    update_csv_player_by_nickname(player["nickname"], {
                        "Cible actuelle": next_target["nickname"]
                    })
                # Mettre à jour l'info du joueur en mémoire
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
        
        # Écritures dans le CSV avec verrou
        with _csv_players_lock:
            # Recharger pour réduire les races
            invalidate_players_cache()
            killer_now = get_player_by_nickname(session["nickname"]) or killer
            victim_now = get_player_by_nickname(victim["nickname"]) or victim
            if victim_now and str(victim_now.get("status", "")).lower() == "dead":
                return jsonify({"success": False, "message": "Cette cible est déjà morte"}), 409

            killer_kills = killer_now.get("kill_count", 0)
            
            # Mise à jour batch des deux joueurs
            batch_update_csv_players([
                (killer_now["nickname"], {
                    "Nombre de kills": str(killer_kills + 1),
                    "Cible actuelle": next_target_nickname or ""
                }),
                (victim_now["nickname"], {
                    "État": "dead",
                    "Cible actuelle": "",
                    "Tué par (surnom du killer)": killer_now.get("nickname", "")
                })
            ])

        # Invalider le cache joueurs pour diffuser les changements
        invalidate_players_cache()
        
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
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur lors du kill: {str(e)}"}), 500

@app.route("/api/killed", methods=["POST"])
def killed():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    try:
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
        
        # Écritures dans le CSV avec verrou
        with _csv_players_lock:
            # Relecture actuelle
            invalidate_players_cache()
            me_now = get_player_by_nickname(session["nickname"]) or player
            if str(me_now.get("status", "")).lower() == "dead":
                return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 409

            # Recalculer assassin avec lecture actuelle
            all_now = get_all_players()
            assassin = None
            for p in all_now:
                if p.get("target") and me_now.get("nickname") and p["target"].lower() == me_now["nickname"].lower():
                    assassin = p
                    break

            updates_list = [
                (me_now["nickname"], {
                    "État": "dead",
                    "Ordre d'élimination (-1=ne joue pas, 0=en jeu, >0=éliminé)": str(elimination_order)
                })
            ]
            
            if assassin:
                new_target = me_now.get("target") or ""
                assassin_kills = assassin.get("kill_count", 0)
                updates_list.append((assassin["nickname"], {
                    "Cible actuelle": new_target,
                    "Nombre de kills": str(assassin_kills + 1)
                }))
                updates_list[0][1]["Tué par (surnom du killer)"] = assassin.get("nickname", "")
            
            batch_update_csv_players(updates_list)

        # Invalider le cache pour forcer le rechargement
        invalidate_players_cache()
        
        return jsonify({
            "success": True,
            "message": "Vous avez été marqué comme éliminé"
        })
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"Erreur lors de la déclaration de mort: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur lors de la déclaration: {str(e)}"}), 500

@app.route("/api/giveup", methods=["POST"])
def give_up():
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401
    try:
        # Récupérer le joueur qui abandonne
        player = get_player_by_nickname(session["nickname"])

        if not player:
            return jsonify({"success": False, "message": "Joueur non trouvé"}), 404

        if (player.get("status") or "").lower() == "dead":
            return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 400

        with _csv_players_lock:
            invalidate_players_cache()
            me_now = get_player_by_nickname(session["nickname"]) or player
            if str(me_now.get("status", "")).lower() == "dead":
                return jsonify({"success": False, "message": "Vous êtes déjà mort"}), 409

            all_players = get_all_players()
            existing_orders = [ _parse_int(p.get("elimination_order", ""), 0) for p in all_players if str(p.get("elimination_order", "")).strip() != "" ]
            max_order = max(existing_orders) if existing_orders else 0
            elimination_order = max_order + 1

            updates_list = [
                (me_now["nickname"], {
                    "État": "gaveup",
                    "Ordre d'élimination (-1=ne joue pas, 0=en jeu, >0=éliminé)": str(elimination_order),
                    "Cible actuelle": ""
                })
            ]

            # Si le joueur a une cible, il faut la réaffecter à son assassin (sans incrémenter ses kills)
            if me_now.get("target"):
                assassin = None
                for p in all_players:
                    if p.get("target") and me_now.get("nickname") and p.get("target").lower() == me_now.get("nickname").lower():
                        assassin = p
                        break
                if assassin:
                    # Trouver la prochaine cible vivante si la cible actuelle est morte
                    next_target_nickname = me_now.get("target", "")
                    target_player = get_player_by_nickname(next_target_nickname)
                    
                    if target_player and target_player["status"].lower() in ["dead", "gaveup"]:
                        # La cible est morte ou a abandonné, trouver la prochaine cible vivante
                        alive_target = find_next_alive_target(next_target_nickname, None, all_players)
                        if alive_target:
                            next_target_nickname = alive_target["nickname"]
                        else:
                            next_target_nickname = ""
                    
                    updates_list.append((assassin["nickname"], {
                        "Cible actuelle": next_target_nickname
                    }))

            batch_update_csv_players(updates_list)

        # Invalider le cache pour forcer le rechargement
        invalidate_players_cache()

        return jsonify({
            "success": True,
            "message": "Vous avez abandonné le jeu"
        })
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except Exception as e:
        print(f"Erreur lors de l'abandon: {e}")
        import traceback
        traceback.print_exc()
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
    """Récupère tous les joueurs depuis le CSV local avec un cache de 5 secondes (CSV uniquement)."""
    global _players_cache, _players_cache_timestamp
    
    # Vérifier le cache
    now = time.time()
    with _sheet_cache_lock:
        if _players_cache is not None and (now - _players_cache_timestamp) < _players_cache_ttl:
            return _players_cache
    
    # Lire depuis le CSV local
    csv_data = read_csv_players() or []

    # Parser les données du CSV
    players = []
    for i, player_dict in enumerate(csv_data, 1):
        try:
            nickname = player_dict.get("Surnom (le VRAI, pour pouvoir vous identifier)", "").strip()
            if not nickname:
                continue

            # Avec la normalisation que tu as faite, on privilégie l'attendu strict
            person_local = _expected_local_photo_url(nickname, prefer_feet=False)
            feet_local = _expected_local_photo_url(nickname, prefer_feet=True)
            
            players.append({
                "row": i,
                "nickname": nickname,
                "gender": player_dict.get("Sexe (H/F)", "").strip(),
                "year": player_dict.get("Année (0A, 2A, 3A, etc.)", "").strip().upper(),
                "password": _get_csv_value(player_dict, [
                    "Votre mot de passe (vous devrez vous en SOUVENIR pour jouer, même en BO)",
                    "Votre mot de passe",
                    "Mot de passe",
                ]),
                "person_photo": person_local,
                "feet_photo": feet_local,
                "kro_answer": player_dict.get("Combien y a t il de cars dans une kro ?", "").strip(),
                "before_answer": player_dict.get("Est-ce que c'était mieux avant ?", "").strip(),
                "message": player_dict.get("Un petit mot pour vos brasseurs adorés", "").strip(),
                "challenge_ideas": player_dict.get("Idées de défis", "").strip(),
                "target": player_dict.get("Cible actuelle", "").strip(),
                "action": get_action_for_target(player_dict.get("Cible actuelle", "").strip()),
                "status": _normalize_status(player_dict.get("État", "alive")),
                "killed_by": player_dict.get("Tué par (surnom du killer)", "").strip(),
                "is_admin": _parse_admin_flag(player_dict.get("Admin", "False")),
                "phone": player_dict.get("Téléphone", "").strip(),
                "elimination_order": player_dict.get("Ordre d'élimination (-1=ne joue pas, 0=en jeu, >0=éliminé)", "").strip(),
                "kill_count": _parse_int(player_dict.get("Nombre de kills", "0"), 0),
            })
        except Exception as e:
            print(f"[GET_ALL_PLAYERS] Erreur parsing joueur {i}: {e}")
            import traceback
            traceback.print_exc()
            continue

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

@app.route("/api/admin/sync", methods=["POST"])
def admin_sync():
    """Synchronise les données depuis Google Sheets vers les CSV locaux"""
    if "nickname" not in session:
        return jsonify({"success": False, "message": "Non connecté"}), 401

    try:
        current_player = get_player_by_nickname(session["nickname"])
    except ConnectionError as e:
        return jsonify({"success": False, "message": str(e)}), 503

    if not current_player:
        return jsonify({"success": False, "message": "Joueur non trouvé"}), 404

    if not current_player.get("is_admin"):
        return jsonify({"success": False, "message": "Accès refusé - Administrateur requis"}), 403

    try:
        sheet = require_sheet_client()
        workbook = sheet.spreadsheet
        
        print("[SYNC] Début de la synchronisation...")
        
        # 1. Synchroniser la feuille principale (joueurs)
        print("[SYNC] Téléchargement de la feuille joueurs...")
        data = sheet.get_all_values()
        
        if not data:
            return jsonify({"success": False, "message": "Aucune donnée dans la feuille"}), 500
        
        headers = data[0]
        players_data = []
        images_downloaded = 0
        images_failed = 0
        
        for i, row in enumerate(data[1:], 2):
            if len(row) <= SHEET_COLUMNS["NICKNAME"]:
                continue
            
            nickname = (row[SHEET_COLUMNS["NICKNAME"]] or "").strip()
            if not nickname:
                continue
            
            # Créer un dictionnaire pour ce joueur
            player_dict = {}
            for j, header in enumerate(headers):
                player_dict[header] = row[j] if j < len(row) else ""
            
            # Télécharger et compresser les images
            person_photo_id = extract_google_drive_id(row[SHEET_COLUMNS["PERSON_PHOTO"]]) if len(row) > SHEET_COLUMNS["PERSON_PHOTO"] else ""
            feet_photo_id = extract_google_drive_id(row[SHEET_COLUMNS["FEET_PHOTO"]]) if len(row) > SHEET_COLUMNS["FEET_PHOTO"] else ""
            
            if person_photo_id:
                print(f"[SYNC] Téléchargement image personne pour {nickname}...")
                filename = download_and_compress_image(person_photo_id, f"{nickname}_person")
                if filename:
                    player_dict[headers[SHEET_COLUMNS["PERSON_PHOTO"]]] = filename
                    images_downloaded += 1
                else:
                    images_failed += 1
            
            if feet_photo_id:
                print(f"[SYNC] Téléchargement image pieds pour {nickname}...")
                filename = download_and_compress_image(feet_photo_id, f"{nickname}_feet")
                if filename:
                    player_dict[headers[SHEET_COLUMNS["FEET_PHOTO"]]] = filename
                    images_downloaded += 1
                else:
                    images_failed += 1
            
            players_data.append(player_dict)
        
        # Écrire les données joueurs dans le CSV
        write_csv_players(players_data)
        print(f"[SYNC] {len(players_data)} joueurs synchronisés")
        
        # 2. Synchroniser la feuille des défis
        print("[SYNC] Téléchargement de la feuille défis...")
        try:
            defis_ws = workbook.worksheet("defis")
        except Exception:
            # Fallback sur la 2e feuille par index
            worksheets = workbook.worksheets()
            if len(worksheets) >= 2:
                defis_ws = worksheets[1]
            else:
                print("[SYNC] Aucune feuille défis trouvée, création d'un mapping vide")
                defis_ws = None
        
        if defis_ws:
            defis_data = defis_ws.get_all_values()
            actions_map = {}
            
            for row in defis_data[1:]:  # Ignorer l'en-tête
                if not row:
                    continue
                nickname = (row[0] or "").strip()
                action = (row[1] if len(row) > 1 else "").strip()
                if nickname:
                    actions_map[nickname] = action
            
            # Écrire le CSV des défis
            with _csv_defis_lock:
                with open(CSV_DEFIS_FILE, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['Surnom', 'Défi ciblé'])
                    writer.writeheader()
                    for nickname, action in actions_map.items():
                        writer.writerow({'Surnom': nickname, 'Défi ciblé': action})
            
            print(f"[SYNC] {len(actions_map)} défis synchronisés")
        
        # Invalider les caches pour forcer le rechargement
        invalidate_players_cache()
        global _actions_map_cache, _actions_map_cache_timestamp
        with _sheet_cache_lock:
            _actions_map_cache = None
            _actions_map_cache_timestamp = 0.0
        
        print("[SYNC] Synchronisation terminée!")
        
        return jsonify({
            "success": True,
            "message": "Synchronisation réussie",
            "stats": {
                "players": len(players_data),
                "defis": len(actions_map) if defis_ws else 0,
                "images_downloaded": images_downloaded,
                "images_failed": images_failed
            }
        })
        
    except Exception as e:
        import traceback
        print(f"[SYNC] Erreur: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Erreur lors de la synchronisation: {str(e)}"}), 500

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
    # Pour workers async (gevent): cpu_count * 4-8
    # Pour workers sync: cpu_count * 2 + 1
    return max(1, cpu_count * 4)


def _build_gunicorn_options() -> dict:
    host = os.environ.get("HOST", os.environ.get("BIND", "0.0.0.0"))
    port = _coerce_positive_int(os.environ.get("PORT"), 5000)
    workers = _coerce_positive_int(
        os.environ.get("GUNICORN_WORKERS"), _default_worker_count()
    )
    timeout = _coerce_positive_int(os.environ.get("GUNICORN_TIMEOUT"), 120)
    keepalive = _coerce_positive_int(os.environ.get("GUNICORN_KEEPALIVE"), 5)
    
    # Worker class: gevent pour async (meilleur pour I/O), sync par défaut
    worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")
    # Nombre de connexions simultanées par worker gevent
    worker_connections = _coerce_positive_int(os.environ.get("GUNICORN_WORKER_CONNECTIONS"), 1000)

    return {
        "bind": f"{host}:{port}",
        "workers": workers,
        "worker_class": worker_class,
        "worker_connections": worker_connections,
        "timeout": timeout,
        "keepalive": keepalive,
        # Désactiver les access logs par défaut pour éviter le bruit en console.
        # Pour réactiver: export GUNICORN_ACCESS_LOG="-" ou vers un fichier.
        "accesslog": (os.environ.get("GUNICORN_ACCESS_LOG") or None),
        "errorlog": os.environ.get("GUNICORN_ERROR_LOG", "-"),
        "loglevel": os.environ.get("GUNICORN_LOGLEVEL", "info"),
        "worker_tmp_dir": os.environ.get("GUNICORN_WORKER_TMP_DIR"),
        # Précharger l'app désactivé pour éviter les problèmes avec Google Sheets
        "preload_app": False,
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
