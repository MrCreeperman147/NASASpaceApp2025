# ⚡ Guide de Démarrage Rapide

**NASA Space Apps Challenge 2025 - Interactive World Map**

---

## 🚀 Installation en 3 Minutes

### Option A : Installation Automatique (Recommandé)

```bash
# 1. Cloner le projet
git clone https://github.com/votre-username/NASASpaceApp2025.git
cd NASASpaceApp2025

# 2. Rendre le script exécutable
chmod +x setup.sh

# 3. Lancer l'installation
./setup.sh
```

Le script va :
- ✅ Vérifier Python et pip
- ✅ Installer les dépendances
- ✅ Créer credentials.json
- ✅ Configurer .gitignore
- ✅ Tester la configuration

---

### Option B : Installation Manuelle

```bash
# 1. Cloner et installer
git clone https://github.com/votre-username/NASASpaceApp2025.git
cd NASASpaceApp2025
pip install -r requirements.txt

# 2. Configurer les credentials
cp credentials.json.example credentials.json
nano credentials.json  # Éditer avec vos identifiants

# 3. Vérifier la configuration
python check_credentials.py
```

---

## 🔑 Configuration des Credentials

### Étape 1 : Compte Copernicus (Obligatoire)

1. **Créer un compte** : https://dataspace.copernicus.eu/
2. **Activer le compte** : Vérifier votre email
3. **Éditer `credentials.json`** :

```json
{
  "copernicus": {
    "username": "votre_email@example.com",
    "password": "votre_mot_de_passe"
  }
}
```

### Étape 2 : Google Drive (Optionnel)

Seulement si vous voulez utiliser l'upload automatique vers Drive.

1. **Console Google Cloud** : https://console.cloud.google.com/
2. **Créer un projet** et activer l'API Drive
3. **Créer credentials OAuth 2.0** (type: Desktop app)
4. **Télécharger le JSON** et copier dans `credentials.json`

Voir [SECURITY.md](SECURITY.md) pour le guide détaillé.

---

## ✅ Vérifier la Configuration

```bash
# Lancer le script de vérification
python check_credentials.py
```

**Résultat attendu :**
```
✅ Toutes les vérifications sont passées (6/6)
🚀 Vous pouvez utiliser le projet en toute sécurité!
```

**Si des erreurs apparaissent :**
- ❌ Credentials manquants → Éditer `credentials.json`
- ❌ Tracké par Git → Exécuter `git rm --cached credentials.json`
- ❌ Connexion API échouée → Vérifier username/password

---

## 🎯 Utilisation Rapide

### 1. Interface Cartographique

```bash
python src/main.py
```

**Fonctionnalités :**
- 🗺️ Carte interactive Folium
- 📍 Marqueurs personnalisés
- 🌐 Ouverture dans le navigateur
- 💾 Export HTML

### 2. Télécharger des Images Sentinel-2

```bash
# Éditer les paramètres dans sentinelAPI.py (ligne ~1100)
python src/api/sentinelAPI.py
```

**Configuration :**
```python
csv_file = "marees.csv"           # Fichier de marées
max_cloud_cover = 20              # % nuages max
time_window_hours = 1             # Fenêtre temporelle
filter_tile_pair = ['T20TNT', 'T20TPT']  # Tuiles requises
```

### 3. Filtrer les Données de Marée

```python
from src.water_level_filter import WaterLevelFilter

# Charger le CSV
filter_obj = WaterLevelFilter("marees.csv")
filter_obj.load_csv_data()

# Filtrer par niveau (marée haute > 1.5m)
high_tide = filter_obj.filter_by_level_range(1.5, 2.5)

# Export
filter_obj.export_filtered_data(high_tide, "high_tide.csv")
```

### 4. Calculer des Surfaces (NDVI)

```bash
# 1. Préparer les mosaïques
python src/qgis/traitement_qgis.py

# 2. Calculer les surfaces
python src/qgis/code_de_surface.py
```

---

## 📊 Exemples de Workflows

### Workflow 1 : Analyse d'Érosion Côtière

```bash
# 1. Télécharger images aux marées extrêmes
python src/api/sentinelAPI.py

# 2. Créer les mosaïques
python src/qgis/traitement_qgis.py

# 3. Calculer les surfaces émergées
python src/qgis/code_de_surface.py

# 4. Visualiser sur la carte
python src/main.py
```

### Workflow 2 : Sélection d'Images pour Étude

