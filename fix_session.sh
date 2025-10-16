#!/bin/bash

# Script pour corriger les problèmes de session Flask et le timeout
# À exécuter sur le serveur Zomro

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Correction des problèmes de session Flask ===${NC}"
echo

# 1. Vérifier et nettoyer le dossier de sessions Flask
echo -e "${BLUE}1. Nettoyage des sessions Flask...${NC}"
if [ -d "flask_session" ]; then
    echo "Suppression de l'ancien dossier flask_session..."
    rm -rf flask_session
fi
mkdir -p flask_session
chmod -R 777 flask_session
echo -e "${GREEN}Dossier flask_session nettoyé et recréé.${NC}"
echo

# 2. Vérifier et corriger le fichier .env
echo -e "${BLUE}2. Vérification du fichier .env...${NC}"
if [ ! -f ".env" ]; then
    echo "Création du fichier .env..."
    cat > .env << EOL
FLASK_SECRET_KEY=$(openssl rand -hex 16)
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY
FLASK_DEBUG=False
PORT=8080
SESSION_TYPE=filesystem
SESSION_FILE_DIR=/var/www/killer/flask_session
SESSION_PERMANENT=False
SESSION_USE_SIGNER=True
EOL
else
    echo "Mise à jour du fichier .env..."
    grep -q "SESSION_TYPE" .env || echo "SESSION_TYPE=filesystem" >> .env
    grep -q "SESSION_FILE_DIR" .env || echo "SESSION_FILE_DIR=/var/www/killer/flask_session" >> .env
    grep -q "SESSION_PERMANENT" .env || echo "SESSION_PERMANENT=False" >> .env
    grep -q "SESSION_USE_SIGNER" .env || echo "SESSION_USE_SIGNER=True" >> .env
    grep -q "FLASK_SECRET_KEY" .env || echo "FLASK_SECRET_KEY=$(openssl rand -hex 16)" >> .env
fi
echo -e "${GREEN}Fichier .env configuré.${NC}"
echo

# 3. Modifier server.py pour corriger les problèmes de session
echo -e "${BLUE}3. Modification de server.py pour améliorer la gestion des sessions...${NC}"
if [ -f "server.py" ]; then
    # Créer une sauvegarde
    cp server.py server.py.bak
    
    # Modification pour ajouter des configurations de session
    echo "Ajout des configurations de session dans server.py..."
    
    # Vérifier si les imports nécessaires sont présents
    if ! grep -q "from flask_session import Session" server.py; then
        sed -i '1 s/^/from flask_session import Session\n/' server.py
    fi
    
    # Remplacer le code de configuration de l'app
    sed -i '/app = Flask/,/app.secret_key/{
        /app = Flask/ b
        /app.secret_key/! d
    }' server.py
    
    # Ajouter la nouvelle configuration après la ligne app = Flask
    sed -i '/app = Flask/ a \
# Charger les configurations\
app.config["SESSION_TYPE"] = os.environ.get("SESSION_TYPE", "filesystem")\
app.config["SESSION_FILE_DIR"] = os.environ.get("SESSION_FILE_DIR", "/var/www/killer/flask_session")\
app.config["SESSION_PERMANENT"] = os.environ.get("SESSION_PERMANENT", "False").lower() == "true"\
app.config["SESSION_USE_SIGNER"] = os.environ.get("SESSION_USE_SIGNER", "True").lower() == "true"\
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")\
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # Session expirée après 1 heure\
Session(app)  # Initialiser la gestion de session' server.py
    
    # Ajouter un délai augmenté pour les requêtes
    sed -i '/import gspread/a \
# Augmenter le timeout pour les requêtes\
import socket\
socket.setdefaulttimeout(60)' server.py
    
    echo -e "${GREEN}Modifications appliquées à server.py.${NC}"
else
    echo -e "${RED}ERREUR: Fichier server.py introuvable!${NC}"
fi
echo

# 4. Installer les dépendances nécessaires
echo -e "${BLUE}4. Installation des dépendances...${NC}"
pip install Flask-Session
echo -e "${GREEN}Dépendances installées.${NC}"
echo

# 5. Redémarrer l'application
echo -e "${BLUE}5. Redémarrage de l'application...${NC}"
pkill -f "python3 server.py" || true
pkill -f "gunicorn" || true

echo "Démarrage de l'application avec Gunicorn..."
nohup gunicorn -b 0.0.0.0:8080 server:app --workers 2 --timeout 120 > /var/log/killer.log 2>&1 &

# Vérifier que l'application est en cours d'exécution
sleep 3
ps aux | grep "[g]unicorn"
echo -e "${GREEN}Application redémarrée.${NC}"
echo

echo -e "${BLUE}=== Configuration terminée ===${NC}"
echo -e "L'application devrait maintenant fonctionner correctement."
echo -e "Pour vérifier les logs: tail -f /var/log/killer.log"
echo -e "Accédez à l'application via: http://188.137.176.245:8080"