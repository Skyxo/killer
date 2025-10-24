#!/bin/bash
# Script de mise à jour rapide sur Zomro
# Usage: ./deploy_quick.sh

set -e  # Arrêter en cas d'erreur

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ZOMRO_IP="188.137.182.53"
ZOMRO_USER="root"
DEST_DIR="/var/www/killer"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🚀 Mise à jour rapide sur Zomro    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 1. Copier les fichiers modifiés
echo -e "${BLUE}📤 Copie des fichiers sur le serveur...${NC}"

echo "  → server.py"
scp server.py $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || exit 1

echo "  → client/app.js"
scp client/app.js $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || exit 1

echo "  → client/style.css"
scp client/style.css $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || exit 1

echo "  → client/index.html"
scp client/index.html $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || exit 1

# 2. Copier les données si elles existent
if [ -d "data" ]; then
    echo -e "${BLUE}📦 Copie des données (CSV + images)...${NC}"
    scp -r data $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || {
        echo -e "${YELLOW}⚠️  Avertissement: Impossible de copier les données${NC}"
    }
fi

# 3. Redémarrer l'application
echo -e "${BLUE}🔄 Redémarrage de l'application...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "systemctl restart killer" || exit 1

# 4. Attendre que l'application démarre
echo -e "${BLUE}⏳ Attente du démarrage...${NC}"
sleep 3

# 5. Vérifier que l'application répond
echo -e "${BLUE}🔍 Vérification de l'état...${NC}"
if ssh $ZOMRO_USER@$ZOMRO_IP "curl -sf http://localhost:8080/health > /dev/null"; then
    echo -e "${GREEN}✅ Application déployée avec succès !${NC}"
    echo ""
    echo -e "${GREEN}🌐 Accessible sur : http://$ZOMRO_IP:8080${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  L'application ne répond pas encore...${NC}"
    echo "Vérifiez les logs avec :"
    echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -50 /var/log/killer.log'"
fi

echo ""
echo -e "${BLUE}📊 Pour voir les logs en temps réel :${NC}"
echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -f /var/log/killer.log'"

