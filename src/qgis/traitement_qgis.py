#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, subprocess, shutil
from pathlib import Path

# ====== Dossiers R10m localisés via tes TCI ======
TCI_TNT = Path("/Users/mstairi/Desktop/Nasa_Space_Apps/S2A_MSIL2A_20250620T150731_N0511_R125_T20TNT_20250620T194418.SAFE/GRANULE/L2A_T20TNT_A052203_20250620T150728/IMG_DATA/R10m/T20TNT_20250620T150731_TCI_10m.jp2")
TCI_TPT = Path("/Users/mstairi/Desktop/Nasa_Space_Apps/DATA/S2A_MSIL2A_20250620T150731_N0511_R125_T20TPT_20250620T194418.SAFE/GRANULE/L2A_T20TPT_A052203_20250620T150728/IMG_DATA/R10m/T20TPT_20250620T150731_TCI_10m.jp2")

# ====== Sorties EXACTES attendues par ton autre script ======
OUT_DIR = Path("/Users/mstairi/Desktop/Nasa_Space_Apps/DATA"); OUT_DIR.mkdir(parents=True, exist_ok=True)
B04_VRT = OUT_DIR / "Mosaic_B04.vrt"
B08_VRT = OUT_DIR / "Mosaic_B08.vrt"
B04_TIF = OUT_DIR / "Mosaic_Magdalene_B04.tiff"  # CONFIG["BAND_RED"]
B08_TIF = OUT_DIR / "Mosaic_Magdalene_B08.tiff"  # CONFIG["BAND_NIR"]

# ====== Options GeoTIFF ======
GTIFF_CO = ["-co", "COMPRESS=DEFLATE", "-co", "TILED=YES", "-co", "BIGTIFF=IF_SAFER"]

# ====== Forcer GDAL à utiliser TON env conda ======
PREFIX = sys.prefix  # ex: /Users/mstairi/miniconda3/envs/nasa.Hack
os.environ["GDAL_DATA"] = str(Path(PREFIX) / "share" / "gdal")
os.environ["PROJ_DATA"] = str(Path(PREFIX) / "share" / "proj")

def detect_plugin_dir(prefix: str) -> Path | None:
    base = Path(prefix) / "lib" / "gdalplugins"
    cands = [base]
    if base.exists():
        cands += [d for d in base.iterdir() if d.is_dir()]  # ex: gdalplugins/3.9
    cands.append(Path(prefix) / "lib")
    for d in cands:
        for ext in (".dylib", ".so"):
            if list(d.glob(f"gdal_JP2OpenJPEG*{ext}")):
                return d
    return None

PLUGIN_DIR = detect_plugin_dir(PREFIX)
if PLUGIN_DIR:
    os.environ["GDAL_DRIVER_PATH"] = str(PLUGIN_DIR)

def exe(name: str) -> str:
    p = Path(PREFIX) / "bin" / name
    if p.exists(): return str(p)
    alt = shutil.which(name)
    if alt: return alt
    for c in ["/Applications/QGIS.app/Contents/MacOS/bin/"+name,
              "/opt/homebrew/bin/"+name, "/usr/local/bin/"+name]:
        if Path(c).exists(): return c
    raise FileNotFoundError(f"{name} introuvable")

def must_have_jp2():
    if not PLUGIN_DIR:
        raise RuntimeError(
            "Plugin JP2OpenJPEG introuvable dans cet env.\n"
            "Installe-le : conda install -c conda-forge libgdal-jp2openjpeg openjpeg"
        )

def find_exact_R10m_band(tci_jp2: Path, code: str) -> Path:
    """Cherche STRICTEMENT *_{code}_10m.jp2 dans le dossier R10m (non récursif)."""
    r10m = tci_jp2.parent
    if not r10m.is_dir(): raise FileNotFoundError(f"Dossier R10m introuvable : {r10m}")
    hits = sorted(r10m.glob(f"*_{code}_10m.jp2"))
    if not hits:
        listing = "\n".join(p.name for p in sorted(r10m.glob("*.jp2")))
        raise FileNotFoundError(f"Aucun '*_{code}_10m.jp2' dans {r10m}\nJP2 visibles:\n{listing}")
    if len(hits) > 1: hits.sort(key=lambda p: p.stat().st_size, reverse=True)
    return hits[0]

def build_vrt(inputs: list[Path], out_vrt: Path):
    must_have_jp2()
    cmd = [exe("gdalbuildvrt"), str(out_vrt), *map(str, inputs)]
    print("▶", " ".join(cmd)); subprocess.run(cmd, check=True, env=os.environ.copy())
    print(f"✅ VRT → {out_vrt.name}")

def vrt_to_gtiff(in_vrt: Path, out_tif: Path):
    cmd = [exe("gdal_translate"), str(in_vrt), str(out_tif), *GTIFF_CO, "-of", "GTiff"]
    print("▶", " ".join(cmd)); subprocess.run(cmd, check=True, env=os.environ.copy())
    print(f"✅ GTiff → {out_tif.name}")

def main():
    print(">>> PYTHON:", sys.executable)
    print("GDAL_DRIVER_PATH:", os.environ.get("GDAL_DRIVER_PATH"))

    # 1) Repérer STRICTEMENT B04 & B08 dans chaque R10m
    b4_tnt = find_exact_R10m_band(TCI_TNT, "B04")
    b8_tnt = find_exact_R10m_band(TCI_TNT, "B08")
    b4_tpt = find_exact_R10m_band(TCI_TPT, "B04")
    b8_tpt = find_exact_R10m_band(TCI_TPT, "B08")
    print("B04 TNT:", b4_tnt.name, "| B04 TPT:", b4_tpt.name)
    print("B08 TNT:", b8_tnt.name, "| B08 TPT:", b8_tpt.name)

    # 2) VRT mosaïques par bande (ordre indifférent)
    build_vrt([b4_tnt, b4_tpt], B04_VRT)
    build_vrt([b8_tnt, b8_tpt], B08_VRT)

    # 3) VRT -> GeoTIFF 1 bande avec les NOMS EXACTS attendus par ton autre code
    vrt_to_gtiff(B04_VRT, B04_TIF)  # => /.../Mosaic_Magdalene_B04.tiff
    vrt_to_gtiff(B08_VRT, B08_TIF)  # => /.../Mosaic_Magdalene_B08.tiff

    print("\n🚀 Prêt. Utilise ces chemins dans ton script NDVI/shapefile :")
    print(f'  "BAND_RED": "{B04_TIF}"')
    print(f'  "BAND_NIR": "{B08_TIF}"')

if __name__ == "__main__":
    main()