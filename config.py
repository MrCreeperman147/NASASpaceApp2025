"""
Configuration globale du projet NASASpaceApp2025
"""

from pathlib import Path

# Chemins du projet
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# Créer les dossiers s'ils n'existent pas
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Paramètres de traitement d'images
IMAGE_SETTINGS = {
    'default_size': (512, 512),
    'color_mode': 'RGB',
    'interpolation': 'bilinear',
}

# Paramètres GDAL
GDAL_SETTINGS = {
    'cache_max': 512,  # Mo
    'num_threads': 'ALL_CPUS',
}

# Paramètres Dask pour calcul parallèle
DASK_SETTINGS = {
    'num_workers': 4,
    'threads_per_worker': 2,
    'memory_limit': '4GB',
}

# Formats de fichiers supportés
SUPPORTED_IMAGE_FORMATS = ['.tif', '.tiff', '.png', '.jpg', '.jpeg']
SUPPORTED_VECTOR_FORMATS = ['.shp', '.geojson', '.gpkg']

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = PROJECT_ROOT / 'app.log'

# API Keys (à ne pas committer dans Git!)
# Utilisez plutôt des variables d'environnement
NASA_API_KEY = None  # os.getenv('NASA_API_KEY')

def print_config():
    """Affiche la configuration actuelle"""
    print("=" * 70)
    print("CONFIGURATION DU PROJET")
    print("=" * 70)
    print(f"Racine du projet : {PROJECT_ROOT}")
    print(f"Dossier données  : {DATA_DIR}")
    print(f"Données brutes   : {RAW_DATA_DIR}")
    print(f"Données traitées : {PROCESSED_DATA_DIR}")
    print(f"Résultats        : {OUTPUT_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    print_config()