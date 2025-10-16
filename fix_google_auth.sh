#!/bin/bash

# Script pour diagnostiquer et corriger les problèmes d'authentification avec Google Sheets
# À exécuter sur le serveur Zomro

echo "=== Diagnostic et correction des problèmes d'authentification Google Sheets ==="

# Vérifier l'existence et les permissions du fichier service_account.json
echo "Vérification du fichier service_account.json..."
if [ -f "/var/www/killer/service_account.json" ]; then
    echo "✅ Le fichier service_account.json existe."
    ls -l /var/www/killer/service_account.json
    
    # Vérifier si le fichier est lisible
    if [ -r "/var/www/killer/service_account.json" ]; then
        echo "✅ Le fichier service_account.json est lisible."
    else
        echo "❌ Le fichier service_account.json n'est pas lisible. Correction des permissions..."
        chmod 644 /var/www/killer/service_account.json
        echo "Permissions corrigées."
    fi
    
    # Vérifier le contenu du fichier
    echo "Vérification du contenu du fichier service_account.json..."
    if grep -q "private_key" /var/www/killer/service_account.json && grep -q "client_email" /var/www/killer/service_account.json; then
        echo "✅ Le fichier service_account.json semble avoir le format correct."
    else
        echo "❌ Le fichier service_account.json pourrait ne pas avoir le format correct."
        echo "Consultez les premières lignes du fichier pour vérification:"
        head -n 10 /var/www/killer/service_account.json
    fi
else
    echo "❌ Le fichier service_account.json n'existe pas à l'emplacement /var/www/killer/service_account.json."
    echo "Veuillez téléverser le fichier service_account.json au bon endroit."
fi

# Vérifier les variables d'environnement
echo "Vérification des variables d'environnement..."
if [ -f "/var/www/killer/.env" ]; then
    echo "✅ Le fichier .env existe."
    echo "Contenu du fichier .env (sans les valeurs sensibles):"
    grep -v "SECRET" /var/www/killer/.env | grep -v "PASSWORD"
else
    echo "❌ Le fichier .env n'existe pas. Création d'un fichier .env de base..."
    cat > /var/www/killer/.env << EOL
FLASK_SECRET_KEY=$(openssl rand -hex 16)
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY
FLASK_DEBUG=False
REQUESTS_TIMEOUT=60
PORT=8080
EOL
    echo "Fichier .env créé avec des valeurs par défaut."
fi

# Test de connectivité aux API Google
echo "Test de connectivité aux API Google..."
python3 -c "
import ssl, urllib.request, json, sys

# Désactiver la vérification SSL
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
    print('SSL verification désactivée')

try:
    # Test de connexion à l'API Sheets
    print('Test de connexion à sheets.googleapis.com...')
    url = 'https://sheets.googleapis.com/\$discovery/rest?version=v4'
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read())
        if 'version' in data:
            print('✅ Connexion réussie à l\'API Sheets, version:', data['version'])
        else:
            print('❌ Connexion établie mais réponse inattendue')
except Exception as e:
    print(f'❌ Erreur de connexion: {e}')
    sys.exit(1)

try:
    # Test de connexion à l'API OAuth2
    print('Test de connexion à oauth2.googleapis.com...')
    url = 'https://oauth2.googleapis.com/.well-known/openid-configuration'
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read())
        if 'issuer' in data:
            print('✅ Connexion réussie à l\'API OAuth2')
        else:
            print('❌ Connexion établie mais réponse inattendue')
except Exception as e:
    print(f'❌ Erreur de connexion: {e}')
    sys.exit(1)
"

# Test complet d'authentification avec le compte de service
echo "Test complet d'authentification avec le compte de service..."
python3 -c "
import os, sys, ssl
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Désactiver la vérification SSL
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
    print('SSL verification désactivée')

try:
    # Charger les informations du compte de service
    service_account_file = '/var/www/killer/service_account.json'
    sheet_id = '1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY'
    
    print(f'Utilisation du fichier de compte de service: {service_account_file}')
    print(f'Accès à la feuille: {sheet_id}')
    
    # Authentification avec le compte de service
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=scopes)
    
    # Création du service Sheets
    service = build('sheets', 'v4', credentials=credentials)
    
    # Tentative de lecture de la feuille
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range='A1:B2').execute()
    values = result.get('values', [])
    
    if not values:
        print('✅ Connexion réussie mais aucune donnée trouvée.')
    else:
        print(f'✅ Connexion réussie! Données trouvées: {len(values)} lignes.')
        print('Exemple de données: ', values[0] if values else 'Aucune donnée')
    
except FileNotFoundError:
    print(f'❌ Fichier non trouvé: {service_account_file}')
    sys.exit(1)
except PermissionError:
    print(f'❌ Permissions insuffisantes pour lire le fichier: {service_account_file}')
    sys.exit(1)
except HttpError as error:
    print(f'❌ Erreur API: {error}')
    if 'invalid_grant' in str(error) or 'unauthorized_client' in str(error):
        print('Problème d\'authentification avec le compte de service.')
        print('Vérifiez que le fichier service_account.json est correct et que le compte a accès à la feuille.')
    elif 'not found' in str(error):
        print('La feuille spécifiée n\'a pas été trouvée ou le compte n\'y a pas accès.')
        print('Vérifiez l\'ID de la feuille et que le compte de service y a accès.')
    sys.exit(1)
except Exception as e:
    print(f'❌ Erreur: {e}')
    sys.exit(1)
"

# Proposer des solutions en cas d'erreur
echo "=== Solutions possibles en cas d'erreur ==="
echo "1. Si le test de connexion a échoué, vérifiez la connectivité internet du serveur."
echo "2. Si l'authentification a échoué:"
echo "   a. Vérifiez que le fichier service_account.json est correct et à jour"
echo "   b. Assurez-vous que le compte de service a accès à la feuille Google Sheets"
echo "   c. Vérifiez que l'API Google Sheets est activée dans votre projet Google Cloud"
echo "3. Pour partager la feuille avec le compte de service:"
echo "   a. Ouvrez votre feuille Google Sheets"
echo "   b. Cliquez sur 'Partager' en haut à droite"
echo "   c. Ajoutez l'adresse email du compte de service (trouvez-la dans le fichier service_account.json, champ 'client_email')"
echo "   d. Accordez les droits d'édition (rôle 'Éditeur')"

echo "=== Diagnostic terminé ==="