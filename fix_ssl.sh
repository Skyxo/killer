#!/bin/bash
# Script pour corriger les problèmes de certificats SSL sur Zomro

echo "=== Correction des problèmes de certificats SSL ==="
echo

# Vérifier si le script est exécuté avec les privilèges root
if [ "$EUID" -ne 0 ]; then
  echo "Ce script doit être exécuté en tant que root."
  echo "Utilisez: sudo $0"
  exit 1
fi

echo "1. Mise à jour des paquets..."
apt-get update

echo "2. Installation/mise à jour des certificats CA..."
apt-get install -y ca-certificates openssl

echo "3. Mise à jour de la base de certificats..."
update-ca-certificates --fresh

echo "4. Test de connexion aux API Google..."

# Test avec curl
echo "Test avec curl..."
curl -v https://sheets.googleapis.com/$discovery/rest?version=v4 > /dev/null 2>&1
CURL_RESULT=$?

if [ $CURL_RESULT -eq 0 ]; then
    echo "✅ Test curl réussi!"
else
    echo "❌ Test curl échoué avec code $CURL_RESULT."
fi

# Test avec openssl (avec timeout)
echo "Test avec openssl..."
# Utiliser timeout pour éviter que le test ne bloque indéfiniment
timeout 10 bash -c "echo | openssl s_client -connect sheets.googleapis.com:443 -servername sheets.googleapis.com > /dev/null 2>&1"
SSL_RESULT=$?

if [ $SSL_RESULT -eq 0 ]; then
    echo "✅ Test OpenSSL réussi!"
elif [ $SSL_RESULT -eq 124 ]; then
    echo "⚠️ Test OpenSSL a expiré (timeout). Cela indique probablement un blocage réseau."
    echo "Le pare-feu du serveur Zomro bloque probablement les connexions vers les API Google."
    echo "Tentative de correction avancée..."
else
    echo "❌ Test OpenSSL échoué avec code $SSL_RESULT."
    echo "Problème de certificat détecté. Tentative de correction avancée..."
    
    # Configuration de Python pour contourner les problèmes SSL
    echo "5. Configuration de Python pour ignorer les erreurs SSL..."
    
    cat > /var/www/killer/ssl_bypass.py << EOL
import os
import ssl

# Configuration pour les versions plus récentes de Python
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
    print("SSL verification désactivée (méthode moderne)")

# Configuration pour les versions plus anciennes de Python
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print("Avertissements urllib3 désactivés")
except ImportError:
    pass

print("Configuration SSL bypass terminée.")
EOL

    echo "6. Installation des dépendances supplémentaires pour la compatibilité SSL..."
    pip install urllib3 certifi pyopenssl

    echo "7. Création du script d'initialisation de l'application..."
    
    cat > /var/www/killer/start_app.sh << EOL
#!/bin/bash
# Script de démarrage de l'application avec contournement SSL
export PYTHONPATH=/var/www/killer:\$PYTHONPATH

# Démarrer l'application avec le contournement SSL
cd /var/www/killer
python -c "import ssl_bypass"
gunicorn -b 0.0.0.0:5000 server:app --workers 3 --timeout 60
EOL

    chmod +x /var/www/killer/start_app.sh
    echo "Script de démarrage créé: /var/www/killer/start_app.sh"
    
    echo "8. Création du service systemd mis à jour..."
    
    cat > /etc/systemd/system/killer.service << EOL
[Unit]
Description=Killer Game Flask Application
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/killer
ExecStart=/var/www/killer/start_app.sh
Restart=always
StandardOutput=file:/var/log/killer.log
StandardError=file:/var/log/killer.error.log
Environment="PYTHONWARNINGS=ignore:Unverified HTTPS request"
Environment="SERVICE_ACCOUNT_FILE=/var/www/killer/service_account.json"
Environment="SHEET_ID=1ZIiFg_BA7fgpMJfb_s-BmOs_idm3Px_2zWqJ3DLh-dY"

[Install]
WantedBy=multi-user.target
EOL

    echo "Service systemd mis à jour."
    systemctl daemon-reload
    
    echo "9. Modification du script proxy_config.py pour contourner SSL..."
    
    cat > /var/www/killer/proxy_config.py << EOL
# Configuration du proxy et SSL pour la connexion aux API Google
import os
import sys
import ssl

# Désactivation de la vérification SSL (ATTENTION: À utiliser uniquement en dernier recours)
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
    print("SSL verification désactivée")

# Certificats SSL personnalisés (utiliser le chemin du système)
os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'

# Configuration du timeout
os.environ['REQUESTS_TIMEOUT'] = '60'

print("Configuration proxy et SSL chargée.")
EOL
    
    echo "Fichier proxy_config.py mis à jour."
fi

echo "===================================================="
echo "Tests et correctifs SSL terminés."
echo "Si les problèmes persistent:"
echo "1. Vérifiez que le pare-feu n'interfère pas avec les connexions"
echo "2. Vérifiez la date et l'heure du système (importante pour SSL)"
echo "3. Vérifiez que les ports 443 (HTTPS) sont ouverts en sortie"
echo "===================================================="