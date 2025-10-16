#!/bin/bash

# Script pour redémarrer l'application avec les bonnes configurations
# À exécuter sur le serveur Zomro

echo "=== Redémarrage complet de l'application Killer ==="

# Se déplacer dans le répertoire de l'application
cd /var/www/killer

# Arrêter tous les processus existants
echo "Arrêt des processus existants..."
pkill -f "python3 server.py" || true
pkill -f "gunicorn" || true
systemctl stop killer || true

# Vérifier et corriger le fichier service_account.json
if [ ! -f "service_account.json" ]; then
    echo "ERREUR: Le fichier service_account.json est manquant!"
    echo "Veuillez téléverser le fichier service_account.json sur le serveur."
    exit 1
else
    echo "Le fichier service_account.json existe."
    chmod 644 service_account.json
fi

# S'assurer que le dossier flask_session existe et a les bonnes permissions
echo "Configuration du dossier flask_session..."
mkdir -p flask_session
chmod -R 777 flask_session

# Vérifier le fichier .env
echo "Vérification du fichier .env..."
if [ ! -f ".env" ]; then
    echo "Création du fichier .env..."
    cat > .env << EOL
FLASK_SECRET_KEY=$(openssl rand -hex 16)
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY
FLASK_DEBUG=False
PORT=8080
EOL
else
    echo "Le fichier .env existe déjà."
fi

# Créer le fichier ssl_bypass.py
echo "Création du fichier ssl_bypass.py..."
cat > ssl_bypass.py << EOL
import ssl
import socket

# Désactiver la vérification SSL
if hasattr(ssl, "_create_default_https_context"):
    ssl._create_default_https_context = ssl._create_unverified_context

# Augmenter le timeout des sockets pour les requêtes HTTP
socket.setdefaulttimeout(60)

print("SSL verification désactivée et timeout augmenté")
EOL

# Installer ou mettre à jour les dépendances
echo "Mise à jour des dépendances..."
pip install --upgrade gspread oauth2client python-dotenv flask gunicorn

# Redémarrer l'application avec Gunicorn
echo "Démarrage de l'application avec Gunicorn..."
export PYTHONPATH=$PYTHONPATH:/var/www/killer
python3 -c "import ssl_bypass"
nohup gunicorn -b 0.0.0.0:8080 server:app --workers 2 --timeout 120 > /var/log/killer.log 2>&1 &

# Vérifier que l'application est en cours d'exécution
sleep 3
echo "Vérification des processus en cours d'exécution..."
ps aux | grep "[g]unicorn\|[p]ython3 server.py"

echo "=== Application redémarrée ==="
echo "Vérifiez les logs pour vous assurer que tout fonctionne correctement:"
echo "tail -f /var/log/killer.log"
echo "L'application devrait être accessible à http://188.137.176.245:8080"