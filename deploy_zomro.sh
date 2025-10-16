#!/bin/bash
# Script de déploiement pour le serveur Zomro avec corrections SSL et réseau

# Couleurs pour une meilleure lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Déploiement sur Zomro avec corrections SSL et réseau ===${NC}"
echo

# Configuration
ZOMRO_IP="188.137.176.245"
ZOMRO_USER="root"
SSH_KEY="~/.ssh/killer"
DEST_DIR="/var/www/killer"

# Vérifier que le fichier service_account.json existe
if [ ! -f "service_account.json" ]; then
    echo -e "${RED}ERREUR: Le fichier service_account.json n'existe pas!${NC}"
    echo "Ce fichier est nécessaire pour l'authentification Google."
    exit 1
fi

# Vérifier et créer .env.zomro si nécessaire
if [ ! -f ".env.zomro" ]; then
    echo -e "${YELLOW}Fichier .env.zomro non trouvé. Création...${NC}"
    cat > .env.zomro << EOL
# Configuration pour le serveur Flask sur Zomro
FLASK_SECRET_KEY=$(openssl rand -hex 16)

# Configuration Google Sheets
# Utiliser le chemin absolu pour éviter les problèmes de chemin relatif
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY

# Configuration pour le debug
FLASK_DEBUG=False

# Configuration pour la connexion réseau
REQUESTS_TIMEOUT=60
EOL
    echo -e "${GREEN}Fichier .env.zomro créé avec succès${NC}"
fi

# Préparer les fichiers pour le déploiement
echo -e "${BLUE}Préparation des fichiers...${NC}"

# Vérifier l'existence de la clé SSH
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}Clé SSH non trouvée à $SSH_KEY.${NC}"
    echo "Voulez-vous continuer avec l'authentification par mot de passe? (o/n)"
    read -r answer
    if [[ "$answer" != "o" && "$answer" != "O" ]]; then
        echo "Déploiement annulé."
        exit 1
    fi
    SSH_COMMAND="ssh $ZOMRO_USER@$ZOMRO_IP"
    SCP_COMMAND="scp"
else
    SSH_COMMAND="ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_IP"
    SCP_COMMAND="scp -i $SSH_KEY"
fi

# Créer le répertoire de destination sur le serveur
echo -e "${BLUE}Création du répertoire sur le serveur...${NC}"
$SSH_COMMAND "mkdir -p $DEST_DIR" || {
    echo -e "${RED}ERREUR: Impossible de créer le répertoire sur le serveur!${NC}"
    echo "Vérifiez vos identifiants SSH et réessayez."
    exit 1
}

# Copier les fichiers
echo -e "${BLUE}Copie des fichiers vers le serveur...${NC}"
$SCP_COMMAND server.py requirements.txt fix_ssl.sh test_google_auth.py proxy_config.py $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
    echo -e "${RED}ERREUR: Impossible de copier les fichiers principaux!${NC}"
    exit 1
}

# Copier les fichiers importants
echo -e "${BLUE}Copie des fichiers de configuration...${NC}"
$SCP_COMMAND service_account.json $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
    echo -e "${RED}ERREUR: Impossible de copier service_account.json!${NC}"
    exit 1
}

$SCP_COMMAND .env.zomro $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/.env || {
    echo -e "${RED}ERREUR: Impossible de copier .env.zomro!${NC}"
    exit 1
}

$SCP_COMMAND killer.service $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
    echo -e "${YELLOW}AVERTISSEMENT: Impossible de copier killer.service!${NC}"
}

# Copier le dossier client
echo -e "${BLUE}Copie du dossier client...${NC}"
$SCP_COMMAND -r client $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
    echo -e "${RED}ERREUR: Impossible de copier le dossier client!${NC}"
    exit 1
}

# Exécuter les commandes de configuration sur le serveur
echo -e "${BLUE}Configuration du serveur...${NC}"
$SSH_COMMAND "cd $DEST_DIR && pip install -r requirements.txt && chmod +x fix_ssl.sh test_google_auth.py" || {
    echo -e "${YELLOW}AVERTISSEMENT: Certaines commandes de configuration ont échoué!${NC}"
}

# Exécuter le script de correction SSL
echo -e "${BLUE}Exécution du script de correction SSL...${NC}"
$SSH_COMMAND "cd $DEST_DIR && ./fix_ssl.sh" || {
    echo -e "${YELLOW}AVERTISSEMENT: Le script de correction SSL a rencontré des problèmes!${NC}"
}

# Tester l'authentification Google
echo -e "${BLUE}Test de l'authentification Google...${NC}"
$SSH_COMMAND "cd $DEST_DIR && python test_google_auth.py"

# Configurer et démarrer le service
echo -e "${BLUE}Configuration et démarrage du service...${NC}"
$SSH_COMMAND "cd $DEST_DIR && cp killer.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable killer && systemctl restart killer" || {
    echo -e "${YELLOW}AVERTISSEMENT: Configuration du service échouée!${NC}"
    echo -e "Essai de démarrage manuel de l'application..."
    $SSH_COMMAND "cd $DEST_DIR && nohup gunicorn -b 0.0.0.0:5000 server:app --workers 3 --timeout 60 > /var/log/killer.log 2>&1 &"
}

echo
echo -e "${GREEN}=== Déploiement terminé! ===${NC}"
echo
echo -e "${BLUE}Vérification du statut:${NC}"
$SSH_COMMAND "systemctl status killer || ps aux | grep gunicorn"

echo
echo -e "${BLUE}Pour vérifier les logs:${NC}"
echo "   $SSH_COMMAND \"tail -f /var/log/killer.log\""
echo 
echo -e "${BLUE}Pour accéder à l'application:${NC}"
echo "   http://$ZOMRO_IP:5000"
echo
echo -e "${YELLOW}Si vous rencontrez encore des problèmes:${NC}"
echo "1. Vérifiez les logs: $SSH_COMMAND \"tail -f /var/log/killer.log\""
echo "2. Testez la connectivité: $SSH_COMMAND \"cd $DEST_DIR && python test_google_auth.py\""
echo "3. Vérifiez le pare-feu: $SSH_COMMAND \"iptables -L -n\""
echo "4. Relancez le service: $SSH_COMMAND \"systemctl restart killer\""