#!/bin/bash

# Script pour vérifier et configurer le pare-feu pour le port 8080
# À exécuter sur le serveur Zomro

echo "=== Vérification et configuration du pare-feu pour le port 8080 ==="

# Vérifier si ufw est installé et actif
if command -v ufw &> /dev/null; then
    echo "UFW est installé. Vérification du statut..."
    ufw status
    
    echo "Autorisation du port 8080..."
    ufw allow 8080/tcp
    echo "Port 8080 autorisé dans UFW."
fi

# Vérifier si iptables est utilisé
if command -v iptables &> /dev/null; then
    echo "Vérification des règles iptables pour le port 8080..."
    iptables -L -n | grep 8080
    
    echo "Ajout d'une règle iptables pour le port 8080..."
    iptables -I INPUT -p tcp --dport 8080 -j ACCEPT
    echo "Règle iptables ajoutée pour le port 8080."
fi

# Vérifier si firewalld est utilisé
if command -v firewall-cmd &> /dev/null; then
    echo "Firewalld est installé. Vérification du statut..."
    firewall-cmd --state
    
    echo "Autorisation du port 8080..."
    firewall-cmd --add-port=8080/tcp --permanent
    firewall-cmd --reload
    echo "Port 8080 autorisé dans firewalld."
fi

echo "Vérification des connexions actuelles sur le port 8080..."
netstat -tulpn | grep :8080 || ss -tulpn | grep :8080 || lsof -i :8080

echo "=== Vérification terminée ==="
echo "Si votre site n'est toujours pas accessible, essayez de redémarrer le serveur:"
echo "systemctl restart killer"
echo "ou lancez manuellement avec nohup:"
echo "nohup python3 server.py &"