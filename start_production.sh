#!/bin/bash

# Script pour lancer l'application Flask en mode production avec Gunicorn
# À exécuter sur le serveur Zomro

echo "=== Démarrage de l'application Killer en mode production ==="

# Arrêter tous les processus existants
echo "Arrêt des processus existants..."
pkill -f "python3 server.py" || true
pkill -f "gunicorn" || true
systemctl stop killer || true

# Installer Gunicorn si nécessaire
if ! command -v gunicorn &> /dev/null; then
    echo "Installation de Gunicorn..."
    pip install gunicorn
fi

# Se déplacer dans le répertoire de l'application
cd /var/www/killer

# Activer le contournement SSL
echo "Activation du contournement SSL..."
python3 -c "
import ssl
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
print('SSL verification désactivée')
"

# Lancer l'application avec Gunicorn
echo "Démarrage de l'application avec Gunicorn..."
nohup gunicorn -b 0.0.0.0:8080 server:app --workers 3 --timeout 60 > /var/log/killer.log 2>&1 &

# Vérifier que l'application est en cours d'exécution
sleep 3
ps aux | grep gunicorn

echo "=== Application démarrée ==="
echo "Pour vérifier les logs: tail -f /var/log/killer.log"
echo "Pour accéder à l'application: http://188.137.176.245"