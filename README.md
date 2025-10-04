# NASASpaceApp2025

Projet pour le NASA Space Apps Challenge 2025 - Analyse et traitement de données géospatiales.

## 📋 Description

Ce projet utilise des technologies de traitement d'images et d'analyse géospatiale pour [décrire l'objectif de votre projet].

## 🛠️ Technologies utilisées

- **Python 3.12.10**
- **GDAL 3.11.1** - Traitement de données raster géospatiales
- **Rasterio 1.4.3** - Lecture/écriture de fichiers géospatiaux
- **Xarray** - Manipulation de données multidimensionnelles
- **NumPy** - Calculs numériques
- **OpenCV** - Vision par ordinateur et traitement d'images
- **scikit-image** - Algorithmes de traitement d'images
- **Pillow** - Manipulation d'images
- **Dask** - Calcul parallèle pour grandes données

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