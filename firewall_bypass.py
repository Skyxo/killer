# Configuration pour contourner le blocage pare-feu de Zomro

import os
import sys
import socket
import ssl

print("=== Configuration du contournement pare-feu ===")

# 1. Forcer l'utilisation d'IPv4 uniquement (peut aider dans certains cas)
print("Configuration IPv4...")
socket.has_ipv6 = False
os.environ["PYTHONHTTPVERBS"] = "IPv4"

# 2. Augmenter tous les timeouts
print("Configuration des timeouts...")
socket.setdefaulttimeout(60)  # 60 secondes

# 3. Configuration SSL pour ignorer les vérifications si nécessaire
try:
    print("Configuration SSL...")
    if hasattr(ssl, '_create_default_https_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
        print("SSL verification désactivée (méthode moderne)")
except Exception as e:
    print(f"Erreur lors de la configuration SSL: {str(e)}")

# 4. Contournement DNS - ajouter des entrées hosts manuelles
# Cela peut aider si le pare-feu bloque au niveau DNS
print("Configuration du cache DNS manuel...")
GOOGLE_IPS = {
    "sheets.googleapis.com": "142.250.179.138",
    "oauth2.googleapis.com": "142.250.102.95",
    "www.googleapis.com": "172.217.168.202"
}

# Fonction pour remplacer les résolutions DNS standards
_orig_getaddrinfo = socket.getaddrinfo
def _new_getaddrinfo(*args, **kwargs):
    host = args[0]
    if host in GOOGLE_IPS:
        print(f"Utilisation de l'IP manuelle pour {host}: {GOOGLE_IPS[host]}")
        # Remplacer par notre IP connue
        return _orig_getaddrinfo(GOOGLE_IPS[host], *args[1:], **kwargs)
    return _orig_getaddrinfo(*args, **kwargs)

# Remplacer la fonction de résolution DNS
socket.getaddrinfo = _new_getaddrinfo
print("Résolution DNS personnalisée activée")

# 5. Configuration pour utiliser des proxys si disponibles
print("Vérification de proxys disponibles...")
PROXY_ENVS = [
    'https_proxy', 'HTTPS_PROXY', 
    'http_proxy', 'HTTP_PROXY'
]

proxy_found = False
for env in PROXY_ENVS:
    if os.environ.get(env):
        print(f"Proxy trouvé dans {env}: {os.environ.get(env)}")
        proxy_found = True

if not proxy_found:
    print("Aucun proxy configuré dans l'environnement.")
    # Vous pouvez définir un proxy par défaut ici si nécessaire
    # os.environ['https_proxy'] = 'http://proxy.exemple.com:8080'

print("=== Configuration du contournement pare-feu terminée ===")

# 6. Configurer les modules de requêtes pour utiliser ces paramètres
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print("Avertissements urllib3 désactivés")
except ImportError:
    pass

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    print("Avertissements requests désactivés")
except (ImportError, AttributeError):
    pass