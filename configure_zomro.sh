#!/bin/bash
# Script pour configurer et tester l'environnement sur le serveur Zomro

# Configuration
REMOTE_DIR="/var/www/killer"

echo "=== Configuration de l'environnement Zomro ==="

# 1. Vérifier et créer les répertoires nécessaires
mkdir -p $REMOTE_DIR/flask_session
chmod 777 $REMOTE_DIR/flask_session
echo "✅ Répertoires créés et permissions configurées"

# 2. Vérifier le fichier service_account.json
if [ -f "$REMOTE_DIR/service_account.json" ]; then
    echo "✅ Fichier service_account.json présent"
    
    # Vérifier les permissions
    chmod 644 $REMOTE_DIR/service_account.json
    echo "✅ Permissions de service_account.json configurées"
else
    echo "❌ ERREUR: service_account.json manquant!"
    echo "Veuillez transférer le fichier service_account.json vers $REMOTE_DIR/"
    exit 1
fi

# 3. Vérifier le fichier .env
if [ -f "$REMOTE_DIR/.env" ]; then
    echo "✅ Fichier .env présent"
else
    echo "❌ AVERTISSEMENT: .env manquant! Création à partir de .env.zomro"
    if [ -f "$REMOTE_DIR/.env.zomro" ]; then
        cp $REMOTE_DIR/.env.zomro $REMOTE_DIR/.env
        echo "✅ Fichier .env créé à partir de .env.zomro"
    else
        echo "❌ ERREUR: .env.zomro manquant également!"
        exit 1
    fi
fi

# 4. Installer les dépendances Python
echo "Installation des dépendances Python..."
pip install -r $REMOTE_DIR/requirements.txt
echo "✅ Dépendances installées"

# 5. Test de connectivité
echo "Test de connectivité à Google..."
python3 -c "
import socket
import ssl
import urllib.request

# Test DNS
try:
    ip = socket.gethostbyname('sheets.googleapis.com')
    print(f'✅ DNS pour sheets.googleapis.com: OK ({ip})')
except Exception as e:
    print(f'❌ DNS pour sheets.googleapis.com: ÉCHEC ({str(e)})')

# Test HTTPS
try:
    response = urllib.request.urlopen('https://sheets.googleapis.com/', timeout=10)
    print(f'✅ HTTPS pour sheets.googleapis.com: OK (status {response.status})')
except Exception as e:
    print(f'❌ HTTPS pour sheets.googleapis.com: ÉCHEC ({str(e)})')
    print('Si cette erreur persiste, contactez le support de Zomro pour autoriser les connexions sortantes vers sheets.googleapis.com')
"

# 6. Test de service_account.json
echo "Test du fichier service_account.json..."
python3 -c "
import json
import os

try:
    with open('$REMOTE_DIR/service_account.json', 'r') as f:
        data = json.load(f)
    
    if 'client_email' in data and 'private_key' in data:
        print(f'✅ Fichier service_account.json valide')
        print(f'   Client email: {data[\"client_email\"]}')
    else:
        print('❌ Fichier service_account.json invalide (champs manquants)')
except Exception as e:
    print(f'❌ Erreur lors de la lecture de service_account.json: {str(e)}')
"

# 7. Vérifier si flask_session est accessible
echo "Test des permissions du répertoire flask_session..."
if [ -w "$REMOTE_DIR/flask_session" ]; then
    echo "✅ Répertoire flask_session accessible en écriture"
else
    echo "❌ ERREUR: Répertoire flask_session non accessible en écriture!"
    echo "Exécution de: chmod -R 777 $REMOTE_DIR/flask_session"
    chmod -R 777 $REMOTE_DIR/flask_session
fi

# 8. Instructions pour démarrer le serveur
echo
echo "=== Configuration terminée ==="
echo
echo "Pour démarrer le serveur en mode développement:"
echo "cd $REMOTE_DIR && python3 server.py"
echo
echo "Pour démarrer le serveur en mode production:"
echo "cd $REMOTE_DIR && nohup gunicorn -b 0.0.0.0:5000 server:app &"
echo
echo "Pour arrêter le serveur en mode production:"
echo "pkill gunicorn"