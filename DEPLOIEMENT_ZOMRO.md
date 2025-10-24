# 🚀 Guide de déploiement sur Zomro

## 📋 Informations du serveur

- **IP**: 188.137.182.53
- **Utilisateur**: root
- **Port application**: 8080
- **Répertoire**: /var/www/killer

## ⚡ Déploiement rapide

### Option 1 : Déploiement complet (recommandé)

```bash
./zomro.sh deploy
```

Cette commande va :
1. ✅ Vérifier que tous les fichiers nécessaires sont présents
2. 🧹 Nettoyer les fichiers temporaires
3. 📤 Copier tous les fichiers sur le serveur
4. 📦 Créer un environnement virtuel Python
5. 📥 Installer toutes les dépendances
6. ⚙️ Configurer le service systemd
7. 🚀 Démarrer l'application

**Note**: Vous devrez entrer le mot de passe root du serveur Zomro.

### Option 2 : Mise à jour rapide (sans tout réinstaller)

Si l'application est déjà déployée et que vous voulez juste mettre à jour le code :

```bash
# 1. Copier les fichiers modifiés
scp server.py root@188.137.182.53:/var/www/killer/
scp client/app.js root@188.137.182.53:/var/www/killer/client/
scp -r data root@188.137.182.53:/var/www/killer/

# 2. Redémarrer l'application
ssh root@188.137.182.53 'systemctl restart killer'
```

## 🔧 Commandes utiles

### Vérifier l'état de l'application

```bash
ssh root@188.137.182.53 'systemctl status killer'
```

### Voir les logs en temps réel

```bash
ssh root@188.137.182.53 'tail -f /var/log/killer.log'
```

### Redémarrer l'application

```bash
ssh root@188.137.182.53 'systemctl restart killer'
```

### Arrêter l'application

```bash
ssh root@188.137.182.53 'systemctl stop killer'
```

### Vérifier les ports utilisés

```bash
./zomro.sh check
```

### Tester la connectivité aux API Google

```bash
./zomro.sh test
```

### Nettoyer les fichiers temporaires locaux

```bash
./zomro.sh clean
```

## 🌐 Accéder à l'application

Une fois déployée, l'application est accessible à :

**http://188.137.182.53:8080**

## 🔍 Résolution des problèmes

### Problème : L'application ne démarre pas

```bash
# Vérifier les logs d'erreur
ssh root@188.137.182.53 'tail -50 /var/log/killer.error.log'

# Vérifier que le port n'est pas déjà utilisé
./zomro.sh check
```

### Problème : Les photos ne s'affichent pas

```bash
# Vérifier que le dossier data est bien copié
ssh root@188.137.182.53 'ls -la /var/www/killer/data/images/'

# Re-copier les données si nécessaire
scp -r data root@188.137.182.53:/var/www/killer/
ssh root@188.137.182.53 'systemctl restart killer'
```

### Problème : Erreurs de connectivité Google Sheets

```bash
# Appliquer les correctifs SSL
./zomro.sh fix

# Redémarrer l'application
ssh root@188.137.182.53 'systemctl restart killer'
```

### Problème : Le service ne répond plus

```bash
# Tuer tous les processus Python
ssh root@188.137.182.53 'pkill -f python'

# Redémarrer le service
ssh root@188.137.182.53 'systemctl restart killer'
```

## 📦 Structure des fichiers sur le serveur

```
/var/www/killer/
├── server.py                  # Application Flask
├── requirements.txt           # Dépendances Python
├── service_account.json       # Credentials Google
├── .env                       # Variables d'environnement
├── .venv/                     # Environnement virtuel Python
├── client/                    # Fichiers frontend
│   ├── app.js
│   ├── index.html
│   ├── style.css
│   └── img/
├── data/                      # Données locales
│   ├── formulaire.csv
│   ├── defis.csv
│   └── images/
│       ├── tetes/
│       └── pieds/
└── flask_session/            # Sessions Flask
```

## 🔐 Sécurité

- Le fichier `service_account.json` contient des credentials sensibles
- Assurez-vous qu'il n'est **jamais** commité dans Git
- Le fichier `.env` est également sensible et ne doit pas être partagé

## 📝 Notes importantes

1. **Port 8080** : L'application écoute sur le port 8080 (pas 5000)
2. **Systemd** : L'application est gérée par systemd et redémarre automatiquement en cas d'erreur
3. **Logs** : Tous les logs sont dans `/var/log/killer.log` et `/var/log/killer.error.log`
4. **Cache** : Les photos sont servies depuis `/var/www/killer/data/images/`

## ✅ Checklist avant déploiement

- [ ] Le fichier `service_account.json` est présent
- [ ] Le dossier `data/` contient les CSV et images
- [ ] Le fichier `client/app.js` a été mis à jour avec le fix des photos
- [ ] Le script `zomro.sh` est exécutable (`chmod +x zomro.sh`)
- [ ] Vous avez le mot de passe root du serveur Zomro

## 🎯 Workflow de développement recommandé

1. **Développer localement**
   ```bash
   python server.py
   # Tester sur http://localhost:8080
   ```

2. **Tester que tout fonctionne**
   - Connexion
   - Affichage des photos
   - Kill/Killed
   - Leaderboard

3. **Déployer sur Zomro**
   ```bash
   ./zomro.sh deploy
   ```

4. **Vérifier que ça fonctionne**
   ```bash
   curl -I http://188.137.182.53:8080/health
   ```

## 🆘 Support

En cas de problème, consultez :
- Les logs : `ssh root@188.137.182.53 'tail -100 /var/log/killer.log'`
- L'état du service : `ssh root@188.137.182.53 'systemctl status killer'`
- Le README.md pour plus de détails techniques

