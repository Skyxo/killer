#!/bin/bash

# Script de synchronisation des données depuis Google Sheets
# Usage: ./sync.sh [admin_nickname] [admin_password]

ADMIN_USER="${1:-admin}"
ADMIN_PASS="${2:-killer2025}"
SERVER_URL="${3:-http://localhost:5000}"

echo "=== Synchronisation des données Killer Game ==="
echo "Serveur: $SERVER_URL"
echo "Utilisateur: $ADMIN_USER"
echo ""

# Étape 1: Login admin
echo "[1/2] Connexion en tant qu'administrateur..."
LOGIN_RESPONSE=$(curl -s -c cookies.txt -X POST "$SERVER_URL/api/login" \
  -H "Content-Type: application/json" \
  -d "{\"nickname\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}")

if echo "$LOGIN_RESPONSE" | grep -q '"success":true'; then
  echo "✓ Connexion réussie"
else
  echo "✗ Échec de la connexion"
  echo "$LOGIN_RESPONSE"
  rm -f cookies.txt
  exit 1
fi

# Étape 2: Synchronisation
echo "[2/2] Synchronisation des données..."
SYNC_RESPONSE=$(curl -s -b cookies.txt -X POST "$SERVER_URL/api/admin/sync" \
  -H "Content-Type: application/json")

if echo "$SYNC_RESPONSE" | grep -q '"success":true'; then
  echo "✓ Synchronisation réussie!"
  echo ""
  echo "Statistiques:"
  echo "$SYNC_RESPONSE" | grep -oP '"stats":\{[^}]+\}' | sed 's/[{}"]//g' | tr ',' '\n' | sed 's/^/  /'
else
  echo "✗ Échec de la synchronisation"
  echo "$SYNC_RESPONSE"
  rm -f cookies.txt
  exit 1
fi

# Nettoyage
rm -f cookies.txt

echo ""
echo "=== Synchronisation terminée ==="

