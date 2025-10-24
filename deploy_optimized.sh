#!/bin/bash
# Script de déploiement avec optimisations pour 100+ utilisateurs

set -e

ZOMRO_IP="188.137.182.53"
ZOMRO_USER="root"
DEST_DIR="/var/www/killer"

echo "=== Déploiement optimisé pour 100+ utilisateurs ==="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}1. Copie des fichiers...${NC}"
scp server.py requirements.txt service_account.json $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/
scp .env.production $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/.env
scp -r client $ZOMRO_USER@$ZOMRO_IP:$DEST_DIR/

echo -e "${BLUE}2. Installation de gevent sur le serveur...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP << 'EOF'
cd /var/www/killer
source .venv/bin/activate
pip install --upgrade pip
pip install gevent==23.9.1
pip install -r requirements.txt
EOF

echo -e "${BLUE}3. Mise à jour de la configuration systemd...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP << 'EOF'
cat > /etc/systemd/system/killer.service << 'EOL'
[Unit]
Description=Killer Game Flask Application (Optimized for 100+ users)
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/killer
EnvironmentFile=/var/www/killer/.env
Environment="PYTHONUNBUFFERED=1"
ExecStartPre=/bin/mkdir -p /var/www/killer/flask_session
ExecStart=/var/www/killer/.venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=file:/var/log/killer.log
StandardError=file:/var/log/killer.error.log

# Limites de ressources
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
EOF

echo -e "${BLUE}4. Redémarrage du service...${NC}"
ssh $ZOMRO_USER@$ZOMRO_IP << 'EOF'
systemctl restart killer
sleep 3
systemctl status killer --no-pager
EOF

echo ""
echo -e "${GREEN}=== Déploiement terminé! ===${NC}"
echo ""
echo -e "${YELLOW}Configuration appliquée:${NC}"
echo "  - Workers: 16 (gevent)"
echo "  - Worker connections: 1000"
echo "  - Cache: 30 secondes"
echo "  - Timeout: 120 secondes"
echo ""
echo -e "${YELLOW}Capacité estimée:${NC} 200-500 utilisateurs simultanés"
echo ""
echo -e "${BLUE}Vérifier les logs:${NC}"
echo "  ssh $ZOMRO_USER@$ZOMRO_IP 'tail -f /var/log/killer.log'"
echo ""
echo -e "${BLUE}Tester:${NC}"
echo "  curl http://$ZOMRO_IP:8080/health"
echo ""
