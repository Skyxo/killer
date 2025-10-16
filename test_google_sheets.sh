#!/bin/bash

# Script pour tester la connexion à Google Sheets
# À exécuter sur le serveur Zomro

echo "=== Test de la connexion à Google Sheets ==="

# Se déplacer dans le répertoire de l'application
cd /var/www/killer

# Vérifier que le fichier service_account.json existe
if [ ! -f "service_account.json" ]; then
    echo "ERREUR: Le fichier service_account.json est manquant!"
    exit 1
fi

# Vérifier les permissions du fichier service_account.json
echo "Vérification des permissions du fichier service_account.json..."
ls -la service_account.json

# Corriger les permissions si nécessaire
echo "Correction des permissions..."
chmod 644 service_account.json

# Afficher les 5 premières lignes du fichier (sans les secrets)
echo "Aperçu du fichier service_account.json (sans les secrets)..."
head -n 5 service_account.json

# Créer un script Python pour tester la connexion
echo "Création d'un script de test..."
cat > test_sheets_connection.py << EOL
import os
import ssl
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Désactiver la vérification SSL
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
print("SSL verification désactivée")

# Charger les informations d'environnement
service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE", "/var/www/killer/service_account.json")
sheet_id = os.environ.get("SHEET_ID", "1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY")

print(f"Utilisation du fichier: {service_account_file}")
print(f"ID de la feuille: {sheet_id}")

# Vérifier si le fichier existe
if not os.path.exists(service_account_file):
    print(f"ERREUR: Le fichier {service_account_file} n'existe pas!")
    exit(1)

try:
    # Charger les informations du compte de service
    print("Chargement des informations du compte de service...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, scope)
    
    # Connexion à l'API
    print("Connexion à l'API Google Sheets...")
    gc = gspread.authorize(credentials)
    
    # Ouverture de la feuille
    print(f"Ouverture de la feuille {sheet_id}...")
    worksheet = gc.open_by_key(sheet_id).sheet1
    
    # Récupération des données
    print("Récupération des données...")
    data = worksheet.get_all_records()
    
    # Afficher les noms des colonnes
    if data:
        print(f"Connexion réussie! Colonnes disponibles: {list(data[0].keys())}")
        print(f"Nombre d'enregistrements: {len(data)}")
    else:
        print("La feuille est vide ou ne contient pas de données.")
    
except Exception as e:
    print(f"ERREUR: {str(e)}")
    
    # Afficher plus d'informations sur le fichier service_account
    try:
        with open(service_account_file, 'r') as f:
            account_info = json.load(f)
            print(f"Email du compte de service: {account_info.get('client_email')}")
            print(f"ID du projet: {account_info.get('project_id')}")
    except Exception as e2:
        print(f"Impossible de lire les informations du compte: {str(e2)}")
EOL

# Exécuter le script de test
echo "Exécution du test de connexion..."
export SERVICE_ACCOUNT_FILE="/var/www/killer/service_account.json"
export SHEET_ID="1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY"
python3 test_sheets_connection.py

echo "=== Test terminé ==="
echo "Si le test a échoué, assurez-vous que:"
echo "1. Le fichier service_account.json est correct et complet"
echo "2. La feuille Google Sheets a été partagée avec l'email du compte de service"
echo "3. L'API Google Sheets est activée pour le projet"