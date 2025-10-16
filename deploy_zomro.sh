#!/bin/bash
# Script de déploiement pour le serveur Zomro

# Configuration
ZOMRO_SERVER="188.137.176.245"
ZOMRO_USER="root"
REMOTE_DIR="/var/www/killer"
SSH_KEY="$HOME/.ssh/killer"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Déploiement vers le serveur Zomro ===${NC}"
echo

# Vérifier que la clé SSH existe
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}La clé SSH $SSH_KEY n'existe pas.${NC}"
    echo "Veuillez créer une clé SSH ou modifier le chemin dans le script."
    exit 1
fi

# Vérifier la connexion SSH
echo -e "${YELLOW}Test de connexion SSH...${NC}"
ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER "echo 'Connexion SSH réussie'" || {
    echo -e "${RED}Erreur: Impossible de se connecter au serveur via SSH.${NC}"
    exit 1
}
echo -e "${GREEN}Connexion SSH OK${NC}"

# Préparation des fichiers de configuration
echo -e "${YELLOW}Préparation des fichiers de configuration...${NC}"
if [ ! -f "service_account.json" ]; then
    echo -e "${RED}Erreur: Le fichier service_account.json est manquant.${NC}"
    exit 1
fi
if [ ! -f ".env.zomro" ]; then
    echo -e "${RED}Erreur: Le fichier .env.zomro est manquant.${NC}"
    exit 1
fi

# Créer le répertoire distant s'il n'existe pas
echo -e "${YELLOW}Création du répertoire distant...${NC}"
ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER "mkdir -p $REMOTE_DIR $REMOTE_DIR/client $REMOTE_DIR/flask_session"

# Transférer les fichiers
echo -e "${YELLOW}Transfert des fichiers vers le serveur...${NC}"
scp -i $SSH_KEY server.py requirements.txt $ZOMRO_USER@$ZOMRO_SERVER:$REMOTE_DIR/
scp -i $SSH_KEY service_account.json $ZOMRO_USER@$ZOMRO_SERVER:$REMOTE_DIR/
scp -i $SSH_KEY .env.zomro $ZOMRO_USER@$ZOMRO_SERVER:$REMOTE_DIR/.env
scp -i $SSH_KEY client/* $ZOMRO_USER@$ZOMRO_SERVER:$REMOTE_DIR/client/

# Permissions
echo -e "${YELLOW}Configuration des permissions...${NC}"
ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER "chmod 755 $REMOTE_DIR $REMOTE_DIR/client $REMOTE_DIR/flask_session && chmod 644 $REMOTE_DIR/server.py $REMOTE_DIR/requirements.txt $REMOTE_DIR/.env $REMOTE_DIR/service_account.json $REMOTE_DIR/client/*"

# Installation des dépendances
echo -e "${YELLOW}Installation des dépendances...${NC}"
ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER "cd $REMOTE_DIR && pip install -r requirements.txt"

# Test de l'application
echo -e "${YELLOW}Test de la connexion à Google...${NC}"
ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER "cd $REMOTE_DIR && python3 -c \"
import os
from dotenv import load_dotenv
import gspread
from google.oauth2 import service_account

print('Chargement des variables d\'environnement...')
load_dotenv()

print('Vérification du fichier service_account.json...')
service_account_file = os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account.json')
if not os.path.exists(service_account_file):
    print('ERREUR: Fichier service_account.json non trouvé')
    exit(1)
print('Fichier service_account.json trouvé')

print('Tentative de connexion à Google Sheets...')
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
try:
    credentials = service_account.Credentials.from_service_account_file(service_account_file, scopes=scope)
    client = gspread.authorize(credentials)
    print('Connexion réussie à Google Sheets!')
    
    sheet_id = os.environ.get('SHEET_ID')
    if not sheet_id:
        print('AVERTISSEMENT: SHEET_ID manquant')
        exit(1)
        
    print('Tentative d\'ouverture de la feuille...')
    sheet = client.open_by_key(sheet_id).sheet1
    values = sheet.get_values('A1:C2')
    print('Données récupérées avec succès:', values)
    print('Test RÉUSSI: Connexion à Google Sheets OK')
except Exception as e:
    print('ERREUR lors de la connexion à Google Sheets:', str(e))
    exit(1)
\"" || {
    echo -e "${RED}ERREUR: Le test de connexion à Google Sheets a échoué.${NC}"
    echo "Vous pouvez continuer le déploiement, mais l'application risque de ne pas fonctionner correctement."
    echo -n "Continuer quand même ? (o/n) "
    read -r answer
    if [[ "$answer" != "o" && "$answer" != "O" ]]; then
        echo "Déploiement annulé."
        exit 1
    fi
}

# Création du service systemd
echo -e "${YELLOW}Configuration du service systemd...${NC}"
cat > /tmp/killer.service << EOL
[Unit]
Description=Killer Game Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=$REMOTE_DIR
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 -m gunicorn -b 0.0.0.0:5000 server:app --workers 3 --timeout 60
Restart=always
StandardOutput=append:$REMOTE_DIR/killer.log
StandardError=append:$REMOTE_DIR/killer.error.log

[Install]
WantedBy=multi-user.target
EOL

scp -i $SSH_KEY /tmp/killer.service $ZOMRO_USER@$ZOMRO_SERVER:/etc/systemd/system/
rm /tmp/killer.service

# Démarrer le service
echo -e "${YELLOW}Démarrage du service...${NC}"
ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER "systemctl daemon-reload && systemctl enable killer && systemctl restart killer"

echo
echo -e "${GREEN}=== Déploiement terminé ===${NC}"
echo -e "L'application est maintenant accessible à http://$ZOMRO_SERVER:5000/"
echo -e "Pour vérifier le statut du service: ${YELLOW}ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER 'systemctl status killer'${NC}"
echo -e "Pour voir les logs: ${YELLOW}ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER 'tail -f $REMOTE_DIR/killer.log'${NC}"
echo -e "Pour voir les erreurs: ${YELLOW}ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_SERVER 'tail -f $REMOTE_DIR/killer.error.log'${NC}"