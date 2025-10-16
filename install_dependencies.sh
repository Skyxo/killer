#!/bin/bash

# Script pour installer toutes les dépendances requises
# À exécuter sur le serveur Zomro

echo "=== Installation des dépendances pour l'application Killer ==="

# Mise à jour des paquets
echo "Mise à jour des paquets..."
apt-get update -y

# Installation des dépendances système
echo "Installation des dépendances système..."
apt-get install -y python3-pip python3-dev build-essential

# Mise à niveau de pip
echo "Mise à niveau de pip..."
pip3 install --upgrade pip

# Installation des dépendances Python
echo "Installation des dépendances Python..."
pip3 install gspread oauth2client flask gunicorn python-dotenv

# Vérification des installations
echo "Vérification des installations..."
pip3 list | grep -E 'gspread|oauth2client|flask|gunicorn|python-dotenv'

echo "=== Installation terminée ==="
echo "Vous pouvez maintenant exécuter les scripts de test et de démarrage."