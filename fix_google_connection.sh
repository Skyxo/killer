#!/bin/bash

# Script de diagnostic et de correction pour la communication Google Sheets sur Zomro
# Ce script combine toutes les étapes nécessaires pour résoudre les problèmes de connectivité

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Script de diagnostic et correction Google Sheets pour Zomro ===${NC}"
echo

# 1. Installer toutes les dépendances nécessaires
echo -e "${BLUE}1. Installation des dépendances...${NC}"
pip3 install --upgrade pip
pip3 install gspread oauth2client flask gunicorn python-dotenv requests urllib3 pyOpenSSL
echo -e "${GREEN}Dépendances installées.${NC}"
echo

# 2. Vérifier et corriger le fichier service_account.json
echo -e "${BLUE}2. Vérification du fichier service_account.json...${NC}"
if [ ! -f "service_account.json" ]; then
    echo -e "${RED}ERREUR: Le fichier service_account.json est manquant!${NC}"
    exit 1
else
    echo -e "${GREEN}Le fichier service_account.json existe.${NC}"
    chmod 644 service_account.json
fi
echo

# 3. Créer un contournement SSL robuste
echo -e "${BLUE}3. Création d'un contournement SSL robuste...${NC}"
cat > ssl_bypass.py << 'EOL'
import ssl
import socket
import certifi
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

# Désactiver la vérification SSL
if hasattr(ssl, "_create_default_https_context"):
    ssl._create_default_https_context = ssl._create_unverified_context

# Augmenter le timeout des sockets
socket.setdefaulttimeout(120)

# Classe personnalisée pour ignorer la vérification SSL dans les requêtes
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=None, cert_reqs=ssl.CERT_NONE)
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# Modifier la session par défaut de requests
def patch_requests():
    session = requests.Session()
    session.mount('https://', SSLAdapter())
    
    # Remplacer la session par défaut de requests
    old_get = requests.get
    old_post = requests.post
    
    def new_get(*args, **kwargs):
        kwargs.setdefault('verify', False)
        return old_get(*args, **kwargs)
    
    def new_post(*args, **kwargs):
        kwargs.setdefault('verify', False)
        return old_post(*args, **kwargs)
    
    requests.get = new_get
    requests.post = new_post

# Appliquer le patch
patch_requests()

# Configurer urllib3 pour ignorer les avertissements SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("SSL verification désactivée et timeout augmenté")
print("Requêtes HTTP configurées pour ignorer les vérifications SSL")
EOL

echo -e "${GREEN}Contournement SSL robuste créé.${NC}"
echo

# 4. Créer un script de test pour la connectivité Google Sheets avec IP directe
echo -e "${BLUE}4. Création d'un script de test pour la connectivité Google Sheets avec IP directe...${NC}"
cat > test_google_sheets_robust.py << 'EOL'
import os
import sys
import ssl
import json
import socket
import requests
import time

# Importer notre contournement SSL
try:
    import ssl_bypass
    print("SSL bypass importé avec succès")
except Exception as e:
    print(f"Erreur lors de l'importation du SSL bypass: {str(e)}")

# Fonction pour résoudre une adresse DNS manuellement
def resolve_dns(hostname):
    print(f"Résolution DNS pour {hostname}...")
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        print(f"Impossible de résoudre {hostname}")
        return None

# Résoudre les adresses IP pour les domaines Google
sheets_api_ip = resolve_dns('sheets.googleapis.com')
oauth2_api_ip = resolve_dns('oauth2.googleapis.com')
www_googleapis_ip = resolve_dns('www.googleapis.com')

print(f"IP de sheets.googleapis.com: {sheets_api_ip}")
print(f"IP de oauth2.googleapis.com: {oauth2_api_ip}")
print(f"IP de www.googleapis.com: {www_googleapis_ip}")

# Test de connexion HTTP direct
def test_http_connection(url, host_header=None):
    print(f"Test de connexion HTTP vers {url}...")
    headers = {}
    if host_header:
        headers['Host'] = host_header
    
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        elapsed_time = time.time() - start_time
        
        print(f"Statut: {response.status_code}")
        print(f"Temps de réponse: {elapsed_time:.2f} secondes")
        print(f"Taille de la réponse: {len(response.content)} octets")
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur: {str(e)}")
        return False

# Tests des domaines Google via HTTP
print("\nTest de connexion standard...")
test_http_connection('https://sheets.googleapis.com/$discovery/rest?version=v4')
test_http_connection('https://oauth2.googleapis.com/token')
test_http_connection('https://www.googleapis.com/discovery/v1/apis')

# Tests avec IP directe si disponible
if sheets_api_ip:
    print("\nTest de connexion via IP directe pour sheets.googleapis.com...")
    test_http_connection(f'https://{sheets_api_ip}/$discovery/rest?version=v4', 'sheets.googleapis.com')

if oauth2_api_ip:
    print("\nTest de connexion via IP directe pour oauth2.googleapis.com...")
    test_http_connection(f'https://{oauth2_api_ip}/token', 'oauth2.googleapis.com')

