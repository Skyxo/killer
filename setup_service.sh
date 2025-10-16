#!/bin/bash

# Script pour installer et activer le service killer en permanence
# À exécuter sur le serveur distant

echo "Configuration du service killer..."

# Copier le fichier service dans /etc/systemd/system
cp ./killer.service /etc/systemd/system/
chmod 644 /etc/systemd/system/killer.service

# Recharger systemd
systemctl daemon-reload

# Activer le service pour qu'il démarre automatiquement
systemctl enable killer.service

# Démarrer le service
systemctl start killer.service

# Vérifier l'état
echo "État du service :"
systemctl status killer.service

echo ""
echo "Le service killer est maintenant configuré pour fonctionner en permanence."
echo "Il redémarrera automatiquement en cas de panne ou au redémarrage du serveur."
echo ""
echo "Commandes utiles :"
echo "  - Vérifier l'état : systemctl status killer.service"
echo "  - Redémarrer le service : systemctl restart killer.service"
echo "  - Arrêter le service : systemctl stop killer.service"
echo "  - Voir les logs : journalctl -u killer.service"