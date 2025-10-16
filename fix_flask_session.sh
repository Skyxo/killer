#!/bin/bash

# Script pour vérifier et réparer les problèmes de session Flask
# À exécuter sur le serveur Zomro

echo "=== Vérification et réparation des sessions Flask ==="

# Se déplacer dans le répertoire de l'application
cd /var/www/killer

# Vérifier si le dossier flask_session existe
if [ ! -d "flask_session" ]; then
    echo "Création du dossier flask_session..."
    mkdir -p flask_session
fi

# Corriger les permissions
echo "Correction des permissions pour flask_session..."
chmod -R 777 flask_session

# Vérifier si la variable SECRET_KEY est définie
echo "Vérification du fichier .env..."
if [ -f ".env" ]; then
    if ! grep -q "FLASK_SECRET_KEY" .env; then
        echo "Ajout de FLASK_SECRET_KEY dans .env..."
        echo "FLASK_SECRET_KEY=$(openssl rand -hex 16)" >> .env
    fi
else
    echo "Création du fichier .env avec FLASK_SECRET_KEY..."
    echo "FLASK_SECRET_KEY=$(openssl rand -hex 16)" > .env
    echo "SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json" >> .env
    echo "SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY" >> .env
fi

# Afficher les configurations
echo "Contenu du fichier .env:"
cat .env

# Créer un script Python pour tester la session Flask
echo "Création d'un script pour tester la session Flask..."
cat > test_flask_session.py << EOL
from flask import Flask, session
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Créer une application Flask minimale
app = Flask(__name__)

# Configurer le secret key
secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")
app.secret_key = secret_key

print(f"Secret Key: {secret_key}")

# Vérifier si le dossier flask_session existe
if os.path.exists('flask_session'):
    print("Le dossier flask_session existe")
else:
    print("Le dossier flask_session n'existe pas")

# Vérifier si le dossier est accessible en écriture
try:
    test_file = 'flask_session/test_file'
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print("Le dossier flask_session est accessible en écriture")
except Exception as e:
    print(f"Erreur d'accès en écriture: {str(e)}")

print("Test de session Flask terminé")
EOL

# Exécuter le script de test
echo "Exécution du test de session Flask..."
python3 test_flask_session.py

echo "=== Test terminé ==="
echo "Si le test a échoué, vérifiez les permissions et la configuration de Flask"