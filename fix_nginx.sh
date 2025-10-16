#!/bin/bash

# Script pour configurer NGINX et résoudre l'erreur 502 Bad Gateway
# À exécuter sur le serveur Zomro

echo "=== Configuration de NGINX pour l'application Killer ==="

# Vérifier si NGINX est installé
if ! command -v nginx &> /dev/null; then
    echo "NGINX n'est pas installé. Installation..."
    apt-get update && apt-get install -y nginx
    echo "NGINX installé."
fi

# Arrêter temporairement NGINX pour la configuration
echo "Arrêt de NGINX..."
systemctl stop nginx

# Vérifier si notre application Flask est en cours d'exécution
FLASK_RUNNING=$(ps aux | grep "python3 server.py\|gunicorn" | grep -v grep)
if [ -z "$FLASK_RUNNING" ]; then
    echo "L'application Flask ne semble pas être en cours d'exécution."
    echo "Démarrage de l'application Flask..."
    cd /var/www/killer
    nohup python3 server.py > /var/log/killer.log 2>&1 &
    echo "Application Flask démarrée."
else
    echo "L'application Flask est en cours d'exécution."
fi

# Créer la configuration NGINX
echo "Création de la configuration NGINX pour l'application Killer..."
cat > /etc/nginx/sites-available/killer << EOL
server {
    listen 80;
    server_name 188.137.176.245;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    access_log /var/log/nginx/killer-access.log;
    error_log /var/log/nginx/killer-error.log;
}
EOL

# Activer le site
ln -sf /etc/nginx/sites-available/killer /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Vérifier la configuration NGINX
echo "Vérification de la configuration NGINX..."
nginx -t

# Redémarrer NGINX
echo "Redémarrage de NGINX..."
systemctl restart nginx

# Vérifier l'état de NGINX
echo "Vérification de l'état de NGINX..."
systemctl status nginx

echo "=== Configuration terminée ==="
echo "Vous devriez maintenant pouvoir accéder à votre application via http://188.137.176.245"
echo "Pour voir les logs NGINX en cas d'erreurs:"
echo "  tail -f /var/log/nginx/killer-error.log"
echo "  tail -f /var/log/nginx/killer-access.log"
echo "Pour voir les logs de l'application Flask:"
echo "  tail -f /var/log/killer.log"