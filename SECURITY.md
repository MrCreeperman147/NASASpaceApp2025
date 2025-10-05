# 🔒 Guide de Sécurité - NASA Space Apps Challenge 2025

## ⚠️ IMPORTANT : Gestion des Credentials

Ce projet utilise des APIs externes qui nécessitent des identifiants d'authentification. **Ne JAMAIS commiter vos credentials dans Git !**

---

## 📋 Configuration Initiale

### 1. Copier le Template

```bash
cp credentials.json.example credentials.json
```

### 2. Configurer les Credentials Copernicus

#### A. Créer un Compte
1. Aller sur [Copernicus Data Space](https://dataspace.copernicus.eu/)
2. Cliquer sur "Register"
3. Remplir le formulaire d'inscription
4. Confirmer votre email

#### B. Éditer `credentials.json`
```json
{
  "copernicus": {
    "username": "votre_email@example.com",
    "password": "votre_mot_de_passe"
  }
}
```

### 3. Configurer Google Drive (Optionnel)

Pour utiliser la fonction d'upload automatique vers Google Drive :

#### A. Créer un Projet Google Cloud
1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un nouveau projet
3. Activer l'API Google Drive :
   - Menu → APIs & Services → Library
   - Rechercher "Google Drive API"
   - Cliquer "Enable"

#### B. Créer des Credentials OAuth 2.0
1. Menu → APIs & Services → Credentials
2. Cliquer "Create Credentials" → "OAuth client ID"
3. Type d'application : "Desktop app"
4. Télécharger le fichier JSON
5. Copier les valeurs dans `credentials.json` :

```json
{
  "installed": {
    "client_id": "VOTRE_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "votre-project-id",
    "client_secret": "VOTRE_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

---

## 🛡️ Bonnes Pratiques

### ✅ À FAIRE
- Utiliser `credentials.json` pour stocker les identifiants
- Vérifier que `credentials.json` est dans `.gitignore`
- Utiliser des mots de passe forts
- Ne partager vos credentials qu'avec des personnes de confiance
- Révoquer les tokens si compromis

### ❌ À NE PAS FAIRE
- ❌ Commiter `credentials.json` dans Git
- ❌ Partager vos credentials publiquement
- ❌ Hardcoder les credentials dans le code
- ❌ Envoyer credentials.json par email non chiffré
- ❌ Partager des captures d'écran avec credentials visibles

---

## 🔍 Vérification

### Avant de Commiter

```bash
# Vérifier que credentials.json n'est PAS tracké
git status | grep credentials.json

# Si credentials.json apparaît, l'ajouter à .gitignore
echo "credentials.json" >> .gitignore
git add .gitignore
git commit -m "Add credentials.json to gitignore"

# Supprimer du cache Git si déjà commité
git rm --cached credentials.json
```

### Scanner les Commits Précédents

Si vous avez accidentellement commité des credentials :

```bash
# Utiliser BFG Repo-Cleaner (recommandé)
brew install bfg
bfg --delete-files credentials.json
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Ou utiliser git-filter-repo
pip install git-filter-repo
git filter-repo --path credentials.json --invert-paths

# Forcer le push (ATTENTION : coordonner avec l'équipe)
git push origin --force --all
```

---

## 🔄 Migration du Code Existant

Si vous avez déjà des credentials en dur dans le code :

### Avant (❌ NON SÉCURISÉ)
```python
# Dans sentinelAPI.py
username = "brightogbeiwi@gmail.com"
password = "MrCreeperman147+*"
```

### Après (✅ SÉCURISÉ)
```python
# Dans sentinelAPI.py
from sentinelAPI import load_credentials

creds = load_credentials("credentials.json")
username = creds['copernicus']['username']
password = creds['copernicus']['password']
```

---

## 🚨 En Cas de Fuite

Si vos credentials ont été exposés publiquement :

### 1. Copernicus
1. Aller sur [Copernicus Data Space](https://dataspace.copernicus.eu/)
2. Se connecter avec les anciens identifiants
3. Aller dans "Account Settings"
4. Changer immédiatement le mot de passe

### 2. Google Cloud
1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. APIs & Services → Credentials
3. Supprimer les anciennes credentials OAuth
4. Créer de nouvelles credentials
5. Mettre à jour `credentials.json`

### 3. Nettoyer Git
```bash
# Supprimer l'historique des credentials
git filter-repo --path credentials.json --invert-paths

# Créer un nouveau credentials.json avec nouveaux identifiants
cp credentials.json.example credentials.json
# Éditer avec les nouveaux identifiants

# Push force
git push origin --force --all
```

---

## 📦 Variables d'Environnement (Alternative)

Pour une sécurité accrue, vous pouvez utiliser des variables d'environnement :

### 1. Créer un fichier `.env`

```bash
# .env (ne pas commiter)
COPERNICUS_USERNAME=votre_email@example.com
COPERNICUS_PASSWORD=votre_mot_de_passe
GOOGLE_CLIENT_ID=votre_client_id
GOOGLE_CLIENT_SECRET=votre_client_secret
```

### 2. Charger avec python-dotenv

```python
# Installation
pip install python-dotenv

# Utilisation
from dotenv import load_dotenv
import os

load_dotenv()

username = os.getenv('COPERNICUS_USERNAME')
password = os.getenv('COPERNICUS_PASSWORD')
```

### 3. Mettre à jour `.gitignore`

```
.env
.env.local
.env.*.local
```

---

## 🔐 Chiffrement des Credentials (Avancé)

Pour les environnements de production, utilisez un gestionnaire de secrets :

### Option 1 : Keyring (Local)
```python
import keyring

# Stocker
keyring.set_password("copernicus", "username", "votre_email@example.com")
keyring.set_password("copernicus", "password", "votre_mot_de_passe")

# Récupérer
username = keyring.get_password("copernicus", "username")
password = keyring.get_password("copernicus", "password")
```

### Option 2 : HashiCorp Vault (Production)
```python
import hvac

client = hvac.Client(url='http://127.0.0.1:8200')
client.token = 'your-vault-token'

# Récupérer
secret = client.secrets.kv.v2.read_secret_version(path='copernicus')
username = secret['data']['data']['username']
password = secret['data']['data']['password']
```

### Option 3 : AWS Secrets Manager (Cloud)
```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-1')
response = client.get_secret_value(SecretId='copernicus/credentials')
secrets = json.loads(response['SecretString'])

username = secrets['username']
password = secrets['password']
```

---

## 📊 Checklist de Sécurité

Avant de partager votre projet :

- [ ] `credentials.json` est dans `.gitignore`
- [ ] Pas de credentials en dur dans le code
- [ ] `credentials.json.example` est présent et sans vraies valeurs
- [ ] `token.pickle` est dans `.gitignore`
- [ ] Scanner avec `git secrets` ou `trufflehog`
- [ ] README contient les instructions de configuration
- [ ] Variables sensibles identifiées et documentées

---

## 🛠️ Outils de Scanning

### Git Secrets (Prévention)
```bash
# Installation
brew install git-secrets

# Configuration
git secrets --install
git secrets --register-aws

# Scanner le repo
git secrets --scan
```

### TruffleHog (Détection)
```bash
# Installation
pip install trufflehog

# Scanner l'historique complet
trufflehog git file://. --json
```

### Gitleaks (CI/CD)
```bash
# Installation
brew install gitleaks

# Scanner
gitleaks detect --source . --verbose

# Configuration pour GitHub Actions
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: gitleaks/gitleaks-action@v2
```

---

## 📚 Ressources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [12 Factor App - Config](https://12factor.net/config)
- [Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

## 📞 Support

En cas de problème de sécurité :
1. Ne pas créer d'issue publique
2. Contacter l'équipe en privé
3. Changer immédiatement les credentials compromis
4. Documenter l'incident pour amélioration future

---

**Dernière mise à jour** : Octobre 2025  
**Auteur** : Équipe NASA Space Apps Challenge 2025