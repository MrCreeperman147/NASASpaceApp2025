#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, subprocess, shutil
from pathlib import Path

# ====== Configuration GDAL/PROJ ======
PREFIX = sys.prefix
os.environ.setdefault("GDAL_DATA", os.path.join(PREFIX, "share", "gdal"))
os.environ.setdefault("PROJ_DATA", os.path.join(PREFIX, "share", "proj"))

try:
    from pyproj import datadir
    datadir.set_data_dir(os.environ["PROJ_DATA"])
except Exception:
    pass

# ====== Dossier de sortie ======
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ====== Options GeoTIFF ======
GTIFF_CO = ["-co", "COMPRESS=DEFLATE", "-co", "TILED=YES", "-co", "BIGTIFF=IF_SAFER"]


def find_gdal_exe(name: str) -> str:
    """Trouve l'exécutable GDAL"""
    # D'abord dans l'environnement Python actuel
    p = Path(PREFIX) / "bin" / name
    if p.exists():
        return str(p)
    
    # Ensuite avec which
    alt = shutil.which(name)
    if alt:
        return alt
    
    # Chemins communs
    for c in [
        f"/Applications/QGIS.app/Contents/MacOS/bin/{name}",
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}"
    ]:
        if Path(c).exists():
            return c
    
    raise FileNotFoundError(f"{name} introuvable")


def detect_plugin_dir(prefix: str) -> Path | None:
    """Détecte le dossier des plugins GDAL"""
    base = Path(prefix) / "lib" / "gdalplugins"
    cands = [base]
    
    if base.exists():
        cands += [d for d in base.iterdir() if d.is_dir()]
    
    cands.append(Path(prefix) / "lib")
    
    for d in cands:
        for ext in (".dylib", ".so"):
            if list(d.glob(f"gdal_JP2OpenJPEG*{ext}")):
                return d
    
    return None


PLUGIN_DIR = detect_plugin_dir(PREFIX)
if PLUGIN_DIR:
    os.environ["GDAL_DRIVER_PATH"] = str(PLUGIN_DIR)


def must_have_jp2():
    """Vérifie que le plugin JP2 est disponible"""
    if not PLUGIN_DIR:
        raise RuntimeError(
            "Plugin JP2OpenJPEG introuvable.\n"
            "Installation: conda install -c conda-forge libgdal-jp2openjpeg openjpeg"
        )


def find_band_from_tci(tci_jp2: Path, band_code: str) -> Path:
    """
    Trouve un fichier de bande à partir du fichier TCI
    
    Args:
        tci_jp2: Chemin vers le fichier TCI
        band_code: Code de la bande (ex: 'B04', 'B08')
    
    Returns:
        Path vers le fichier de bande
    """
    # Le fichier de bande est dans le même dossier que le TCI
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


def build_vrt(inputs: list[Path], out_vrt: Path):
    """Construit un VRT (mosaïque virtuelle)"""
    must_have_jp2()
    
    cmd = [find_gdal_exe("gdalbuildvrt"), str(out_vrt), *map(str, inputs)]
    print(f"▶ {' '.join(cmd)}")
    
    subprocess.run(cmd, check=True, env=os.environ.copy())
    print(f"✅ VRT → {out_vrt.name}")


def vrt_to_gtiff(in_vrt: Path, out_tif: Path):
    """Convertit un VRT en GeoTIFF"""
    cmd = [find_gdal_exe("gdal_translate"), str(in_vrt), str(out_tif), *GTIFF_CO, "-of", "GTiff"]
    print(f"▶ {' '.join(cmd)}")
    
    subprocess.run(cmd, check=True, env=os.environ.copy())
    print(f"✅ GTiff → {out_tif.name}")


def process_tci_pair(tci_1: str, tci_2: str) -> tuple[Path, Path]:
    """
    Traite une paire de fichiers TCI pour créer des mosaïques B04 et B08
    
    Args:
        tci_1: Chemin vers le premier fichier TCI
        tci_2: Chemin vers le deuxième fichier TCI
    
    Returns:
        Tuple (chemin_b04, chemin_b08)
    """
    print("\n" + "="*80)
    print("TRAITEMENT PAIRE TCI → MOSAÏQUES B04/B08")
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
    
    # Créer les noms de sortie avec timestamp
    timestamp = tci_1_path.stem.split('_')[2] if '_' in tci_1_path.stem else "mosaic"
    
    b04_vrt = OUT_DIR / f"Mosaic_B04_{timestamp}.vrt"
    b08_vrt = OUT_DIR / f"Mosaic_B08_{timestamp}.vrt"
    b04_tif = OUT_DIR / f"Mosaic_B04_{timestamp}.tiff"
    b08_tif = OUT_DIR / f"Mosaic_B08_{timestamp}.tiff"
    
    # Créer les VRT
    print(f"\n🔧 Création des mosaïques VRT...")
    build_vrt([b4_1, b4_2], b04_vrt)
    build_vrt([b8_1, b8_2], b08_vrt)
    
    # Convertir en GeoTIFF
    print(f"\n🔧 Conversion en GeoTIFF...")
    vrt_to_gtiff(b04_vrt, b04_tif)
    vrt_to_gtiff(b08_vrt, b08_tif)
    
    print(f"\n✅ Traitement terminé!")
    print(f"   B04: {b04_tif}")
    print(f"   B08: {b08_tif}")
    
    return b04_tif, b08_tif


if __name__ == "__main__":
    # Test avec deux fichiers TCI fournis en arguments
    if len(sys.argv) != 3:
        print("Usage: python traitement_qgis.py <TCI_1.jp2> <TCI_2.jp2>")
        sys.exit(1)
    
    tci_1 = sys.argv[1]
    tci_2 = sys.argv[2]
    
    try:
        b04, b08 = process_tci_pair(tci_1, tci_2)
        print(f"\n🎉 Succès!")
        print(f"Utilisez ces fichiers pour code_de_surface.py:")
        print(f'  BAND_RED="{b04}"')
        print(f'  BAND_NIR="{b08}"')
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)