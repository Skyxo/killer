#!/bin/bash
# Script pour vérifier et préparer le déploiement sur Zomro

echo "=== Préparation du déploiement pour Zomro ==="
echo

# Vérifier le fichier service_account.json
if [ -f "service_account.json" ]; then
    echo "✅ Fichier service_account.json trouvé"
else
    echo "❌ ERREUR: Fichier service_account.json manquant!"
    echo "Ce fichier est nécessaire pour la connexion à Google Sheets."
    exit 1
fi

# Vérifier le fichier .env.zomro
if [ -f ".env.zomro" ]; then
    echo "✅ Fichier .env.zomro trouvé"
else
    echo "❌ ERREUR: Fichier .env.zomro manquant!"
    echo "Création d'un fichier .env.zomro par défaut..."
    cat > .env.zomro << EOL
# Configuration pour le serveur Flask sur Zomro
FLASK_SECRET_KEY=$(openssl rand -hex 16)

# Configuration Google Sheets
# Utiliser le chemin absolu pour éviter les problèmes de chemin relatif
SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json
SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY

# Configuration pour le debug
FLASK_DEBUG=False

# Configuration pour la connexion réseau
REQUESTS_TIMEOUT=60
EOL
    echo "✅ Fichier .env.zomro créé avec succès"
fi

# Vérifier les dépendances
echo "Vérification des dépendances Python..."
pip install --user requests > /dev/null 2>&1

# Vérifier la connectivité aux API Google
echo "Vérification de la connectivité aux API Google..."
cat > check_google.py << EOL
import socket
import ssl
import sys
from urllib.request import urlopen

# Domaines Google à vérifier
domains = [
    "sheets.googleapis.com",
    "oauth2.googleapis.com", 
    "www.googleapis.com"
]

all_ok = True

for domain in domains:
    try:
        # Test DNS
        try:
            ip = socket.gethostbyname(domain)
            print(f"✓ DNS pour {domain}: OK ({ip})")
        except socket.gaierror as e:
            print(f"✗ DNS pour {domain}: ÉCHEC ({str(e)})")
            all_ok = False
        
        # Test HTTPS
        try:
            with urlopen(f"https://{domain}/", timeout=10) as response:
                print(f"✓ HTTPS pour {domain}: OK (status {response.status})")
        except Exception as e:
            print(f"✗ HTTPS pour {domain}: ÉCHEC ({str(e)})")
            all_ok = False
    except Exception as e:
        print(f"✗ Test pour {domain}: ERREUR GÉNÉRALE ({str(e)})")
        all_ok = False

if all_ok:
    print("\n✓ CONNECTIVITÉ AUX API GOOGLE: OK")
    sys.exit(0)
else:
    print("\n✗ PROBLÈMES DE CONNECTIVITÉ DÉTECTÉS!")
    print("Solutions possibles:")
    print("1. Vérifiez que votre serveur autorise les connexions sortantes vers les domaines Google")
    print("2. Contactez votre hébergeur pour autoriser les domaines requis")
    print("3. Vérifiez la configuration du pare-feu ou proxy du serveur")
    sys.exit(1)
EOL

python check_google.py
CONNECTIVITY_RESULT=$?
rm check_google.py

if [ $CONNECTIVITY_RESULT -ne 0 ]; then
    echo "❌ AVERTISSEMENT: Problèmes de connectivité détectés!"
    echo "Le déploiement peut continuer, mais l'application pourrait ne pas fonctionner correctement."
    echo "Voulez-vous continuer? (o/n)"
    read -r answer
    if [[ "$answer" != "o" && "$answer" != "O" ]]; then
        echo "Déploiement annulé."
        exit 1
    fi
else
    echo "✅ Connectivité aux API Google vérifiée avec succès"
fi

echo
echo "=== Instructions pour le déploiement sur Zomro ==="
echo "1. Transférez tous les fichiers vers le serveur avec SCP ou SFTP"
echo "2. Assurez-vous que le fichier service_account.json est correctement transféré"
echo "3. Copiez le fichier .env.zomro vers .env sur le serveur"
echo "4. Installez les dépendances: pip install -r requirements.txt"
echo "5. Démarrez l'application avec Gunicorn: gunicorn -b 0.0.0.0:5000 server:app"
echo
echo "Commandes pour le déploiement sur Zomro:"
echo "-------------------------------------"
echo "# Se connecter au serveur"
echo "ssh root@188.137.176.245"
echo
echo "# Sur le serveur:"
echo "mkdir -p /var/www/killer"
echo "exit"
echo
echo "# Transférer les fichiers (depuis votre machine locale)"
echo "scp -r * root@188.137.176.245:/var/www/killer/"
echo "scp -r .env.zomro root@188.137.176.245:/var/www/killer/.env"
echo
echo "# Se reconnecter et configurer l'application"
echo "ssh root@188.137.176.245"
echo "cd /var/www/killer"
echo "pip install -r requirements.txt"
echo "python server.py  # Test initial"
echo
echo "# Pour démarrer en production"
echo "nohup gunicorn -b 0.0.0.0:5000 server:app &"
echo
echo "=== Fin des instructions ==="