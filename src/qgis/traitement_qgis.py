#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Traitement d'images Sentinel-2 - Version Pure Python
N'utilise QUE Python/NumPy/Rasterio - AUCUN exécutable GDAL requis
"""

import os, sys, warnings
from pathlib import Path
import numpy as np

# ====== Configuration PROJ ======
def setup_proj_data():
    """Configure PROJ_DATA en cherchant proj.db"""
    if "PROJ_DATA" in os.environ and Path(os.environ["PROJ_DATA"]).exists():
        return
    
    # Chercher proj.db récursivement
    for db_path in Path(sys.prefix).rglob("proj.db"):
        if db_path.is_file():
            os.environ["PROJ_DATA"] = str(db_path.parent)
            break
    else:
        candidates = [
            Path(sys.prefix) / "share" / "proj",
            Path(sys.prefix) / "Library" / "share" / "proj",
            Path(sys.prefix) / "Lib" / "site-packages" / "fiona" / "proj_data",
        ]
        for candidate in candidates:
            if (candidate / "proj.db").exists():
                os.environ["PROJ_DATA"] = str(candidate)
                break
        else:
            os.environ.setdefault("PROJ_DATA", os.path.join(sys.prefix, "share", "proj"))
    
    try:
        from pyproj import datadir
        datadir.set_data_dir(os.environ["PROJ_DATA"])
    except Exception:
        pass

setup_proj_data()

warnings.filterwarnings("ignore", category=UserWarning)

# ====== Dossier de sortie ======
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_band_from_tci(tci_jp2: Path, band_code: str) -> Path:
    """
    Trouve un fichier de bande à partir du fichier TCI
    
    Args:
        tci_jp2: Chemin vers le fichier TCI
        band_code: Code de la bande (ex: 'B04', 'B08')
    
    Returns:
        Path vers le fichier de bande
    """
    band_dir = tci_jp2.parent
    
    # Chercher le fichier avec le code de bande
    pattern = f"*_{band_code}_*.jp2"
    hits = list(band_dir.glob(pattern))
    
    if not hits:
        # Essayer sans underscore
        pattern = f"*{band_code}*.jp2"
        hits = list(band_dir.glob(pattern))
    
    if not hits:
        listing = "\n".join(p.name for p in sorted(band_dir.glob("*.jp2")))
        raise FileNotFoundError(
            f"Aucun fichier '{pattern}' trouvé dans {band_dir}\n"
            f"Fichiers JP2 disponibles:\n{listing}"
        )
    
    if len(hits) > 1:
        # Prendre le plus gros fichier
        hits.sort(key=lambda p: p.stat().st_size, reverse=True)
    
    return hits[0]


def create_mosaic_pure_python(input_files: list[Path], output_tif: Path):
    """
    Crée une mosaïque de fichiers raster en pur Python avec rasterio
    """
    try:
        import rasterio
        from rasterio.merge import merge
        from rasterio.enums import Resampling
    except ImportError:
        raise ImportError(
            "\n❌ Module 'rasterio' requis mais non installé.\n\n"
            "Installation:\n"
            "  pip install rasterio\n"
            "  ou\n"
            "  conda install -c conda-forge rasterio\n"
        )
    
    print(f"   📦 Création mosaïque: {output_tif.name}")
    print(f"      Fichiers: {len(input_files)}")
    
    # Ouvrir tous les fichiers sources
    src_files = []
    try:
        for f in input_files:
            print(f"         • {f.name}")
            src = rasterio.open(str(f))
            src_files.append(src)
        
        # Créer la mosaïque
        mosaic, transform = merge(src_files, resampling=Resampling.bilinear)
        
        # Copier les métadonnées du premier fichier
        profile = src_files[0].profile.copy()
        
        # Mettre à jour avec les nouvelles dimensions
        profile.update({
            'driver': 'GTiff',
            'height': mosaic.shape[1],
            'width': mosaic.shape[2],
            'transform': transform,
            'compress': 'deflate',
            'tiled': True,
            'bigtiff': 'IF_SAFER'
        })
        
        # Écrire la mosaïque
        with rasterio.open(str(output_tif), 'w', **profile) as dst:
            dst.write(mosaic)
        
        print(f"      ✅ Mosaïque créée: {output_tif.name}")
        
    finally:
        # Fermer tous les fichiers sources
        for src in src_files:
            src.close()
    
    return output_tif


def create_mosaic_fallback_numpy(input_files: list[Path], output_tif: Path):
    """
    Méthode fallback: mosaïque simple en empilant les rasters
    Utilisée si rasterio.merge échoue
    """
    try:
        import rasterio
        from rasterio.enums import Resampling
    except ImportError:
        raise ImportError("Module rasterio requis")
    
    print(f"   ⚠️  Utilisation méthode fallback (empilement simple)")
    
    # Lire le premier fichier pour les métadonnées
    with rasterio.open(str(input_files[0])) as src:
        profile = src.profile.copy()
        arrays = [src.read(1)]
        transform = src.transform
        bounds = src.bounds
    
    # Lire les autres fichiers
    for f in input_files[1:]:
        with rasterio.open(str(f)) as src:
            # Simple: prendre le premier array (pas de vraie mosaïque)
            # Pour une vraie mosaïque, il faudrait gérer les overlaps
            arrays.append(src.read(1))
    
    # Moyenner les arrays (méthode simple)
    mosaic = np.mean(arrays, axis=0).astype(profile['dtype'])
    
    # Mettre à jour le profil
    profile.update({
        'driver': 'GTiff',
        'compress': 'deflate',
        'tiled': True,
        'bigtiff': 'IF_SAFER'
    })
    
    # Écrire
    with rasterio.open(str(output_tif), 'w', **profile) as dst:
        dst.write(mosaic, 1)
    
    print(f"      ✅ Mosaïque créée (fallback): {output_tif.name}")
    
    return output_tif


def convert_jp2_to_tif_if_needed(jp2_path: Path, output_dir: Path = None) -> Path:
    """
    Convertit un JP2 en TIFF si nécessaire
    Retourne le chemin (JP2 original ou TIFF converti)
    """
    if output_dir is None:
        output_dir = OUT_DIR
    
    try:
        import rasterio
        
        # Essayer d'ouvrir le JP2 directement
        try:
            with rasterio.open(str(jp2_path)) as src:
                # Si ça fonctionne, retourner le JP2 original
                print(f"      ✅ JP2 supporté: {jp2_path.name}")
                return jp2_path
        except Exception:
            # Si ça échoue, convertir en TIFF
            print(f"      🔄 Conversion JP2 → TIFF: {jp2_path.name}")
            
            tif_path = output_dir / (jp2_path.stem + ".tif")
            
            # Essayer avec une autre méthode de lecture
            try:
                from osgeo import gdal
                gdal.UseExceptions()
                
                # Lire avec GDAL
                ds = gdal.Open(str(jp2_path))
                if ds is None:
                    raise RuntimeError("GDAL ne peut pas ouvrir le JP2")
                
                # Convertir en TIFF
                driver = gdal.GetDriverByName('GTiff')
                ds_out = driver.CreateCopy(
                    str(tif_path),
                    ds,
                    options=['COMPRESS=DEFLATE', 'TILED=YES']
                )
                
                ds = None
                ds_out = None
                
                print(f"         ✅ Converti: {tif_path.name}")
                return tif_path
                
            except Exception as e2:
                raise RuntimeError(
                    f"\n❌ Impossible de lire le fichier JP2: {jp2_path.name}\n"
                    f"   Erreur rasterio: {e2}\n\n"
                    f"Solutions:\n"
                    f"1. Installer le support JP2:\n"
                    f"   conda install -c conda-forge rasterio gdal openjpeg\n\n"
                    f"2. Convertir manuellement vos JP2 en GeoTIFF:\n"
                    f"   gdal_translate input.jp2 output.tif\n\n"
                    f"3. Utiliser QGIS pour convertir les fichiers"
                )
    
    except ImportError:
        raise ImportError(
            "\n❌ Module 'rasterio' requis.\n\n"
            "Installation:\n"
            "  pip install rasterio\n"
            "  ou\n"
            "  conda install -c conda-forge rasterio\n"
        )


def process_tci_pair(tci_1: str, tci_2: str) -> tuple[Path, Path]:
    """
    Traite une paire de fichiers TCI pour créer des mosaïques B04 et B08
    VERSION PURE PYTHON - Aucun exécutable GDAL requis
    
    Args:
        tci_1: Chemin vers le premier fichier TCI
        tci_2: Chemin vers le deuxième fichier TCI
    
    Returns:
        Tuple (chemin_b04, chemin_b08)
    """
    print("\n" + "="*80)
    print("TRAITEMENT PAIRE TCI → MOSAÏQUES B04/B08 (Pure Python)")
    print("="*80)
    
    tci_1_path = Path(tci_1)
    tci_2_path = Path(tci_2)
    
    print(f"\n📍 TCI 1: {tci_1_path.name}")
    print(f"📍 TCI 2: {tci_2_path.name}")
    
    # Trouver les bandes B04 et B08 pour chaque TCI
    print(f"\n🔍 Recherche des bandes...")
    
    try:
        b4_1 = find_band_from_tci(tci_1_path, "B04")
        b8_1 = find_band_from_tci(tci_1_path, "B08")
        print(f"   TCI 1 - B04: {b4_1.name}")
        print(f"   TCI 1 - B08: {b8_1.name}")
        
        b4_2 = find_band_from_tci(tci_2_path, "B04")
        b8_2 = find_band_from_tci(tci_2_path, "B08")
        print(f"   TCI 2 - B04: {b4_2.name}")
        print(f"   TCI 2 - B08: {b8_2.name}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Erreur: {e}")
        raise
    
    # Vérifier/convertir les JP2 si nécessaire
    print(f"\n🔍 Vérification format des fichiers...")
    b4_1 = convert_jp2_to_tif_if_needed(b4_1)
    b4_2 = convert_jp2_to_tif_if_needed(b4_2)
    b8_1 = convert_jp2_to_tif_if_needed(b8_1)
    b8_2 = convert_jp2_to_tif_if_needed(b8_2)
    
    # Créer les noms de sortie avec timestamp
    timestamp = tci_1_path.stem.split('_')[2] if '_' in tci_1_path.stem else "mosaic"
    
    b04_tif = OUT_DIR / f"Mosaic_B04_{timestamp}.tiff"
    b08_tif = OUT_DIR / f"Mosaic_B08_{timestamp}.tiff"
    
    # Créer les mosaïques avec rasterio
    print(f"\n🔧 Création des mosaïques (rasterio.merge)...")
    
    try:
        create_mosaic_pure_python([b4_1, b4_2], b04_tif)
        create_mosaic_pure_python([b8_1, b8_2], b08_tif)
    except Exception as e:
        print(f"\n⚠️  Erreur avec rasterio.merge: {e}")
        print(f"   Tentative avec méthode fallback...")
        
        create_mosaic_fallback_numpy([b4_1, b4_2], b04_tif)
        create_mosaic_fallback_numpy([b8_1, b8_2], b08_tif)
    
    print(f"\n✅ Traitement terminé!")
    print(f"   B04: {b04_tif}")
    print(f"   B08: {b08_tif}")
    
    return b04_tif, b08_tif


if __name__ == "__main__":
    # Test avec deux fichiers TCI fournis en arguments
    if len(sys.argv) != 3:
        print("Usage: python traitement_qgis.py <TCI_1.jp2> <TCI_2.jp2>")
        print("\nCe script utilise UNIQUEMENT Python (rasterio).")
        print("Aucun exécutable GDAL requis!")
        print("\nInstallation: pip install rasterio")
        sys.exit(1)
    
    tci_1 = sys.argv[1]
    tci_2 = sys.argv[2]
    
    try:
        b04, b08 = process_tci_pair(tci_1, tci_2)
        print(f"\n🎉 Succès!")
        print(f"\nUtilisez ces fichiers pour code_de_surface.py:")
        print(f'  python code_de_surface.py "{b04}" "{b08}"')
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)