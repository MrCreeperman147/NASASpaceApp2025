"""
Vérification complète des librairies
"""

import sys

print("=" * 70)
print("VÉRIFICATION DES LIBRAIRIES")
print("=" * 70)
print(f"Python : {sys.version}")
print("=" * 70)

libraries = {
    'NumPy': 'numpy',
    'Pillow': 'PIL',
    'OpenCV': 'cv2',
    'scikit-image': 'skimage',
    'Xarray': 'xarray',
    'Dask': 'dask',
    'Tkinter': 'tkinter',  # Inclus avec Python, pas via pip
    'GDAL': 'osgeo.gdal',
    'Rasterio': 'rasterio',
}

installed = []
missing = []

for name, module in libraries.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'Inclus avec Python' if module == 'tkinter' else 'N/A')
        print(f"✓ {name:<20} {version}")
        installed.append(name)
    except ImportError:
        print(f"✗ {name:<20} NON INSTALLÉ")
        missing.append(name)

print("=" * 70)

if not missing:
    print("✅ Toutes les librairies sont installées !")
elif missing == ['Tkinter']:
    print("⚠️  Seul Tkinter manque (réinstaller Python avec tcl/tk)")
else:
    print(f"❌ Librairies manquantes : {', '.join(missing)}")
    if 'Tkinter' in missing:
        missing.remove('Tkinter')
    if missing:
        print(f"\nPour installer les librairies manquantes :")
        print(f"  pip install {' '.join(missing.lower())}")

print("=" * 70)