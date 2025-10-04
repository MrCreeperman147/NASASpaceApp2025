# NASASpaceApp2025

Projet pour le NASA Space Apps Challenge 2025 - Analyse et traitement de données géospatiales.

## 📋 Description

Ce projet utilise des technologies de traitement d'images et d'analyse géospatiale pour [décrire l'objectif de votre projet].

## 🛠️ Technologies utilisées

### Langages et environnement
- **Python 3.12** - Langage principal du projet
- **Virtual Environment** - Isolation des dépendances

### Traitement géospatial et raster
- **GDAL 3.11.1** - Bibliothèque de référence pour les données géospatiales
- **Rasterio 1.4.3** - Interface Python pour GDAL, lecture/écriture de fichiers raster
- **Shapely 2.1.2** - Manipulation d'objets géométriques
- **PySTAC 1.14.1** - Catalogage de données spatiotemporelles

### Traitement d'images et vision
- **OpenCV 4.12.0** - Vision par ordinateur et traitement d'images avancé
- **Scikit-image 0.25.2** - Algorithmes de traitement d'images scientifiques
- **Pillow 11.3.0** - Manipulation d'images de base
- **ImageIO 2.37.0** - Lecture/écriture de formats d'images multiples
- **TIFFfile 2025.9.30** - Support avancé pour fichiers TIFF

### Analyse de données scientifiques
- **NumPy 2.3.3** - Calculs numériques et manipulation d'arrays
- **Pandas 2.3.3** - Manipulation et analyse de données tabulaires
- **SciPy 1.16.2** - Algorithmes scientifiques et statistiques
- **Xarray 2025.1.1** - Manipulation de données multidimensionnelles étiquetées
- **PyArrow 21.0.0** - Traitement de données colonnaires haute performance

### Calcul parallèle et distribué
- **Dask 2025.9.1** - Calcul parallèle pour datasets volumineux
- **Distributed 2025.9.1** - Calcul distribué avec Dask

### Visualisation et interfaces
- **Matplotlib 3.10.6** - Création de graphiques et visualisations
- **Bokeh 3.8.0** - Visualisations interactives web

### Analyse de réseaux et connectivité
- **NetworkX 3.5** - Création, manipulation et analyse de graphes
- **Requests 2.32.5** - Client HTTP pour APIs
- **OpenEO 0.45.0** - Interface pour traitement cloud de données Earth Observation

### Utilitaires et support
- **Click 8.3.0** - Interface en ligne de commande
- **PyYAML 6.0.3** - Parsing de fichiers de configuration YAML
- **Affine 2.4.0** - Transformations géométriques affines
- **FSspec 2025.9.0** - Interface filesystem abstraite

## 🚀 Installation

### Prérequis

- Python 3.12.x installé
- Git installé

### Étapes d'installation

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/MrCreeperman147/NASASpaceApp2025.git
   cd NASASpaceApp2025
   ```

2. **Créer l'environnement virtuel**
   ```bash
   py -3.12 -m venv venv
   ```

3. **Activer l'environnement**
   
   **Sur Windows (CMD):**
   ```bash
   venv\Scripts\activate
   ```
   
   **Sur Windows (PowerShell):**
   ```powershell
   venv\Scripts\Activate.ps1
   ```
   
   **Sur Linux/macOS:**
   ```bash
   source venv/bin/activate
   ```

4. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

5. **Vérifier l'installation**
   ```bash
   python test_libraries.py
   ```

## 📁 Structure du projet

```
NASASpaceApp2025/
├── data/              # Données (non versionnées)
├── src/               # Code source
├── tests/             # Tests unitaires
├── main.py            # Point d'entrée principal
├── requirements.txt   # Dépendances Python
└── README.md          # Ce fichier
```

## 💻 Utilisation

```bash
# Activer l'environnement virtuel
venv\Scripts\activate

# Exécuter le programme principal
python main.py
```

## 🧪 Tests

```bash
# Exécuter les tests
python -m pytest tests/

# Tester les librairies
python test_libraries.py
```

## 📊 Données

Les données utilisées proviennent de [source des données].

Placez vos données dans le dossier `data/raw/`.

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Committez vos changements (`git commit -m 'Ajout de fonctionnalité'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

## 📝 Licence

Aucune licence

## 👥 Auteurs

- Bright Ogbeiwi - [brightogbeiwi@gmail.com]

## 🏆 NASA Space Apps Challenge 2025

Ce projet a été développé dans le cadre du NASA Space Apps Challenge 2025.

**Challenge:** Create Your Own Challenge


**Équipe:** Explorer_J1K2R1

## 📞 Contact

Pour toute question, contactez [brightogbeiwi@gmail.com]