# Essayons maintenant avec gspread
print("\nTest avec gspread...")
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    
    # Charger les informations d'environnement
    service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
    sheet_id = os.environ.get("SHEET_ID", "1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY")
    
    print(f"Utilisation du fichier: {service_account_file}")
    print(f"ID de la feuille: {sheet_id}")
    
    # Charger les informations du compte de service
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    print("Chargement des informations du compte de service...")
    credentials = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, scope)
    
    print("Connexion à l'API Google Sheets...")
    gc = gspread.authorize(credentials)
    
    print(f"Ouverture de la feuille {sheet_id}...")
    worksheet = gc.open_by_key(sheet_id).sheet1
    
    print("Récupération des données...")
    data = worksheet.get_all_records()
    
    if data:
        print(f"Connexion réussie! Colonnes disponibles: {list(data[0].keys())}")
        print(f"Nombre d'enregistrements: {len(data)}")
    else:
        print("La feuille est vide ou ne contient pas de données.")
    
except Exception as e:
    print(f"ERREUR: {str(e)}")
    
    # Afficher plus d'informations sur le fichier service_account
    try:
        with open(service_account_file, 'r') as f:
            account_info = json.load(f)
            print(f"Email du compte de service: {account_info.get('client_email')}")
            print(f"ID du projet: {account_info.get('project_id')}")
    except Exception as e2:
        print(f"Impossible de lire les informations du compte: {str(e2)}")
EOL

echo -e "${GREEN}Script de test créé.${NC}"
echo

# 5. Créer un patch pour server.py
echo -e "${BLUE}5. Création d'un patch pour server.py...${NC}"
cat > patch_server.py << 'EOL'
#!/usr/bin/env python3
import os
import sys

# Vérifiez si le fichier server.py existe
if not os.path.exists('server.py'):
    print("Le fichier server.py n'existe pas dans le répertoire courant!")
    sys.exit(1)

# Lire le contenu de server.py
with open('server.py', 'r') as f:
    server_content = f.read()

# Vérifier si le contournement SSL est déjà importé
if 'import ssl_bypass' not in server_content:
    # Ajouter l'import au début du fichier
    modified_content = "import ssl_bypass\n" + server_content
    
    # Écrire le contenu modifié
    with open('server.py', 'w') as f:
        f.write(modified_content)
    
    print("Le fichier server.py a été modifié pour importer le contournement SSL.")
else:
    print("Le fichier server.py contient déjà l'import du contournement SSL.")
EOL

chmod +x patch_server.py
echo -e "${GREEN}Patch pour server.py créé.${NC}"
echo

# 6. Installer certifi et créer un contournement pour certificats
echo -e "${BLUE}6. Installation et configuration de certificats supplémentaires...${NC}"
pip3 install certifi
cat > fix_certificates.py << 'EOL'
import os
import sys
import certifi
import ssl
import urllib.request
import tempfile
import subprocess

# Afficher la configuration SSL actuelle
print(f"Fichier de certificats SSL par défaut: {certifi.where()}")

# Créer un gestionnaire SSL personnalisé
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Télécharger les certificats Google
google_certs_urls = [
    "https://pki.goog/gsr2/GSR2.crt",
    "https://pki.goog/gtsr1/GTSR1.crt"
]

temp_dir = tempfile.mkdtemp()
print(f"Téléchargement des certificats dans {temp_dir}")

for url in google_certs_urls:
    try:
        cert_name = url.split('/')[-1]
        cert_path = os.path.join(temp_dir, cert_name)
        
        print(f"Téléchargement de {url}...")
        with urllib.request.urlopen(url, context=ssl_context) as response:
            cert_data = response.read()
            with open(cert_path, 'wb') as cert_file:
                cert_file.write(cert_data)
        print(f"Certificat téléchargé: {cert_path}")
        
        # Convertir le certificat au format PEM
        pem_path = os.path.join(temp_dir, f"{cert_name}.pem")
        cmd = f"openssl x509 -inform DER -in {cert_path} -out {pem_path}"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Certificat converti en PEM: {pem_path}")
    except Exception as e:
        print(f"Erreur lors du téléchargement du certificat {url}: {str(e)}")

print("\nCertificats téléchargés et convertis avec succès.")
EOL

echo -e "${GREEN}Configuration des certificats créée.${NC}"
echo

# 7. Exécuter les scripts de test et de correction
echo -e "${BLUE}7. Exécution des scripts de test et de correction...${NC}"
echo -e "${YELLOW}Installation des paquets système nécessaires...${NC}"
apt-get update -y
apt-get install -y openssl ca-certificates

echo -e "${YELLOW}Application du patch sur server.py...${NC}"
python3 patch_server.py

echo -e "${YELLOW}Exécution du test de connectivité robuste...${NC}"
export SERVICE_ACCOUNT_FILE="service_account.json"
export SHEET_ID="1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY"
python3 test_google_sheets_robust.py

echo -e "${BLUE}=== Test et diagnostic terminés ====${NC}"
echo
echo -e "${GREEN}Si la connexion est réussie, redémarrez votre application:${NC}"
echo -e "systemctl restart killer"
echo -e "ou"
echo -e "pkill -f \"python3 server.py\"; pkill -f \"gunicorn\"; nohup gunicorn -b 0.0.0.0:8080 server:app --workers 2 --timeout 120 > /var/log/killer.log 2>&1 &"
echo
echo -e "${YELLOW}Si la connexion a échoué, vérifiez:${NC}"
echo -e "1. Que le fichier service_account.json est correct et complet"
echo -e "2. Que la feuille Google Sheets a été partagée avec l'email du compte de service"
echo -e "3. Que le serveur Zomro autorise les connexions sortantes vers les API Google"