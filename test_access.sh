#!/bin/bash

# Script pour vérifier l'accès direct à l'application Flask
# À exécuter sur le serveur Zomro

echo "=== Test d'accès direct à l'application Flask ==="

# Vérifier si l'application est en cours d'exécution sur le port 8080
echo "Vérification des processus sur le port 8080..."
lsof -i :8080 || netstat -tulpn | grep :8080 || ss -tulpn | grep :8080

# Essayer d'accéder à l'application localement
echo "Test d'accès local à l'application..."
curl -v http://localhost:8080/

echo "=== Tests terminés ==="
echo "Si le test local fonctionne mais que vous ne pouvez pas accéder depuis l'extérieur,"
echo "le problème est probablement lié au pare-feu ou à la configuration NGINX."