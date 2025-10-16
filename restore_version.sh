#!/bin/bash

# Script pour restaurer une ancienne version à partir de GitHub

echo "=== Restauration d'une version précédente ==="
echo

# 1. Visualiser l'historique des commits
echo "Historique des commits récents :"
git log --oneline -n 10

echo
echo "Pour restaurer une ancienne version, vous avez besoin du hash du commit (la première colonne)."
echo "Exemple : abc1234"
echo

# Demander le hash du commit
read -p "Entrez le hash du commit auquel vous souhaitez revenir : " COMMIT_HASH

if [ -z "$COMMIT_HASH" ]; then
    echo "Aucun hash de commit fourni. Opération annulée."
    exit 1
fi

# Vérifier si le hash existe
if ! git cat-file -e "$COMMIT_HASH" 2>/dev/null; then
    echo "Hash de commit invalide ou inexistant. Vérifiez l'historique et réessayez."
    exit 1
fi

echo
echo "Vous avez choisi de restaurer au commit : $COMMIT_HASH"
echo "Description du commit :"
git show --quiet --pretty=format:"%h %s (%an, %ar)" "$COMMIT_HASH"

echo
echo "Options de restauration :"
echo "1) Restaurer temporairement (sans créer de nouveau commit)"
echo "2) Restaurer et créer un nouveau commit"
echo "3) Créer une nouvelle branche à partir de cette version"
echo

read -p "Choisissez une option (1/2/3) : " OPTION

case $OPTION in
    1)
        echo "Restauration temporaire au commit $COMMIT_HASH..."
        git checkout "$COMMIT_HASH"
        echo
        echo "Vous êtes maintenant en mode 'detached HEAD' au commit $COMMIT_HASH."
        echo "Pour revenir à l'état précédent, utilisez : git checkout main"
        ;;
    2)
        echo "Restauration avec création d'un nouveau commit..."
        git checkout main
        git reset --hard "$COMMIT_HASH"
        echo
        echo "Votre branche main a été restaurée à l'état du commit $COMMIT_HASH."
        echo "Pour pousser cette modification vers GitHub, utilisez : git push --force origin main"
        echo "ATTENTION : Cette opération écrasera l'historique sur GitHub !"
        ;;
    3)
        read -p "Nom de la nouvelle branche : " BRANCH_NAME
        if [ -z "$BRANCH_NAME" ]; then
            BRANCH_NAME="restore-$(date +%Y%m%d-%H%M%S)"
        fi
        echo "Création de la branche $BRANCH_NAME à partir du commit $COMMIT_HASH..."
        git checkout -b "$BRANCH_NAME" "$COMMIT_HASH"
        echo
        echo "Nouvelle branche $BRANCH_NAME créée à partir du commit $COMMIT_HASH."
        echo "Pour pousser cette branche vers GitHub, utilisez : git push -u origin $BRANCH_NAME"
        ;;
    *)
        echo "Option invalide. Opération annulée."
        exit 1
        ;;
esac

echo
echo "=== Opération terminée ==="