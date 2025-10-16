#!/bin/bash

# Script pour tuer tous les processus sur le port 8080
# Exécuter ce script sur le serveur distant

echo "Recherche des processus utilisant le port 8080..."

# Rechercher les PID des processus utilisant le port 8080 avec différentes commandes
# car on ne sait pas lesquelles sont disponibles sur le serveur
pids=""

if command -v lsof &> /dev/null; then
    echo "Utilisation de lsof..."
    pids=$(lsof -t -i:8080)
elif command -v netstat &> /dev/null; then
    echo "Utilisation de netstat..."
    pids=$(netstat -tulpn | grep ":8080" | awk '{print $7}' | cut -d'/' -f1)
elif command -v ss &> /dev/null; then
    echo "Utilisation de ss..."
    pids=$(ss -tulpn | grep ":8080" | awk '{print $7}' | cut -d',' -f2 | cut -d'=' -f2)
else
    echo "ERREUR: Aucun outil disponible pour identifier les processus (lsof, netstat, ss)."
    exit 1
fi

# Si des PID ont été trouvés, les terminer
if [ -n "$pids" ]; then
    echo "Processus trouvés utilisant le port 8080: $pids"
    echo "Tentative de terminer ces processus..."
    
    for pid in $pids; do
        echo "Envoi du signal TERM au processus $pid..."
        kill $pid
        sleep 1
        
        # Vérifier si le processus existe toujours
        if kill -0 $pid 2>/dev/null; then
            echo "Le processus $pid ne s'est pas terminé, tentative avec KILL..."
            kill -9 $pid
        else
            echo "Processus $pid terminé avec succès."
        fi
    done
    
    echo "Vérification finale..."
    sleep 2
    
    # Vérifier si des processus utilisent toujours le port 8080
    if command -v lsof &> /dev/null; then
        remaining=$(lsof -t -i:8080)
    elif command -v netstat &> /dev/null; then
        remaining=$(netstat -tulpn | grep ":8080")
    elif command -v ss &> /dev/null; then
        remaining=$(ss -tulpn | grep ":8080")
    fi
    
    if [ -n "$remaining" ]; then
        echo "ATTENTION: Des processus utilisent toujours le port 8080:"
        echo "$remaining"
    else
        echo "Tous les processus utilisant le port 8080 ont été terminés avec succès."
    fi
else
    echo "Aucun processus n'utilise actuellement le port 8080."
fi

# Vérifier l'état du service killer
if systemctl is-active killer &> /dev/null; then
    echo "Le service killer est actif. Arrêt du service..."
    systemctl stop killer
    echo "Service killer arrêté."
else
    echo "Le service killer n'est pas actif."
fi

echo "Port 8080 libéré. Vous pouvez maintenant redémarrer votre application."