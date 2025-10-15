# KILLER - Jeu de l'assassin

Une application web pour gérer le jeu du Killer, permettant aux joueurs de se connecter, voir leur cible, et marquer leurs "kills".

## Table des matières

1. [Présentation](#présentation)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Utilisation](#utilisation)
5. [Tests Manuels](#tests-manuels)
6. [Limitations connues et recommandations](#limitations-connues-et-recommandations)
7. [Remarques techniques](#remarques-techniques)

## Présentation

Cette application permet de gérer un jeu de Killer où :
- Chaque joueur a une cible à éliminer selon une action spécifique
- Après avoir éliminé sa cible, le joueur hérite de la cible suivante
- Le jeu continue jusqu'à ce qu'il ne reste qu'un seul survivant

## Installation

### Prérequis

- Python 3.9 ou supérieur
- Un compte Google pour accéder à Google Sheets API

### Étapes d'installation

1. Clonez ce dépôt sur votre machine locale
   ```bash
   git clone <url-du-dépôt>
   cd killer_project
   ```

2. Installez les dépendances requises
   ```bash
   pip install -r requirements.txt
   ```

3. Créez et configurez votre compte de service Google (voir section Configuration)

4. Créez un fichier `.env` à partir du fichier `.env.example` et remplissez les variables d'environnement nécessaires

5. Démarrez le serveur
   ```bash
   python server.py
   ```
   ou
   ```bash
   flask run
   ```

6. Accédez à l'application via votre navigateur à l'adresse http://localhost:5000

## Configuration

### 1. Création d'un compte de service Google

1. Rendez-vous sur la [Console Google Cloud](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Activez l'API Google Sheets pour votre projet
   - Dans "Bibliothèque d'API", recherchez et activez "Google Sheets API"
4. Créez un compte de service :
   - Allez dans "IAM et administration" > "Comptes de service"
   - Cliquez sur "Créer un compte de service"
   - Donnez un nom à votre compte de service et une description
   - Accordez au compte de service le rôle "Éditeur" (ou un rôle personnalisé avec des permissions de lecture/écriture)
   - Cliquez sur "Continuer" puis "Terminé"
5. Créez une clé pour votre compte de service :
   - Dans la liste des comptes de service, cliquez sur le compte que vous venez de créer
   - Allez dans l'onglet "Clés"
   - Cliquez sur "Ajouter une clé" > "Créer une clé"
   - Sélectionnez "JSON" comme type de clé
   - Une clé sera téléchargée sur votre ordinateur

6. Renommez le fichier téléchargé en `service_account.json` et placez-le à la racine du projet

### 2. Configuration de la feuille Google Sheets

1. Accédez à la [feuille Google Sheets](https://docs.google.com/spreadsheets/d/1MSGo1flz_yyGKcJ0EQdnx4Qe92ciNu9gXMu9EYp6OH4/edit?usp=sharing)
2. Assurez-vous que la feuille contient les colonnes suivantes :
   - `Nom`
   - `Prénom` 
   - `Année`
   - `Surnom du tueur`
   - `Mot de passe`
   - `Surnom de sa cible`
   - `Action à réaliser`
   - `État` (cette colonne sera ajoutée automatiquement au premier démarrage de l'application)
   
3. Partagez votre feuille avec l'adresse email du compte de service :
   - Ouvrez votre feuille Google Sheets
   - Cliquez sur le bouton "Partager" en haut à droite
   - Ajoutez l'adresse email de votre compte de service (elle se trouve dans le fichier `service_account.json`, recherchez le champ `client_email`)
   - Accordez-lui les droits d'édition (rôle "Éditeur")
   - Désactivez la notification
   - Cliquez sur "Partager"

### 3. Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet avec les informations suivantes :

```
FLASK_SECRET_KEY=une_clé_secrète_longue_et_aléatoire
SERVICE_ACCOUNT_FILE=service_account.json
SHEET_ID=1MSGo1flz_yyGKcJ0EQdnx4Qe92ciNu9gXMu9EYp6OH4
```

Remplacez `une_clé_secrète_longue_et_aléatoire` par une chaîne de caractères aléatoire. Vous pouvez en générer une avec Python :

```python
import secrets
print(secrets.token_hex(16))
```

## Utilisation

### 1. Préparation de la feuille de données

1. Remplissez la feuille Google Sheets avec les informations des joueurs
2. Assurez-vous que chaque joueur possède :
   - Un nom et prénom
   - Une année (classe, promotion, etc.)
   - Un surnom unique (utilisé pour la connexion)
   - Un mot de passe
   - Le surnom de sa cible
   - Une action à réaliser pour éliminer sa cible

### 2. Utilisation de l'application

1. Les joueurs se connectent avec leur surnom et mot de passe
2. Une fois connecté, chaque joueur voit :
   - Ses propres informations (nom, prénom, surnom, année)
   - Les informations de sa cible actuelle (nom, prénom, surnom, année)
   - L'action qu'il doit réaliser pour éliminer sa cible
3. Lorsqu'un joueur élimine sa cible, il clique sur le bouton "J'ai tué ma cible"
4. Le système attribue automatiquement la prochaine cible au joueur
5. Le jeu continue jusqu'à ce qu'il ne reste plus qu'un joueur vivant

## Tests Manuels

Voici quelques scénarios de test pour vérifier le bon fonctionnement de l'application :

### Test 1: Authentification
1. Ouvrez l'application dans votre navigateur
2. Entrez un surnom et un mot de passe valides
3. Vérifiez que vous êtes redirigé vers la page principale avec les informations de votre profil et de votre cible

### Test 2: Processus de kill
1. Connectez-vous avec deux comptes différents (dans deux navigateurs ou en mode navigation privée)
2. Avec le compte du "tueur", notez les informations de la cible
3. Cliquez sur le bouton "J'ai tué ma cible"
4. Vérifiez que vous recevez la prochaine cible
5. Connectez-vous avec le compte de la "victime" et vérifiez qu'il ne peut plus se connecter ou qu'il est marqué comme "mort"

### Test 3: Chaîne de cibles
1. Configurez une chaîne de 3 joueurs où A cible B, B cible C, et C cible A
2. Connectez-vous en tant que A et éliminez B
3. Vérifiez qu'A obtient maintenant C comme cible
4. Éliminez C et vérifiez que le jeu détecte la fin de partie (aucune cible vivante)

## Limitations connues et recommandations

### Sécurité
- **Mots de passe en clair**: Dans cette implémentation, les mots de passe sont stockés en clair dans la feuille Google Sheets, ce qui n'est pas recommandé pour un environnement de production.
  - **Recommandation**: Migrer vers un système utilisant des hashes. Pour ce faire, ajoutez une colonne pour stocker des hashes bcrypt et modifiez la logique d'authentification dans le serveur.

### Concurrence
- **Risques de race conditions**: Si plusieurs joueurs tentent de tuer des cibles en même temps, des incohérences peuvent survenir car l'API Google Sheets n'offre pas de transactions atomiques.
  - **Recommandation**: Implémentez un système de verrouillage simple en ajoutant une colonne "locked" dans la feuille, ou utilisez Google Apps Script pour gérer la concurrence.

### Performance
- **Limitations de l'API Google Sheets**: Les requêtes Google Sheets API sont limitées en fréquence et peuvent être lentes sous charge.
  - **Recommandation**: Pour une utilisation intensive, migrez vers une base de données dédiée (SQLite, PostgreSQL, etc.).

### Autres recommandations
- Ajouter un système de logs pour suivre les actions (qui a tué qui et quand)
- Implémenter une vue administrateur pour gérer les joueurs et résoudre les problèmes
- Ajouter un système de notifications (email, SMS) pour informer les joueurs des changements

## Remarques techniques

### Structure de la colonne "État"
L'application ajoute automatiquement une colonne "État" à la feuille Google Sheets si elle n'existe pas déjà. Cette colonne contient l'une des valeurs suivantes:
- `alive` : le joueur est toujours en vie et participe au jeu
- `dead` : le joueur a été éliminé

### Logique de transfert de cible
Lorsqu'un joueur élimine sa cible, le système:
1. Récupère la cible actuelle de la victime (qui devient la nouvelle cible du tueur)
2. Si cette nouvelle cible est déjà morte, il cherche récursivement la prochaine cible vivante
3. Si aucune cible vivante n'est trouvée, le joueur n'a plus de cible, ce qui indique la fin du jeu

### Endpoint de débogage
L'application inclut un endpoint de débogage (`/api/debug`) qui affiche l'état complet de la feuille. Il est accessible uniquement pour les utilisateurs connectés, mais devrait être désactivé ou protégé par une authentification supplémentaire en production.