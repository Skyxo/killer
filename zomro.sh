#!/bin/bash
# Script de déploiement consolidé pour Zomro
# Ce script combine les fonctionnalités de tous les scripts précédents

# Couleurs pour une meilleure lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Script de déploiement consolidé pour Zomro ===${NC}"
echo

# Configuration
ZOMRO_IP="188.137.182.53"
ZOMRO_USER="root"
SSH_KEY="~/.ssh/id_ed25519"  # Utilisation de la clé existante
DEST_DIR="/var/www/killer"
PORT=8080

# Fonction pour afficher l'aide
show_help() {
    echo "Usage: $0 [option]"
    echo "Options:"
    echo "  deploy     Déploie l'application sur le serveur Zomro"
    echo "  test       Teste la connectivité aux API Google"
    echo "  check      Vérifie les ports utilisés sur le serveur"
    echo "  fix        Exécute les correctifs SSL sur le serveur"
    echo "  clean      Nettoie les fichiers temporaires locaux"
    echo "  help       Affiche cette aide"
    echo
    echo "Exemples:"
    echo "  $0 deploy  # Déploie l'application sur le serveur"
    echo "  $0 test    # Teste la connectivité aux API Google"
}

# Fonction pour nettoyer les fichiers temporaires
clean_temp_files() {
    echo -e "${BLUE}Nettoyage des fichiers temporaires...${NC}"
    rm -rf /home/charl/killer/flask_session/* 2>/dev/null
    find /home/charl/killer -name "*.pyc" -delete 2>/dev/null
    find /home/charl/killer -name "__pycache__" -type d -exec rm -rf {} +
    echo -e "${GREEN}Nettoyage terminé.${NC}"
}

# Fonction pour vérifier les fichiers essentiels
check_required_files() {
    local missing_files=0
    
    # Vérifier le fichier service_account.json
    if [ ! -f "service_account.json" ]; then
        echo -e "${RED}ERREUR: Fichier service_account.json manquant!${NC}"
        echo "Ce fichier est nécessaire pour l'authentification Google."
        missing_files=1
    else
        echo -e "${GREEN}✓ service_account.json présent${NC}"
    fi
    
    # Vérifier server.py
    if [ ! -f "server.py" ]; then
        echo -e "${RED}ERREUR: Fichier server.py manquant!${NC}"
        missing_files=1
    else
        echo -e "${GREEN}✓ server.py présent${NC}"
    fi
    
    # Vérifier le dossier client
    if [ ! -d "client" ]; then
        echo -e "${RED}ERREUR: Dossier client manquant!${NC}"
        missing_files=1
    else
        echo -e "${GREEN}✓ Dossier client présent${NC}"
    fi
    
    # Vérifier requirements.txt
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}ERREUR: Fichier requirements.txt manquant!${NC}"
        missing_files=1
    else
        echo -e "${GREEN}✓ requirements.txt présent${NC}"
    fi
    
    # Vérifier .env ou .env.zomro
    if [ ! -f ".env" ] && [ ! -f ".env.zomro" ]; then
        echo -e "${YELLOW}AVERTISSEMENT: Fichier .env ou .env.zomro manquant${NC}"
        echo "Création d'un fichier .env.zomro par défaut..."
        cat > .env.zomro << EOL
# Configuration pour le serveur Flask sur Zomro
FLASK_SECRET_KEY=$(openssl rand -hex 16)
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY
FLASK_DEBUG=False
REQUESTS_TIMEOUT=60
PORT=$PORT
EOL
        echo -e "${GREEN}✓ .env.zomro créé${NC}"
    else
        echo -e "${GREEN}✓ Fichier de configuration d'environnement présent${NC}"
    fi
    
    if [ $missing_files -eq 1 ]; then
        return 1
    fi
    return 0
}

# Fonction pour tester la connectivité
test_connectivity() {
    echo -e "${BLUE}Test de connectivité aux API Google...${NC}"
    
    # Test simple avec Python
    python3 -c "
import socket, ssl, sys, urllib.request

# Définir un timeout plus court
socket.setdefaulttimeout(10)

# Désactiver la vérification SSL
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# Domaines à tester
domains = {
    'sheets.googleapis.com': 'https://sheets.googleapis.com/$discovery/rest?version=v4',
    'oauth2.googleapis.com': 'https://oauth2.googleapis.com/token',
    'www.googleapis.com': 'https://www.googleapis.com/discovery/v1/apis'
}

# Résultats
all_ok = True

# Tester chaque domaine
for domain, url in domains.items():
    print(f'Test de {domain}... ', end='', flush=True)
    
    # Test DNS
    try:
        ip = socket.gethostbyname(domain)
        print(f'DNS OK ({ip}), ', end='', flush=True)
    except socket.gaierror as e:
        print(f'DNS échoué ({str(e)}), ', end='', flush=True)
        all_ok = False
    
    # Test HTTP
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f'HTTP OK (status {response.getcode()})')
    except Exception as e:
        print(f'HTTP échoué ({str(e)})')
        all_ok = False

# Résultat final
print()
if all_ok:
    print('✅ Tous les tests ont réussi!')
    sys.exit(0)
else:
    print('❌ Certains tests ont échoué.')
    sys.exit(1)
"
    
    RESULT=$?
    if [ $RESULT -eq 0 ]; then
        echo -e "${GREEN}Tests de connectivité réussis!${NC}"
    else
        echo -e "${RED}Tests de connectivité échoués!${NC}"
        echo "Le pare-feu de Zomro peut bloquer les connexions vers les API Google."
        echo "Consultez la documentation pour des solutions alternatives."
    fi
}

# Fonction pour vérifier les ports sur le serveur distant
check_ports() {
    if [ -z "$1" ]; then
        echo -e "${RED}ERREUR: SSH Command non défini${NC}"
        return 1
    fi
    
    local SSH_COMMAND="$1"
    
    echo -e "${BLUE}Vérification des ports utilisés sur le serveur...${NC}"
    
    # Script à exécuter sur le serveur
    $SSH_COMMAND "bash -c '
echo \"Vérification des processus utilisant le port 5000...\"
if command -v lsof &> /dev/null; then
    lsof -i :5000 || echo \"Aucun processus trouvé avec lsof\"
elif command -v netstat &> /dev/null; then
    netstat -tulpn | grep :5000 || echo \"Aucun processus trouvé avec netstat\"
elif command -v ss &> /dev/null; then
    ss -tulpn | grep :5000 || echo \"Aucun processus trouvé avec ss\"
else
    echo \"Aucun outil disponible pour vérifier les ports\"
fi

echo \"Vérification des processus utilisant le port '$PORT'...\"
if command -v lsof &> /dev/null; then
    lsof -i :$PORT || echo \"Aucun processus trouvé avec lsof\"
elif command -v netstat &> /dev/null; then
    netstat -tulpn | grep :$PORT || echo \"Aucun processus trouvé avec netstat\"
elif command -v ss &> /dev/null; then
    ss -tulpn | grep :$PORT || echo \"Aucun processus trouvé avec ss\"
fi
'"
}

# Fonction pour appliquer les correctifs SSL sur le serveur
fix_ssl() {
    if [ -z "$1" ]; then
        echo -e "${RED}ERREUR: SSH Command non défini${NC}"
        return 1
    fi
    
    local SSH_COMMAND="$1"
    
    echo -e "${BLUE}Application des correctifs SSL sur le serveur...${NC}"
    
    # Script à exécuter sur le serveur
    $SSH_COMMAND "bash -c '
echo \"=== Correction des problèmes SSL ===\"

# Mise à jour des paquets
echo \"1. Mise à jour des certificats CA...\"
apt-get update -y && apt-get install -y ca-certificates openssl

# Mise à jour des certificats
echo \"2. Mise à jour de la base de certificats...\"
update-ca-certificates --fresh

# Création du script de contournement SSL
echo \"3. Création du script de contournement SSL...\"
cat > /var/www/killer/ssl_bypass.py << EOL
import ssl
if hasattr(ssl, \"_create_default_https_context\"):
    ssl._create_default_https_context = ssl._create_unverified_context
print(\"SSL verification désactivée\")
EOL

# Test de connexion
echo \"4. Test de connexion à Google...\"
timeout 10 curl -v https://sheets.googleapis.com/\$discovery/rest?version=v4
'"
}

# Fonction pour déployer l'application
deploy_app() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo -e "${RED}ERREUR: SCP ou SSH Command non définis${NC}"
        return 1
    fi
    
    local SCP_COMMAND="$1"
    local SSH_COMMAND="$2"
    
    echo -e "${BLUE}Déploiement de l'application sur le serveur Zomro...${NC}"
    
    # 1. Créer le répertoire sur le serveur
    echo -e "${BLUE}Création du répertoire sur le serveur...${NC}"
    $SSH_COMMAND "mkdir -p $DEST_DIR" || {
        echo -e "${RED}ERREUR: Impossible de créer le répertoire sur le serveur!${NC}"
        return 1
    }
    
    # 2. Copier les fichiers essentiels
    echo -e "${BLUE}Copie des fichiers essentiels...${NC}"
    $SCP_COMMAND server.py requirements.txt service_account.json $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
        echo -e "${RED}ERREUR: Impossible de copier les fichiers essentiels!${NC}"
        return 1
    }
    
    # 3. Copier le fichier d'environnement
    echo -e "${BLUE}Copie du fichier d'environnement...${NC}"
    if [ -f ".env.zomro" ]; then
        $SCP_COMMAND .env.zomro $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/.env || {
            echo -e "${YELLOW}AVERTISSEMENT: Impossible de copier .env.zomro!${NC}"
        }
    elif [ -f ".env" ]; then
        $SCP_COMMAND .env $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
            echo -e "${YELLOW}AVERTISSEMENT: Impossible de copier .env!${NC}"
        }
    fi
    
    # 4. Copier le dossier client
    echo -e "${BLUE}Copie du dossier client...${NC}"
    $SCP_COMMAND -r client $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
        echo -e "${RED}ERREUR: Impossible de copier le dossier client!${NC}"
        return 1
    }
    
    # 5. Créer le service systemd
    echo -e "${BLUE}Création du service systemd...${NC}"
    $SSH_COMMAND "cat > /etc/systemd/system/killer.service << EOL
[Unit]
Description=Killer Game Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=$DEST_DIR
EnvironmentFile=-$DEST_DIR/.env
Environment=PYTHONUNBUFFERED=1
Environment=SERVICE_ACCOUNT_FILE=$DEST_DIR/service_account.json
Environment=SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY
Environment=PORT=$PORT
ExecStartPre=/bin/mkdir -p $DEST_DIR/flask_session
ExecStart=$DEST_DIR/.venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=file:/var/log/killer.log
StandardError=file:/var/log/killer.error.log

[Install]
WantedBy=multi-user.target
EOL" || {
        echo -e "${YELLOW}AVERTISSEMENT: Impossible de créer le service systemd!${NC}"
    }
    
    # 6. Préparer l'environnement virtuel et installer les dépendances
    echo -e "${BLUE}Création/actualisation de l'environnement virtuel...${NC}"
    $SSH_COMMAND "cd $DEST_DIR && python3 -m venv .venv" || {
        echo -e "${YELLOW}AVERTISSEMENT: Impossible de créer l'environnement virtuel!${NC}"
    }
    echo -e "${BLUE}Installation des dépendances dans l'environnement virtuel...${NC}"
    $SSH_COMMAND "cd $DEST_DIR && $DEST_DIR/.venv/bin/pip install --upgrade pip && $DEST_DIR/.venv/bin/pip install -r requirements.txt" || {
        echo -e "${YELLOW}AVERTISSEMENT: Problème lors de l'installation des dépendances dans l'environnement virtuel!${NC}"
    }
    
    # 7. Créer le script de contournement SSL
    echo -e "${BLUE}Création du script de contournement SSL...${NC}"
    $SSH_COMMAND "cat > $DEST_DIR/ssl_bypass.py << EOL
import ssl
if hasattr(ssl, \"_create_default_https_context\"):
    ssl._create_default_https_context = ssl._create_unverified_context
print(\"SSL verification désactivée\")
EOL" || {
        echo -e "${YELLOW}AVERTISSEMENT: Impossible de créer le script de contournement SSL!${NC}"
    }
    
    # 8. Démarrer le service
    echo -e "${BLUE}Démarrage du service...${NC}"
    $SSH_COMMAND "systemctl daemon-reload && systemctl enable killer && systemctl restart killer" || {
        echo -e "${YELLOW}AVERTISSEMENT: Problème lors du démarrage du service!${NC}"
        echo -e "Tentative de démarrage manuel..."
        $SSH_COMMAND "cd $DEST_DIR && python -c 'import ssl_bypass' && nohup gunicorn -b 0.0.0.0:$PORT server:app --workers 3 --timeout 60 > /var/log/killer.log 2>&1 &"
    }
    
    # 9. Afficher le statut
    echo -e "${BLUE}Vérification du statut...${NC}"
    $SSH_COMMAND "systemctl status killer || ps aux | grep gunicorn"
    
    echo -e "${GREEN}=== Déploiement terminé! ===${NC}"
    echo -e "L'application est accessible à l'adresse: http://$ZOMRO_IP:$PORT"
    echo -e "Pour vérifier les logs: $SSH_COMMAND \"tail -f /var/log/killer.log\""
}

# Vérifier si un argument est fourni
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

# Traiter les arguments
case "$1" in
    deploy)
        # Vérifier les fichiers requis
        check_required_files || exit 1
        
        # Nettoyer les fichiers temporaires
        clean_temp_files
        
        # Configuration SSH - Forcer l'authentification par mot de passe
        echo -e "${YELLOW}Utilisation de l'authentification par mot de passe.${NC}"
        SSH_COMMAND="ssh $ZOMRO_USER@$ZOMRO_IP"
        SCP_COMMAND="scp"
        
        # Déployer l'application
        deploy_app "$SCP_COMMAND" "$SSH_COMMAND"
        ;;
        
    test)
        # Tester la connectivité
        test_connectivity
        ;;
        
    check)
        # Vérifier les ports sur le serveur
        if [ -f "$SSH_KEY" ]; then
            SSH_COMMAND="ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_IP"
        else
            echo -e "${YELLOW}Clé SSH non trouvée à $SSH_KEY. Utilisation de l'authentification par mot de passe.${NC}"
            SSH_COMMAND="ssh $ZOMRO_USER@$ZOMRO_IP"
        fi
        
        check_ports "$SSH_COMMAND"
        ;;
        
    fix)
        # Appliquer les correctifs SSL
        if [ -f "$SSH_KEY" ]; then
            SSH_COMMAND="ssh -i $SSH_KEY $ZOMRO_USER@$ZOMRO_IP"
        else
            echo -e "${YELLOW}Clé SSH non trouvée à $SSH_KEY. Utilisation de l'authentification par mot de passe.${NC}"
            SSH_COMMAND="ssh $ZOMRO_USER@$ZOMRO_IP"
        fi
        
        fix_ssl "$SSH_COMMAND"
        ;;
        
    clean)
        # Nettoyer les fichiers temporaires
        clean_temp_files
        ;;
        
    help|*)
        show_help
        ;;
esac