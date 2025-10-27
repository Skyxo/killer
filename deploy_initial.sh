#!/bin/bash
# Script de déploiement initial complet sur Zomro
# Usage: ./deploy_initial.sh

set -e  # Arrêter en cas d'erreur

# Couleurs pour une meilleure lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🚀 DÉPLOIEMENT INITIAL COMPLET      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Configuration
ZOMRO_IP="188.137.182.53"
ZOMRO_USER="root"
DEST_DIR="/var/www/killer"
PORT=8080

# Vérifier les fichiers essentiels
echo -e "${BLUE}🔍 Vérification des fichiers essentiels...${NC}"

MISSING_FILES=0
# service_account.json n'est plus nécessaire - utilisation de CSV locaux

if [ ! -f "server.py" ]; then
    echo -e "${RED}❌ Fichier server.py manquant!${NC}"
    MISSING_FILES=1
else
    echo -e "${GREEN}✓ server.py${NC}"
fi

if [ ! -d "client" ]; then
    echo -e "${RED}❌ Dossier client manquant!${NC}"
    MISSING_FILES=1
else
    echo -e "${GREEN}✓ Dossier client${NC}"
fi

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Fichier requirements.txt manquant!${NC}"
    MISSING_FILES=1
else
    echo -e "${GREEN}✓ requirements.txt${NC}"
fi

if [ $MISSING_FILES -eq 1 ]; then
    echo -e "${RED}Déploiement annulé: fichiers manquants!${NC}"
    exit 1
fi

