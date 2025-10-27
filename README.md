# 🎯 Killer Game - Guide Complet de Configuration et Déploiement

Ce guide vous explique comment configurer et déployer le jeu Killer de A à Z.

---

## 📋 Table des matières

1. [Création du Google Form](#1--création-du-google-form)
2. [Sheet des défis personnalisés](#2--sheet-des-défis-personnalisés)
3. [Téléchargement et organisation des données](#3--téléchargement-et-organisation-des-données)
4. [Renommage des photos](#4--renommage-des-photos)
5. [Envoi automatique des emails](#5--envoi-automatique-des-emails)
6. [Test en local](#6--test-en-local)
7. [Déploiement sur serveur Zomro](#7--déploiement-sur-serveur-zomro)

---

## 1. 📝 Création du Google Form

### Colonnes obligatoires à créer

Créez un Google Form avec **toutes** les questions suivantes dans cet ordre :

| Nom de la colonne | Type de question | Options | Obligatoire |
|------------------|------------------|---------|-------------|
| `Horodateur` | Automatique | Activé dans les paramètres | Oui |
| `Surnom (le VRAI, pour pouvoir vous identifier)` | Texte court | - | Oui |
| `Année` | Choix multiple | 0a, 2a, 3a, 4a, 5a, 6a | Oui |
| `Sexe` | Choix multiple | H, F | Oui |
| `Votre mot de passe (vous devrez vous en SOUVENIR pour jouer, même en BO)` | Texte court | - | Oui |
| `Une photo de vous neuillesque (pour le jeu)` | Import de fichiers | Autoriser Google Drive | Oui |
| `une photo de vos pieds (pour le plaisir)` | Import de fichiers | Autoriser Google Drive | Non |
| `Combien y a t il de cars dans une kro ?` | Texte court | - | Non |
| `Est-ce que c'était mieux avant ?` | Choix multiple | Oui / Non / Je suis sénile | Non |
| `Un petit mot pour vos brasseurs adorés <3` | Paragraphe | - | Non |
| `Idées de défis complètement beuteuh (ça facilite le brassage)` | Paragraphe | - | Non |

### ⚠️ Configuration ESSENTIELLE des emails

**IMPORTANT** : Pour pouvoir envoyer les mots de passe aux joueurs juste avant le jeu, vous **DEVEZ** activer la collecte automatique des adresses email :

1. Dans les paramètres du formulaire (⚙️ en haut à droite)
2. Cochez **"Collecter les adresses e-mail"**
3. Cette option créera automatiquement une colonne `Adresse e-mail` dans les réponses

Sans cette configuration, vous ne pourrez **PAS** envoyer les mots de passe automatiquement !

### Colonnes système (ajoutées manuellement dans le CSV)

Ces colonnes seront gérées par le jeu et doivent être ajoutées dans votre CSV après export :

- `Cible actuelle` : Le surnom de la cible du joueur
- `État` : `alive`, `dead`, `admin`, `gaveup`
- `Tué par` : Surnom du killer (si mort)
- `Ordre d'élimination` : Numéro d'ordre (1, 2, 3...) initialisé à 0 pour tous. Si vous mettez -1 la personne ne sera pas comptée dans le jeu (utile pour faire des tests)
- `Nombre de kill` : Nombre de victimes initialisées à 0 pour tous
- `Admin` : `TRUE` ou `FALSE`
- `Téléphone` : Numéro de téléphone (format: 06.XX.XX.XX.XX)

### Paramètres du formulaire

- ✅ Activez "Collecter les adresses e-mail"
- ✅ Limitez à 1 réponse par personne
- ✅ Autorisez la modification après envoi (pour les retardataires)
- ✅ Dans "Réponses", cliquez sur l'icône Sheets pour créer une feuille de calcul liée

---

## 2. 📊 Sheet des défis personnalisés

### Création du fichier `defis.csv`

Créez un Google Sheet séparé (ou un onglet dans le même fichier) avec cette structure :

| Surnom | défis |
|--------|-------|
| user1 | lui faire boire de l'huile |
| user2 | lui faire manger un bout d'oignon cru |
| user3 | qu'il s'expose un ecocup sur le crane |

### Format des défis

- **Colonne A (Surnom)** : Le surnom EXACT du joueur (doit correspondre au formulaire)
- **Colonne B (défis)** : Le défi personnalisé pour éliminer ce joueur

### Conseils pour les défis

- Soyez créatifs mais respectueux du consentement
- Évitez les défis dangereux ou humiliants
- Testez les défis sur vous-même avant de les proposer
- Variez la difficulté : certains faciles, d'autres plus complexes
- Pensez à l'ambiance du WE (bars, soirées, activités...)

### Export du sheet

1. Fichier → Télécharger → Valeurs séparées par des virgules (.csv)
2. Renommez le fichier en `defis.csv`
3. Placez-le dans le dossier `data/`

---

## 3. 📥 Téléchargement et organisation des données

### Pourquoi télécharger les données ?

**L'API Google Drive est limitée et peut être surchargée** :
- ⏱️ Lenteur d'affichage des photos
- 🚫 Risque de dépassement des quotas API
- 💰 Coûts potentiels si trop de requêtes
- 🔒 Dépendance à la connexion internet

**Solution** : Télécharger toutes les photos en local pour un affichage instantané !

### Étape 1 : Exporter les réponses du formulaire

1. Ouvrez votre Google Form
2. Allez dans l'onglet **"Réponses"**
3. Cliquez sur l'icône **Google Sheets** (vert) pour ouvrir la feuille de calcul
4. Dans Google Sheets : **Fichier → Télécharger → Valeurs séparées par des virgules (.csv)**
5. Renommez le fichier téléchargé en **`formulaire.csv`**
6. Placez-le dans le dossier `data/` de votre projet

### Étape 2 : Télécharger automatiquement toutes les photos

**🚀 Utilisez le script automatique - Ne téléchargez RIEN manuellement !**

Le script fait tout le travail pour vous : téléchargement, conversion, renommage, optimisation.

#### Installation des dépendances

```bash
pip install requests pillow
```

#### Lancement du script

```bash
cd scripts
python download_photos.py
```

**C'est tout !** En quelques minutes, le script va :
- ✅ Lire automatiquement `data/formulaire.csv`
- ✅ Télécharger **toutes** les photos depuis Google Drive
- ✅ Les convertir en JPG et les optimiser (max 1200x1200px, qualité 90%)
- ✅ Les renommer automatiquement : `[Surnom].jpg` ou `[Surnom]_pieds.jpg`
- ✅ Les placer dans `data/images/tetes/` et `data/images/pieds/`
- ✅ Afficher un résumé détaillé des téléchargements

#### Exemple de sortie

```
🚀 Démarrage du téléchargement des photos...

[1] Traitement de admin1...
  ✅ Photo de profil sauvegardée: admin1.jpg
  ✅ Photo de pieds sauvegardée: admin1_pieds.jpg

[2] Traitement de user1...
  ✅ Photo de profil sauvegardée: user1.jpg
  ⊘  Pas de photo de pieds

============================================================
📊 RÉSUMÉ
Total de joueurs : 5
Photos de profil : 5 téléchargées
Photos de pieds : 3 téléchargées
============================================================
✅ Tous les téléchargements ont réussi !
```

#### Options avancées

```bash
# Test sans télécharger (voir ce qui serait fait)
python download_photos.py --dry-run

# Forcer le retéléchargement (écraser les fichiers existants)
python download_photos.py --force
```

#### En cas d'interruption

Le script est **idempotent** : si un téléchargement échoue ou est interrompu, relancez simplement la commande. Il ignorera les fichiers déjà téléchargés et reprendra là où il s'était arrêté.

```bash
python download_photos.py
```

📖 **Documentation complète** : `scripts/README.md`

⚠️ **Ne téléchargez PAS les photos manuellement** : c'est long, fastidieux, et sujet aux erreurs. Le script gère tout automatiquement !

### Arborescence finale

Après l'exécution du script, vous aurez :

```
killer/
└── data/
    ├── formulaire.csv       # Réponses du formulaire
    ├── defis.csv            # Défis personnalisés
    └── images/
        ├── tetes/           # Photos de profil (téléchargées automatiquement)
        │   ├── admin1.jpg
        │   ├── user1.jpg
        │   └── ...
        └── pieds/           # Photos de pieds (téléchargées automatiquement)
            ├── admin1_pieds.jpg
            ├── user1_pieds.jpg
            └── ...
```

---

## 4. ✅ Vérification des photos

Après avoir lancé le script, **vérifiez que tout s'est bien passé** :

Vous devriez voir des fichiers comme :
- `admin1.jpg`, `user1.jpg`, `user2.jpg`... dans `tetes/`
- `admin1_pieds.jpg`, `user1_pieds.jpg`... dans `pieds/`

### Format des noms de fichiers

Le script a automatiquement créé :
- **Photos de profil** : `data/images/tetes/[Surnom].jpg`
- **Photos de pieds** : `data/images/pieds/[Surnom]_pieds.jpg`

### Que faire en cas de problème ?

#### ❌ Certaines photos manquent

Le script affiche les échecs dans son résumé. Vérifiez :
1. Les liens Google Drive dans `formulaire.csv` sont corrects
2. Les photos sont bien partagées publiquement sur google drive

Puis relancez le script :
```bash
cd scripts
python download_photos.py
```

#### ❌ Une photo est floue ou de mauvaise qualité

Supprimez-la et retéléchargez :
```bash
rm data/images/tetes/[Surnom].jpg
cd scripts
python download_photos.py --force
```

#### ❌ Le script plante ou timeout

- Vérifiez votre connexion internet
- Relancez simplement, il reprendra où il s'était arrêté
- Les photos très lourdes peuvent prendre du temps

#### ❌ "Impossible d'extraire l'ID du lien"

Le format du lien Google Drive n'est pas reconnu. Vérifiez que c'est bien un lien de ce type :
- `https://drive.google.com/file/d/ID/view?usp=sharing`
- `https://drive.google.com/open?id=ID`

### ✅ Checklist avant de continuer

- [ ] Toutes les photos de profil sont présentes
- [ ] Les noms correspondent aux surnoms (pas d'erreur de frappe)
- [ ] Les photos s'affichent correctement (ouvrez-en quelques unes)
- [ ] Pas de messages d'erreur dans le résumé du script

Une fois que tout est OK, passez à l'étape suivante !

---

## 5. 📧 Envoi automatique des emails

### Objectif

Envoyer automatiquement les identifiants (surnom + mot de passe) à chaque joueur **juste avant le début du jeu**.

### Prérequis

1. ✅ Le fichier `formulaire.csv` doit contenir une colonne **`Adresse e-mail`**
2. ✅ Chaque ligne doit avoir un email valide
3. ✅ Vous devez avoir un compte SMTP (Gmail, Outlook, ou autre)

### Configuration SMTP

#### Avec Gmail

1. Créez un compte Gmail dédié (ex: `killer.weu56@gmail.com`)
2. Activez l'authentification à deux facteurs
3. Générez un "mot de passe d'application" :
   - Allez dans **Compte Google → Sécurité → Validation en deux étapes**
   - Cliquez sur **Mots de passe des applications**
   - Sélectionnez **Autre** et nommez-le "Killer"
   - Copiez le mot de passe généré (16 caractères, supprimer les espaces)

4. Créez un fichier `.env` dans le dossier `email/` :

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=killer.weu56@gmail.com
SMTP_PASSWORD=xxxxxxxxxxxxxxxx  # Mot de passe d'application
FROM_NAME=Killer WEU56
FROM_EMAIL=killer.weu56@gmail.com
```

#### Avec Outlook / Hotmail

```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=votre.email@outlook.com
SMTP_PASSWORD=votre_mot_de_passe
FROM_NAME=Killer WEU56
FROM_EMAIL=votre.email@outlook.com
```

### Format du CSV

Le fichier `formulaire.csv` **doit** contenir ces colonnes :

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `Surnom (le VRAI, pour pouvoir vous identifier)` | Identifiant du joueur | user1 |
| `Votre mot de passe (vous devrez vous en SOUVENIR pour jouer, même en BO)` | Mot de passe choisi | user1 |
| `Adresse e-mail` | Adresse email (collectée automatiquement) | user1@gmail.com |

**⚠️ ATTENTION** : La colonne `Adresse e-mail` est créée automatiquement par Google Forms **seulement si** vous avez activé "Collecter les adresses e-mail" dans les paramètres !

### Utilisation du script

```bash
cd email
python send_credentials.py \
  --csv ../data/formulaire.csv \
  --rate 1.0 \
  --login-url "http://188.137.182.53:8080/"
```

Le script charge automatiquement les variables d'environnement depuis le fichier `.env` à la racine du projet.

### Options du script

| Option | Description | Par défaut |
|--------|-------------|-----------|
| `--csv` | Chemin du fichier CSV | (obligatoire) |
| `--rate` | Délai entre chaque email (secondes) | 1.0 |
| `--login-url` | URL de connexion au jeu | (vide) |
| `--dry-run` | Tester sans envoyer les emails | Non activé |
| `--subject` | Objet de l'email | "Rappel pour le killer idf/mdp" |

### Test avant envoi

```bash
# Mode test (n'envoie pas les emails)
python send_credentials.py \
  --csv ../data/formulaire.csv \
  --dry-run
```

Vérifiez que :
- ✅ Tous les emails sont détectés
- ✅ Les surnoms sont corrects
- ✅ Les mots de passe sont présents

### Logs d'envoi

Le script génère un fichier `sent_log.csv` :

```csv
identifiant,email,status,error,timestamp
Astro,astro@example.com,sent,,1698765432.123
Nyhllo,nyhllo@example.com,error,Authentication failed,1698765433.456
```

### Conseils

- 🕐 **Envoyez les emails 1-2 heures avant le début du jeu** (pas trop tôt)
- 📱 Testez d'abord sur **votre propre email**
- 🔄 Si un envoi échoue, vous pouvez **relancer le script** (les emails déjà envoyés seront enregistrés)
- 📊 Vérifiez le taux de réussite dans `sent_log.csv`

---

## 6. 🧪 Test en local

### Installation

```bash
# Cloner le projet
git clone [votre-repo]
cd killer

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration

Créez un fichier `.env` à la racine :

```bash
FLASK_SECRET_KEY=votre_secret_key_aleatoire
FLASK_DEBUG=True
PORT=8080
```

### Lancement

```bash
python server.py
```

L'application sera accessible sur : **http://localhost:8080**

### Tests à effectuer

1. ✅ Page de connexion s'affiche correctement
2. ✅ Connexion avec un compte joueur (surnom + mot de passe)
3. ✅ Les photos des joueurs s'affichent
4. ✅ La cible est affichée avec son défi
5. ✅ Le formulaire de kill fonctionne
6. ✅ Les admins peuvent valider/refuser les kills
7. ✅ Le classement s'affiche correctement

### Logs de débogage

```bash
# Voir les requêtes HTTP
tail -f server.log

# En mode debug, les erreurs s'affichent directement dans le navigateur
```

---

## 7. 🚀 Déploiement sur serveur Zomro

### Pourquoi Zomro ?

- 💰 Prix abordables (à de 0.016 centimes / heures)
- 🌍 Serveurs en Europe (faible latence)
- 🛠️ Accès root complet
- 📈 Ressources garanties

### Choix du serveur

#### Configuration minimale (50-100 joueurs)

- **RAM** : 2 GB
- **CPU** : 2 cœurs
- **Stockage** : 20 GB SSD
- **Bande passante** : 1 TB/mois
- **Prix** : ~8-10€/mois

### Achat et configuration du serveur

1. **Créer un compte sur Zomro** : https://zomro.com
2. **Commander un VPS** :
   - Choisissez **Ubuntu 22.04 LTS** (recommandé)
   - Sélectionnez la configuration souhaitée
   - Notez votre **adresse IP** et **mot de passe root**

3. **Configurer l'accès SSH** :

```bash
# Tester la connexion
ssh root@VOTRE_IP

# (Recommandé) Configurer une clé SSH pour éviter le mot de passe
ssh-keygen -t rsa -b 4096
ssh-copy-id root@VOTRE_IP
```

4. **Installer les dépendances sur le serveur** :

```bash
ssh root@VOTRE_IP

# Mise à jour du système
apt update && apt upgrade -y

# Installation de Python et outils
apt install -y python3 python3-venv python3-pip git curl

# Installation de systemd (si pas déjà installé)
apt install -y systemd
```

### Déploiement initial

1. **Modifier l'IP dans le script** :

Éditez `deploy_initial.sh` :

```bash
ZOMRO_IP="VOTRE_IP_ICI"  # Remplacez par votre IP Zomro
```

2. **Rendre le script exécutable** :

```bash
chmod +x deploy_initial.sh
```

3. **Lancer le déploiement** :

```bash
./deploy_initial.sh
```

Le script va :
- ✅ Copier tous les fichiers (code + CSV + images)
- ✅ Installer Python et les dépendances
- ✅ Créer un service systemd
- ✅ Démarrer l'application
- ✅ Configurer le redémarrage automatique

⏱️ **Durée estimée** : 5-10 minutes (selon la taille des photos)

### Vérification du déploiement

```bash
# Vérifier que le service tourne
ssh root@VOTRE_IP 'systemctl status killer'

# Voir les logs en temps réel
ssh root@VOTRE_IP 'tail -f /var/log/killer.log'

# Tester l'accès
curl http://VOTRE_IP:8080/health
```

Si tout fonctionne, vous verrez :
```json
{"status": "ok"}
```

### Accès à l'application

L'application sera accessible sur : **http://VOTRE_IP:8080**

Partagez ce lien aux joueurs !

### Mises à jour rapides

Pour les modifications de code (sans changer les photos) :

```bash
./deploy_update.sh
```

⏱️ **Durée** : 30 secondes seulement !

### Commandes utiles

```bash
# Redémarrer l'application
ssh root@VOTRE_IP 'systemctl restart killer'

# Arrêter l'application
ssh root@VOTRE_IP 'systemctl stop killer'

# Voir les logs d'erreur
ssh root@VOTRE_IP 'tail -50 /var/log/killer.error.log'

# Vérifier l'espace disque
ssh root@VOTRE_IP 'df -h'

# Vérifier la RAM utilisée
ssh root@VOTRE_IP 'free -h'
```

### Résolution de problèmes

#### L'application ne démarre pas

```bash
# Vérifier les logs détaillés
ssh root@VOTRE_IP 'journalctl -u killer -n 100'

# Vérifier les permissions
ssh root@VOTRE_IP 'ls -la /var/www/killer'

# Tester manuellement
ssh root@VOTRE_IP
cd /var/www/killer
source .venv/bin/activate
python server.py
```

#### Les photos ne s'affichent pas

```bash
# Vérifier que les photos sont présentes
ssh root@VOTRE_IP 'ls -la /var/www/killer/data/images/tetes/'

# Vérifier les permissions
ssh root@VOTRE_IP 'chmod -R 755 /var/www/killer/data/images/'
```

#### Erreur 502 Bad Gateway

```bash
# Le service n'est pas démarré
ssh root@VOTRE_IP 'systemctl start killer'
```

---

## 📞 Support

Pour toute question ou problème :

1. 📖 Consultez ce README
2. 🔍 Vérifiez les logs : `/var/log/killer.log`
3. 💬 Contactez moi sur FB : Charles Bergeat (Nyhllö)

---

## 🎉 Bon jeu !

Une fois tout configuré :

1. ✅ Les joueurs reçoivent leurs identifiants par email
2. ✅ Ils se connectent sur l'application
3. ✅ Ils découvrent leur cible et leur défi
4. ✅ Le jeu commence !

**Amusez-vous bien et que le meilleur killer gagne ! 🔪🎯**

