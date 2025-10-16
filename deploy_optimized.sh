#!/bin/bash

# Script de déploiement optimisé pour les problèmes de connectivité sur Zomro
# À exécuter depuis votre machine locale

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Déploiement optimisé pour Zomro ===${NC}"
echo

# Configuration
ZOMRO_IP="188.137.176.245"
ZOMRO_USER="root"
DEST_DIR="/var/www/killer"

# 1. Créer un dossier temporaire pour le déploiement
echo -e "${BLUE}1. Préparation des fichiers de déploiement...${NC}"
TEMP_DIR=$(mktemp -d)
echo -e "Dossier temporaire: ${TEMP_DIR}"

# 2. Copier les fichiers essentiels dans le dossier temporaire
echo -e "${BLUE}2. Copie des fichiers essentiels...${NC}"
cp server.py requirements.txt service_account.json fix_google_connection.sh $TEMP_DIR/
cp -r client $TEMP_DIR/

# 3. Créer un fichier ssl_bypass.py optimisé
echo -e "${BLUE}3. Création d'un contournement SSL optimisé...${NC}"
cat > $TEMP_DIR/ssl_bypass.py << 'EOL'
import ssl
import socket
import requests
from urllib3.util import connection

# Désactiver la vérification SSL
if hasattr(ssl, "_create_default_https_context"):
    ssl._create_default_https_context = ssl._create_unverified_context

# Augmenter le timeout des sockets
socket.setdefaulttimeout(120)

# DNS mapping personnalisé pour les API Google
_orig_create_connection = connection.create_connection

def patched_create_connection(address, *args, **kwargs):
    """Patcher la création de connexions pour utiliser des IP spécifiques pour certains hôtes"""
    host, port = address
    
    # Mapping d'hôtes vers des IP spécifiques
    hostname_mapping = {
        'sheets.googleapis.com': '142.250.185.138',
        'oauth2.googleapis.com': '142.250.186.170',
        'www.googleapis.com': '216.58.214.202'
    }
    
    if host in hostname_mapping:
        ip = hostname_mapping[host]
        print(f"Connexion à {host} via IP directe {ip}")
        return _orig_create_connection((ip, port), *args, **kwargs)
    
    return _orig_create_connection(address, *args, **kwargs)

# Appliquer le patch
connection.create_connection = patched_create_connection

# Désactiver les avertissements SSL
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

# Configurer requests pour ignorer les vérifications SSL
try:
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    requests.packages.urllib3.disable_warnings()
except:
    pass

print("SSL verification désactivée et timeout augmenté")
print("Connexions DNS optimisées pour les API Google")
EOL

# 4. Créer un fichier .env optimisé
echo -e "${BLUE}4. Création d'un fichier .env optimisé...${NC}"
cat > $TEMP_DIR/.env << 'EOL'
FLASK_SECRET_KEY=$(openssl rand -hex 16)
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY
FLASK_DEBUG=False
REQUESTS_TIMEOUT=120
PORT=8080
EOL

# 5. Créer un script de lancement optimisé
echo -e "${BLUE}5. Création d'un script de lancement optimisé...${NC}"
cat > $TEMP_DIR/start.sh << 'EOL'
#!/bin/bash

# Script pour démarrer l'application avec optimisations pour Zomro
cd /var/www/killer

# Arrêter les instances existantes
pkill -f "python3 server.py" || true
pkill -f "gunicorn" || true
systemctl stop killer || true

# Importer le contournement SSL
python3 -c "
import ssl_bypass
print('SSL bypass activé et connexions optimisées')
"

# Installer ou mettre à jour les dépendances si nécessaire
pip3 install --upgrade pip requests urllib3 certifi gspread oauth2client gunicorn flask python-dotenv

# Démarrer l'application avec Gunicorn
export PYTHONPATH=$PYTHONPATH:/var/www/killer
nohup gunicorn -b 0.0.0.0:8080 server:app --workers 2 --timeout 120 > /var/log/killer.log 2>&1 &

# Vérifier que l'application est en cours d'exécution
sleep 3
ps aux | grep "[g]unicorn\|[p]ython3 server.py"

echo "Application démarrée sur le port 8080"
echo "Pour voir les logs: tail -f /var/log/killer.log"
EOL
chmod +x $TEMP_DIR/start.sh

# 6. Préparer le service systemd optimisé
echo -e "${BLUE}6. Création du service systemd optimisé...${NC}"
cat > $TEMP_DIR/killer.service << 'EOL'
[Unit]
Description=Killer Game Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/killer
ExecStartPre=/usr/bin/python3 -c "import ssl_bypass; print('SSL bypass activé')"
ExecStart=/usr/local/bin/gunicorn -b 0.0.0.0:8080 server:app --workers 2 --timeout 120
Restart=always
StandardOutput=file:/var/log/killer.log
StandardError=file:/var/log/killer.error.log
Environment="SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json"
Environment="SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY"
Environment="PORT=8080"
Environment="PYTHONPATH=/var/www/killer"

[Install]
WantedBy=multi-user.target
EOL

# 7. Modifier server.py pour inclure le contournement SSL
echo -e "${BLUE}7. Modification de server.py pour inclure le contournement SSL...${NC}"
sed -i '1i import ssl_bypass' $TEMP_DIR/server.py

# 8. Copier les fichiers sur le serveur
echo -e "${BLUE}8. Copie des fichiers sur le serveur...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "mkdir -p $DEST_DIR"
scp -r $TEMP_DIR/* $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/
ssh $ZOMRO_USER@$ZOMRO_IP "chmod +x $DEST_DIR/*.sh"

# 9. Exécuter le script de correction de connectivité
echo -e "${BLUE}9. Exécution du script de correction de connectivité...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && chmod +x fix_google_connection.sh && ./fix_google_connection.sh"

# 10. Configurer et démarrer le service
echo -e "${BLUE}10. Configuration et démarrage du service...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && cp killer.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable killer && systemctl restart killer"

# 11. Nettoyage
echo -e "${BLUE}11. Nettoyage...${NC}"
rm -rf $TEMP_DIR

echo -e "${GREEN}=== Déploiement terminé! ===${NC}"
echo -e "L'application devrait être accessible à http://$ZOMRO_IP:8080"
echo -e "Pour vérifier les logs: ssh $ZOMRO_USER@$ZOMRO_IP \"tail -f /var/log/killer.log\""