# Créer le fichier .env.zomro si nécessaire
if [ ! -f ".env.zomro" ] && [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Création du fichier .env.zomro...${NC}"
    cat > .env.zomro << EOL
# Configuration pour le serveur Flask sur Zomro
FLASK_SECRET_KEY=$(openssl rand -hex 16)
FLASK_DEBUG=False
REQUESTS_TIMEOUT=60
PORT=$PORT
# Note: L'application utilise maintenant des CSV locaux (pas de Google Sheets)
EOL
    echo -e "${GREEN}✓ .env.zomro créé${NC}"
fi

# Nettoyer les fichiers temporaires locaux
echo -e "${BLUE}🧹 Nettoyage des fichiers temporaires locaux...${NC}"
rm -rf flask_session/* 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Nettoyage terminé${NC}"

# 1. Créer le répertoire sur le serveur
echo -e "${BLUE}📁 Création du répertoire sur le serveur...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "mkdir -p $DEST_DIR" || {
    echo -e "${RED}❌ Impossible de créer le répertoire!${NC}"
    exit 1
}

# 2. Copier les fichiers essentiels
echo -e "${BLUE}📤 Copie des fichiers essentiels...${NC}"
echo "  → server.py, requirements.txt"
scp server.py requirements.txt $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
    echo -e "${RED}❌ Échec de la copie!${NC}"
    exit 1
}

# 3. Copier le fichier d'environnement
echo -e "${BLUE}🔑 Copie du fichier d'environnement...${NC}"
if [ -f ".env.zomro" ]; then
    scp .env.zomro $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/.env
elif [ -f ".env" ]; then
    scp .env $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/
fi

# 4. Copier le dossier client
echo -e "${BLUE}🎨 Copie du dossier client...${NC}"
scp -r client $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
    echo -e "${RED}❌ Échec de la copie du dossier client!${NC}"
    exit 1
}

# 5. Copier les données (CSV + images) - DÉPLOIEMENT INITIAL COMPLET
if [ -d "data" ]; then
    echo -e "${BLUE}📦 Copie COMPLÈTE des données (CSV + images)...${NC}"
    echo -e "${YELLOW}⏳ Cela peut prendre du temps...${NC}"
    scp -r data $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
        echo -e "${YELLOW}⚠️  Avertissement: Impossible de copier les données${NC}"
    }
    echo -e "${GREEN}✓ Données copiées${NC}"
fi

# 6. Créer l'environnement virtuel et installer les dépendances
echo -e "${BLUE}🐍 Configuration de l'environnement Python...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && python3 -m venv .venv" || {
    echo -e "${YELLOW}⚠️  Problème avec l'environnement virtuel${NC}"
}

echo -e "${BLUE}📦 Installation des dépendances...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && $DEST_DIR/.venv/bin/pip install --upgrade pip && $DEST_DIR/.venv/bin/pip install -r requirements.txt" || {
    echo -e "${YELLOW}⚠️  Problème lors de l'installation des dépendances${NC}"
}

# 7. Créer le script de contournement SSL
echo -e "${BLUE}🔐 Création du script de contournement SSL...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "cat > $DEST_DIR/ssl_bypass.py << EOL
import ssl
if hasattr(ssl, \"_create_default_https_context\"):
    ssl._create_default_https_context = ssl._create_unverified_context
print(\"SSL verification désactivée\")
EOL"

# 8. Créer le service systemd
echo -e "${BLUE}⚙️  Création du service systemd...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "cat > /etc/systemd/system/killer.service << EOL
[Unit]
Description=Killer Game Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=$DEST_DIR
EnvironmentFile=-$DEST_DIR/.env
Environment=PYTHONUNBUFFERED=1
Environment=PORT=$PORT
ExecStartPre=/bin/mkdir -p $DEST_DIR/flask_session
ExecStart=$DEST_DIR/.venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=file:/var/log/killer.log
StandardError=file:/var/log/killer.error.log

[Install]
WantedBy=multi-user.target
EOL"

# 9. Créer les répertoires nécessaires
echo -e "${BLUE}📂 Création des répertoires nécessaires...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "mkdir -p $DEST_DIR/data/images $DEST_DIR/flask_session"

# 10. Démarrer le service
echo -e "${BLUE}🚀 Démarrage du service...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "systemctl daemon-reload && systemctl enable killer && systemctl restart killer" || {
    echo -e "${YELLOW}⚠️  Problème avec le service systemd${NC}"
    echo -e "${BLUE}Tentative de démarrage manuel...${NC}"
    ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && python -c 'import ssl_bypass' && nohup .venv/bin/gunicorn -b 0.0.0.0:$PORT server:app --workers 3 --timeout 60 > /var/log/killer.log 2>&1 &"
}

# 11. Attendre que l'application démarre
echo -e "${BLUE}⏳ Attente du démarrage...${NC}"
sleep 5

# 12. Vérifier le statut
echo -e "${BLUE}🔍 Vérification du statut...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "systemctl status killer --no-pager" || {
    echo -e "${YELLOW}Service systemd non disponible, vérification des processus...${NC}"
    ssh $ZOMRO_USER@$ZOMRO_IP "ps aux | grep -E 'gunicorn|python.*server.py' | grep -v grep"
}

# 13. Test de connectivité
echo ""
echo -e "${BLUE}🌐 Test de l'application...${NC}"
if ssh $ZOMRO_USER@$ZOMRO_IP "curl -sf http://localhost:$PORT/health > /dev/null 2>&1"; then
    echo -e "${GREEN}✅ Application déployée avec succès !${NC}"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     🎉 DÉPLOIEMENT RÉUSSI !           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🌐 Accessible sur : http://$ZOMRO_IP:$PORT${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  L'application ne répond pas encore...${NC}"
    echo ""
    echo -e "${BLUE}Pour vérifier les logs :${NC}"
    echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -50 /var/log/killer.log'"
    echo ""
    echo -e "${BLUE}Pour voir les logs en temps réel :${NC}"
    echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -f /var/log/killer.log'"
fi

echo ""
echo -e "${BLUE}📌 Commandes utiles :${NC}"
echo "  • Voir les logs      : ssh $ZOMRO_USER@$ZOMRO_IP 'tail -f /var/log/killer.log'"
echo "  • Redémarrer         : ssh $ZOMRO_USER@$ZOMRO_IP 'systemctl restart killer'"
echo "  • Arrêter            : ssh $ZOMRO_USER@$ZOMRO_IP 'systemctl stop killer'"
echo "  • Statut             : ssh $ZOMRO_USER@$ZOMRO_IP 'systemctl status killer'"
echo ""

