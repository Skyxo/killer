#!/bin/bash
# Script de test de charge pour valider la capacité du serveur

ZOMRO_IP="188.137.182.53"
PORT="8080"
URL="http://${ZOMRO_IP}:${PORT}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Test de charge du serveur Killer ===${NC}"
echo ""

# Vérifier qu'Apache Bench est installé
if ! command -v ab &> /dev/null; then
    echo -e "${RED}Apache Bench (ab) n'est pas installé${NC}"
    echo "Installation:"
    echo "  sudo apt-get install apache2-utils"
    exit 1
fi

# Fonction pour tester
test_load() {
    local concurrent=$1
    local total=$2
    local desc=$3
    
    echo ""
    echo -e "${YELLOW}=== Test: $desc ===${NC}"
    echo "Connexions simultanées: $concurrent"
    echo "Requêtes totales: $total"
    echo ""
    
    ab -n $total -c $concurrent -g test_${concurrent}.tsv "${URL}/health" 2>&1 | tee test_${concurrent}.log
    
    # Analyser les résultats
    local failed=$(grep "Failed requests:" test_${concurrent}.log | awk '{print $3}')
    local time_per_req=$(grep "Time per request:" test_${concurrent}.log | head -1 | awk '{print $4}')
    local requests_per_sec=$(grep "Requests per second:" test_${concurrent}.log | awk '{print $4}')
    
    echo ""
    if [ "$failed" = "0" ]; then
        echo -e "${GREEN}✓ Test réussi: 0 erreurs${NC}"
    else
        echo -e "${RED}✗ Test échoué: $failed erreurs${NC}"
    fi
    
    echo "Temps par requête: ${time_per_req}ms"
    echo "Requêtes/seconde: ${requests_per_sec}"
    echo ""
}

# Test de base
echo -e "${BLUE}Test 1: Vérification de base${NC}"
curl -s "${URL}/health" && echo -e "${GREEN}✓ Serveur accessible${NC}" || echo -e "${RED}✗ Serveur inaccessible${NC}"

# Test progressif
test_load 5 100 "5 utilisateurs (baseline)"
sleep 2

test_load 10 500 "10 utilisateurs"
sleep 2

test_load 25 1000 "25 utilisateurs"
sleep 2

test_load 50 2000 "50 utilisateurs"
sleep 2

test_load 100 5000 "100 utilisateurs (OBJECTIF)"
sleep 2

# Test stress (optionnel)
read -p "Voulez-vous faire un test de stress avec 200 utilisateurs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_load 200 10000 "200 utilisateurs (STRESS TEST)"
fi

echo ""
echo -e "${BLUE}=== Résumé des tests ===${NC}"
echo ""

for log in test_*.log; do
    concurrent=$(echo $log | sed 's/test_//;s/.log//')
    failed=$(grep "Failed requests:" $log | awk '{print $3}')
    time_per_req=$(grep "Time per request:" $log | head -1 | awk '{print $4}')
    
    if [ "$failed" = "0" ]; then
        status="${GREEN}✓${NC}"
    else
        status="${RED}✗${NC}"
    fi
    
    echo -e "$status $concurrent users: ${time_per_req}ms/req, $failed erreurs"
done

echo ""
echo -e "${YELLOW}Fichiers générés:${NC}"
ls -lh test_*.log test_*.tsv 2>/dev/null || echo "Aucun fichier"

echo ""
echo -e "${BLUE}Pour visualiser les graphiques:${NC}"
echo "  gnuplot"
echo "  plot 'test_100.tsv' using 2 with lines title '100 users'"
echo ""
