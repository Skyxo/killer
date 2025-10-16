# Script de contournement des problèmes SSL
import ssl

# Désactiver la vérification SSL
if hasattr(ssl, '_create_default_https_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
    print("SSL verification désactivée")

# Augmenter le timeout des sockets
import socket
socket.setdefaulttimeout(60)  # 60 secondes