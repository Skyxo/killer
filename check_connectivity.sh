#!/bin/bash
# Script de vérification de connectivité pour Zomro

DOMAIN="sheets.googleapis.com"

echo "=== Test de connectivité vers Google Sheets ==="

# Test DNS
echo "Test DNS pour $DOMAIN..."
if host $DOMAIN > /dev/null; then
    echo "✅ DNS OK: $DOMAIN"
else
    echo "❌ DNS ÉCHEC: $DOMAIN"
fi

# Test de connexion TCP
echo "Test TCP vers $DOMAIN:443..."
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$DOMAIN/443"; then
    echo "✅ TCP OK: $DOMAIN:443"
else
    echo "❌ TCP ÉCHEC: $DOMAIN:443"
fi

# Test HTTPS
echo "Test HTTPS vers $DOMAIN..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/ --connect-timeout 10)
if [ "$RESPONSE" -ge 200 ] && [ "$RESPONSE" -lt 500 ]; then
    echo "✅ HTTPS OK: Réponse $RESPONSE de $DOMAIN"
else
    echo "❌ HTTPS ÉCHEC: Réponse $RESPONSE de $DOMAIN"
fi

# Instructions si échec
if [ "$RESPONSE" -lt 200 ] || [ "$RESPONSE" -ge 500 ]; then
    echo 
    echo "Le serveur Zomro semble bloquer les connexions vers Google."
    echo "Solutions possibles:"
    echo "1. Contactez le support Zomro pour autoriser les domaines Google:"
    echo "   - sheets.googleapis.com"
    echo "   - accounts.google.com"
    echo "   - oauth2.googleapis.com"
    echo "2. Configurez un proxy HTTPS sur le serveur"
    echo "3. Utilisez le mode cache si disponible"
fi

# Test du fichier service_account.json
echo
echo "Vérification du fichier service_account.json..."
if [ -f "service_account.json" ]; then
    echo "✅ Fichier service_account.json présent"
    # Vérifier le contenu du fichier
    if grep -q "private_key" service_account.json && grep -q "client_email" service_account.json; then
        echo "✅ Format du fichier service_account.json valide"
    else
        echo "❌ Format du fichier service_account.json invalide"
    fi
else
    echo "❌ Fichier service_account.json manquant"
fi

echo
echo "=== Test terminé ==="