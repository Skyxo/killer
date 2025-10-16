#!/bin/bash

# Script de déploiement pour l'application Killer sur un serveur Zomro
echo "Déploiement de l'application Killer..."

# Mise à jour du système
echo "Mise à jour du système..."
apt update && apt upgrade -y

# Installation des dépendances système
echo "Installation des dépendances système..."
apt install -y python3 python3-pip python3-venv git nginx supervisor

# Création du répertoire de l'application
echo "Configuration du répertoire de l'application..."
mkdir -p /opt/killer
cd /opt/killer

# Clonage du dépôt Git (à faire manuellement lors de la première installation)
if [ ! -d ".git" ]; then
    echo "Clonage du dépôt Git..."
    git init
    git remote add origin https://github.com/Skyxo/killer.git
    git pull origin main
else
    echo "Mise à jour du code source..."
    git pull origin main
fi

# Création et activation de l'environnement virtuel
echo "Configuration de l'environnement Python..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Installation des dépendances Python
echo "Installation des dépendances Python..."
pip install -r requirements.txt

# Configuration du fichier .env
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "Création du fichier .env à partir de .env.example..."
    cp .env.example .env
    echo "N'oubliez pas de modifier le fichier .env avec vos valeurs spécifiques!"
fi

# Configuration de Supervisor pour gérer le processus
echo "Configuration de Supervisor..."
cat > /etc/supervisor/conf.d/killer.conf << EOL
[program:killer]
directory=/opt/killer
command=/opt/killer/.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 server:app
autostart=true
autorestart=true
stderr_logfile=/var/log/killer.err.log
stdout_logfile=/var/log/killer.out.log
user=root
environment=LANG="en_US.utf8", LC_ALL="en_US.UTF-8", LC_LANG="en_US.UTF-8"
EOL

# Configuration de Nginx comme proxy inverse
echo "Configuration de Nginx..."
cat > /etc/nginx/sites-available/killer << EOL
server {
    listen 80;
    server_name 188.137.176.245; # Remplacez par votre nom de domaine si disponible

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /static {
        alias /opt/killer/client;
    }
}
EOL

# Activation de la configuration Nginx
if [ ! -L /etc/nginx/sites-enabled/killer ]; then
    ln -s /etc/nginx/sites-available/killer /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default # Supprimer la config par défaut
fi

# Redémarrage des services
echo "Redémarrage des services..."
supervisorctl reread
supervisorctl update
supervisorctl restart killer
nginx -t && systemctl restart nginx

# Configuration du pare-feu (si UFW est installé)
if command -v ufw &> /dev/null; then
    echo "Configuration du pare-feu..."
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 5000/tcp # Port de l'application Flask pour le débogage direct
fi

echo "Déploiement terminé!"
echo "L'application devrait être accessible à l'adresse http://188.137.176.245"
echo ""
echo "Pour vérifier les logs, utilisez:"
echo "supervisorctl tail -f killer"