#!/bin/bash
echo "🔧 Fix Killer Game sur Zomro"
echo "================================"
echo ""

# Activer l'environnement virtuel
source venv/bin/activate

# Étape 1: Démarrer serveur local en mode dev (port 5000)
echo "1️⃣ Démarrage serveur local..."
export FLASK_APP=server.py
export FLASK_ENV=development
PORT=5000 python server.py > /tmp/killer.log 2>&1 &
SERVER_PID=$!
echo "   Serveur PID: $SERVER_PID"

# Attendre que le serveur soit prêt
echo "   Attente du démarrage..."
for i in {1..30}; do
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        echo "   ✓ Serveur prêt!"
        break
    fi
    sleep 1
done

# Étape 2: Synchroniser en local
echo ""
echo "2️⃣ Synchronisation locale (téléchargement depuis Google Sheets)..."
PORT=5000 ./sync.sh admin killer2025

# Étape 3: Arrêter serveur local
echo ""
echo "3️⃣ Arrêt serveur local..."
kill $SERVER_PID 2>/dev/null
sleep 2

# Désactiver venv
deactivate

# Vérifier que les CSV existent
if [ ! -f "data/players.csv" ]; then
    echo "❌ Erreur: CSV non créés!"
    echo "Logs du serveur:"
    tail -50 /tmp/killer.log
    exit 1
fi

echo "   ✓ CSV créés ($(wc -l < data/players.csv) lignes)"
echo "   ✓ Images: $(ls data/images/*.jpg 2>/dev/null | wc -l) fichiers"

# Étape 4: Upload vers Zomro
echo ""
echo "4️⃣ Upload des données vers Zomro..."
scp -r data root@188.137.182.53:/var/www/killer/

# Étape 5: Redémarrer serveur Zomro
echo ""
echo "5️⃣ Redémarrage du serveur sur Zomro..."
ssh root@188.137.182.53 'systemctl restart killer'

echo ""
echo "✅ Terminé!"
echo ""
echo "🌐 Teste: http://188.137.182.53:8080"
