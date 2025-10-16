#!/bin/bash
# Script pour identifier et gérer les processus qui utilisent le port 5000

echo "=== Gestion des processus utilisant le port 5000 ==="

# Identifier les processus utilisant le port 5000
echo "Recherche des processus utilisant le port 5000..."

# Utilisation de plusieurs commandes car tous les systèmes n'ont pas les mêmes outils
if command -v lsof &> /dev/null; then
    echo "Utilisation de lsof:"
    lsof -i :5000
    RESULT_LSOF=$?
else
    RESULT_LSOF=1
fi

if command -v netstat &> /dev/null; then
    echo "Utilisation de netstat:"
    netstat -tulpn | grep :5000
    RESULT_NETSTAT=$?
else
    RESULT_NETSTAT=1
fi

if command -v ss &> /dev/null; then
    echo "Utilisation de ss:"
    ss -tulpn | grep :5000
    RESULT_SS=$?
else
    RESULT_SS=1
fi

# Vérifier si aucune commande n'a trouvé de processus
if [ $RESULT_LSOF -ne 0 ] && [ $RESULT_NETSTAT -ne 0 ] && [ $RESULT_SS -ne 0 ]; then
    echo "Aucun processus utilisant le port 5000 n'a été trouvé."
    echo "Le problème peut être causé par un processus récemment terminé ou un socket en TIME_WAIT."
    echo "Attendez quelques minutes ou redémarrez le serveur."
else
    echo "Des processus utilisent le port 5000. Voulez-vous les arrêter? (o/n)"
    read -r ANSWER
    
    if [ "$ANSWER" = "o" ] || [ "$ANSWER" = "O" ]; then
        echo "Tentative d'arrêt des processus..."
        
        # Arrêt des processus Flask ou Gunicorn connus
        echo "Arrêt des processus Python/Flask/Gunicorn..."
        pkill -f "python.*server\.py" || true
        pkill -f "gunicorn.*:5000" || true
        
        # Utilisation de fuser pour tuer les processus utilisant le port
        if command -v fuser &> /dev/null; then
            echo "Utilisation de fuser pour arrêter les processus sur le port 5000..."
            fuser -k 5000/tcp || true
        fi
        
        echo "Vérification après arrêt..."
        if command -v lsof &> /dev/null; then
            lsof -i :5000
        elif command -v netstat &> /dev/null; then
            netstat -tulpn | grep :5000
        elif command -v ss &> /dev/null; then
            ss -tulpn | grep :5000
        fi
    fi
fi

echo
echo "=== Informations sur le serveur ==="
echo "Si vous avez modifié l'application pour utiliser le port 8080,"
echo "vous pouvez accéder à l'application via:"
echo "http://$(hostname -I | awk '{print $1}'):8080"
echo
echo "Pour vérifier si le port 8080 est libre:"
if command -v lsof &> /dev/null; then
    lsof -i :8080
elif command -v netstat &> /dev/null; then
    netstat -tulpn | grep :8080
elif command -v ss &> /dev/null; then
    ss -tulpn | grep :8080
fi
echo
echo "Pour démarrer l'application sur le port 8080:"
echo "cd /var/www/killer && python server.py"
echo "ou"
echo "cd /var/www/killer && gunicorn -b 0.0.0.0:8080 server:app --workers 3"