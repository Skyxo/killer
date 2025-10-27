#!/bin/bash
# Script de mise à jour rapide sur Zomro (SANS réupload des photos)
# Usage: ./deploy_update.sh

set -e  # Arrêter en cas d'erreur

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ZOMRO_IP="188.137.182.53"
ZOMRO_USER="root"
DEST_DIR="/var/www/killer"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   ⚡ MISE À JOUR RAPIDE (sans photos) ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 1. Copier les fichiers de code modifiés
echo -e "${BLUE}📤 Copie des fichiers de code...${NC}"

echo "  → server.py"
scp server.py $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || exit 1

echo "  → client/app.js"
scp client/app.js $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || exit 1

echo "  → client/style.css"
scp client/style.css $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || exit 1

echo "  → client/index.html"
scp client/index.html $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || exit 1

# Copier les autres fichiers du client s'ils existent
if [ -f "client/clear_cache.html" ]; then
    echo "  → client/clear_cache.html"
    scp client/clear_cache.html $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/client/ || true
fi

# 2. Copier uniquement les fichiers CSV (PAS les images)
if [ -d "data" ]; then
    echo -e "${BLUE}📄 Copie des fichiers CSV uniquement (images exclues)...${NC}"
    
    # Copier les fichiers CSV un par un
    for csv_file in data/*.csv; do
        if [ -f "$csv_file" ]; then
            echo "  → $(basename $csv_file)"
            scp "$csv_file" $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/data/ || {
                echo -e "${YELLOW}⚠️  Impossible de copier $csv_file${NC}"
            }
        fi
    done
    
    echo -e "${GREEN}✓ CSV copiés (photos ignorées pour économiser la bande passante)${NC}"
fi

# 3. Mise à jour des dépendances si requirements.txt a changé
echo -e "${BLUE}📦 Vérification des dépendances...${NC}"
# Copier requirements.txt pour vérifier les changements
scp requirements.txt $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/ || true

# Demander si on doit mettre à jour les dépendances
read -p "Mettre à jour les dépendances Python ? (o/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo -e "${BLUE}⏳ Mise à jour des dépendances...${NC}"
    ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && $DEST_DIR/.venv/bin/pip install --upgrade pip && $DEST_DIR/.venv/bin/pip install -r requirements.txt" || {
        echo -e "${YELLOW}⚠️  Problème lors de la mise à jour des dépendances${NC}"
    }
fi

# 4. Redémarrer l'application
echo -e "${BLUE}🔄 Redémarrage de l'application...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP "systemctl restart killer" || {
    echo -e "${YELLOW}⚠️  Impossible d'utiliser systemctl, tentative de kill manuel...${NC}"
    ssh $ZOMRO_USER@$ZOMRO_IP "pkill -f 'gunicorn.*server:app' || pkill -f 'python.*server.py'"
    sleep 2
    ssh $ZOMRO_USER@$ZOMRO_IP "cd $DEST_DIR && nohup .venv/bin/gunicorn -b 0.0.0.0:8080 server:app --workers 3 --timeout 60 > /var/log/killer.log 2>&1 &"
}

# 5. Attendre que l'application démarre
echo -e "${BLUE}⏳ Attente du démarrage...${NC}"
sleep 3

# 6. Vérifier que l'application répond
echo -e "${BLUE}🔍 Vérification de l'état...${NC}"
if ssh $ZOMRO_USER@$ZOMRO_IP "curl -sf http://localhost:8080/health > /dev/null 2>&1"; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ MISE À JOUR RÉUSSIE !            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🌐 Accessible sur : http://$ZOMRO_IP:8080${NC}"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠️  L'application ne répond pas encore...${NC}"
    echo ""
    echo -e "${RED}Vérifiez les logs avec :${NC}"
    echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -50 /var/log/killer.log'"
    echo ""
fi

echo -e "${BLUE}📊 Pour voir les logs en temps réel :${NC}"
echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -f /var/log/killer.log'"
echo ""

echo -e "${BLUE}💡 Astuce :${NC}"
echo "  • Ce script n'uploade PAS les images pour économiser la bande passante"
echo "  • Pour un déploiement complet avec photos, utilisez : ./deploy_initial.sh"
echo ""