```python
from src.api.sentinelAPI import (
    load_credentials, 
    search_sentinel2_from_csv_dates,
    select_best_pairs_per_year,
    download_best_pairs
)

# Charger credentials
creds = load_credentials()
username = creds['copernicus']['username']
password = creds['copernicus']['password']

# Rechercher images
products = search_sentinel2_from_csv_dates(
    username, password,
    csv_file_path="marees.csv",
    max_cloud_cover=20,
    filter_tile_pair=['T20TNT', 'T20TPT']
)

# Sélectionner les meilleures par année
best_pairs = select_best_pairs_per_year(products)

# Télécharger uniquement les quicklooks
download_best_pairs(best_pairs, username, password, 'quicklook')
```

### Workflow 3 : Upload Automatique vers Drive

```python
from src.api.sentinelAPI import (
    load_credentials,
    search_sentinel2_from_csv_dates,
    select_best_pairs_per_year,
    upload_best_pairs_to_drive
)

# Configuration et recherche
creds = load_credentials()
products = search_sentinel2_from_csv_dates(...)
best_pairs = select_best_pairs_per_year(products)

# Upload direct vers Google Drive
upload_best_pairs_to_drive(
    best_pairs, 
    username, 
    password,
    base_folder_name='Sentinel2_IlesMadeleine'
)
```

---

## 🔧 Paramètres Importants

### sentinelAPI.py

```python
# Recherche d'images
max_cloud_cover = 20              # 0-100%
time_window_hours = 2             # Fenêtre marée ±heures
max_tide_time_diff = 60           # Différence max (minutes)

# Filtrage
filter_tile_pair = ['T20TNT', 'T20TPT']  # Tuiles requises ensemble
```

### code_de_surface.py

```python
# Seuil NDVI (eau/terre)
threshold_value = 0.05            # ⬇️ = plus de sable
mean_min = 0.02                   # Filtre anti-eau (NDVI moyen)

# Nettoyage
min_object_pixels = 150           # Taille min objets (pixels)
min_area_m2 = 3000                # Taille min polygones finaux (m²)

# CRS
TARGET_EPSG = 32198               # MTM-8/NAD83 (Îles Madeleine)
```

---

## 🆘 Dépannage Rapide

### ❌ "Erreur d'authentification Copernicus"

```bash
# Vérifier les credentials
cat credentials.json | grep copernicus -A 3

# Tester manuellement
python check_credentials.py
```

**Solutions :**
- Vérifier username/password
- Vérifier que le compte est activé
- Essayer de se connecter sur le site

### ❌ "credentials.json not found"

```bash
# Vérifier l'existence
ls -la credentials.json

# Créer depuis le template
cp credentials.json.example credentials.json
nano credentials.json
```

### ❌ "Module not found"

```bash
# Réinstaller les dépendances
pip install -r requirements.txt --upgrade

# Vérifier l'installation
pip list | grep rasterio
pip list | grep geopandas
```

### ❌ "GDAL/PROJ errors"

```bash
# Avec conda (recommandé)
conda install -c conda-forge gdal rasterio geopandas

# Vérifier les chemins
python -c "import rasterio; print(rasterio.__version__)"
```

### ❌ "Git tracking credentials.json"

```bash
# Retirer du tracking
git rm --cached credentials.json
git commit -m "Remove credentials from tracking"

# Vérifier
git status | grep credentials
```

---

## 📚 Documentation

| Fichier | Description |
|---------|-------------|
| [README.md](README.md) | Documentation complète du projet |
| [SECURITY.md](SECURITY.md) | Guide de sécurité détaillé |
| [check_credentials.py](check_credentials.py) | Script de vérification |
| [setup.sh](setup.sh) | Script d'installation automatique |

---

## 🔒 Checklist Sécurité

Avant de commiter :

- [ ] `python check_credentials.py` → ✅ OK
- [ ] `git status` → credentials.json **absent**
- [ ] Pas de credentials en dur dans le code
- [ ] .gitignore à jour

---

## 📞 Aide

**Questions ?** Ouvrir une [Issue GitHub](https://github.com/votre-username/NASASpaceApp2025/issues)

**Problème de sécurité ?** Contacter en privé (pas d'issue publique)

---

## 🎉 Prêt !

Vous êtes maintenant prêt à utiliser le projet !

```bash
# Lancer l'interface
python src/main.py

# Bon exploration ! 🚀
```

---

**Dernière mise à jour** : Octobre 2025  
**Version** : 1.0.0