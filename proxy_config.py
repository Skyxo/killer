# Configuration du serveur proxy pour la connexion aux API Google sur Zomro
# À utiliser si les connexions directes sont bloquées par le pare-feu du serveur

import os
import sys

# Configuration du proxy (à modifier selon les informations de votre hébergeur)
# Utiliser un proxy HTTPS si disponible
os.environ['https_proxy'] = ''  # Par exemple: 'https://proxy.zomro.com:8080'
os.environ['HTTPS_PROXY'] = ''  # Par exemple: 'https://proxy.zomro.com:8080'

# Certificats SSL personnalisés (si nécessaire)
# Commenter cette ligne si vous n'avez pas de problème de certificats SSL
# os.environ['REQUESTS_CA_BUNDLE'] = '/chemin/vers/certificats/ca-bundle.pem'

# Configuration du timeout pour les requêtes réseau
os.environ['REQUESTS_TIMEOUT'] = '60'

print("Configuration proxy chargée.")