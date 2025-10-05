#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calcul de surface terrestre à partir des bandes NDVI
Version adaptée pour le pipeline automatique
"""

import os, sys, warnings
from pathlib import Path

# Patch PROJ
os.environ.setdefault("PROJ_DATA", os.path.join(sys.prefix, "share", "proj"))
try:
    from pyproj import datadir
    datadir.set_data_dir(os.environ["PROJ_DATA"])
except Exception:
    pass
warnings.filterwarnings("ignore", category=UserWarning, module="pyproj")

import numpy as np
import geopandas as gpd
from shapely.geometry import shape

import rasterio
from rasterio.features import shapes, rasterize
from rasterio.enums import Resampling
from rasterio.crs import CRS as RioCRS

from skimage.filters import threshold_otsu
from skimage.morphology import binary_opening, binary_closing, disk
from skimage.morphology import remove_small_objects, remove_small_holes
from skimage.measure import label
from scipy.ndimage import median_filter


# Configuration par défaut
DEFAULT_CONFIG = {
    'threshold_mode': 'fixed',
    'threshold_value': 0.05,
    'median_size': 5,
    'morph_radius': 2,
    'min_object_pixels': 150,
    'min_hole_pixels': 150,
    'mean_min': 0.02,
    'p90_min': 0.05,
    'FAST_MEAN_ONLY': True,
    'min_area_m2': 3000,
    'TARGET_EPSG': 32198,
    'ADD_TOTAL_FIELD': True,
    'TOTAL_FIELD_NAME': 'TOT_KM2',
    'TOTAL_DECIMALS': 4,
}


def read_band(path):
    """Lit une bande raster"""
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        tr, crs = src.transform, src.crs
        w, h = src.width, src.height
        nod = src.nodata
        if nod is not None:
            arr = np.where(arr == nod, np.nan, arr)
        arr[~np.isfinite(arr)] = np.nan
        return arr, tr, crs, w, h


def reproject_match(src_path, dst_transform, dst_crs, dst_w, dst_h, resampling):
    """Reprojette une bande pour correspondre à une autre"""
    with rasterio.open(src_path) as src:
        dst = np.empty((dst_h, dst_w), dtype="float32")
        rasterio.warp.reproject(
            source=src.read(1).astype("float32"),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=resampling
        )
        return dst


def compute_ndvi(nir, red):
    """Calcule le NDVI"""
    num = nir - red
    den = nir + red
    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi = np.where(den != 0, num/den, np.nan)
    return ndvi.astype("float32")


def make_binary_from_ndvi(ndvi, config):
    """Crée un masque binaire à partir du NDVI"""
    # Lissage
    if config['median_size'] and config['median_size'] > 1:
        ndvi = median_filter(ndvi, size=config['median_size'])
    
    valid = np.isfinite(ndvi)
    
    # Seuil NDVI
    if config['threshold_mode'].lower() == "otsu":
        thr = threshold_otsu(ndvi[valid]) if valid.any() else 0.2
    else:
        thr = float(config['threshold_value'])
    
    mask = np.zeros_like(ndvi, dtype=bool)
    mask[valid] = ndvi[valid] >= thr
    
    # Morphologie
    se = disk(config['morph_radius']) if config['morph_radius'] > 0 else None
    if se is not None:
        mask = binary_opening(mask)
        mask = binary_closing(mask, se)
    
    # Nettoyage
    if config['min_object_pixels'] > 0:
        mask = remove_small_objects(mask, min_size=config['min_object_pixels'])
    if config['min_hole_pixels'] > 0:
        mask = remove_small_holes(mask, area_threshold=config['min_hole_pixels'])
    
    return mask.astype(np.uint8), thr


def fast_label_filter_by_ndvi(mask_u8, ndvi, mean_min=0.02, p90_min=0.05, use_p90=False):
    """Filtre les composantes par statistiques NDVI"""
    if mask_u8.max() == 0:
        return mask_u8, 0, 0
    
    lbl = label(mask_u8.astype(bool), connectivity=1)
    nlab = int(lbl.max())
    valid = np.isfinite(ndvi)
    lbl_valid = lbl.copy()
    lbl_valid[~valid] = 0
    
    # Comptages
    counts = np.bincount(lbl_valid.ravel()).astype(np.int64)
    vals = np.zeros_like(lbl_valid, dtype=np.float32)
    vals[valid] = ndvi[valid]
    sums = np.bincount(lbl_valid.ravel(), weights=vals.ravel())
    
    # Mean NDVI
    with np.errstate(invalid='ignore', divide='ignore'):
        means = sums / np.maximum(counts, 1)
    
    keep = np.ones(nlab + 1, dtype=bool)
    keep &= (means >= mean_min)
    
    dropped_p90 = 0
    if use_p90:
        cand_labels = np.nonzero(keep[1:])[0] + 1
        for lab in cand_labels:
            idx = (lbl_valid == lab)
            arr = ndvi[idx]
            arr = arr[np.isfinite(arr)]
            if arr.size == 0:
                keep[lab] = False
                dropped_p90 += 1
                continue
            k = int(0.9 * (arr.size - 1))
            if k < 0: k = 0
            part = np.partition(arr, k)
            p90 = float(part[k])
            if p90 < p90_min:
                keep[lab] = False
                dropped_p90 += 1
    
    kept_labels = np.nonzero(keep[1:])[0] + 1
    final_mask = np.isin(lbl, kept_labels).astype("uint8")
    
    dropped_mean = int(nlab - len(kept_labels))
    return final_mask, dropped_mean, dropped_p90


def polygonize(binary_arr, transform, crs):
    """Vectorise le raster en polygones"""
    geoms = [shape(geom) for geom, val in shapes(
        binary_arr.astype("uint8"),
        mask=(binary_arr == 1),
        transform=transform
    ) if val == 1]
    
    if not geoms:
        return gpd.GeoDataFrame(columns=["area_m2","area_km2"], geometry=[], crs=crs)
    
    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)
    return gdf


def to_metric_for_area(gdf, target_epsg=32198):
    """Reprojette en CRS métrique pour calcul d'aire"""
    try:
        return gdf.to_crs(epsg=target_epsg)
    except Exception as e:
        print(f"⚠️ Reprojection EPSG:{target_epsg} impossible ({e}). Fallback…")
        src_crs = gdf.crs
        try:
            if src_crs and RioCRS.from_string(str(src_crs)).is_projected:
                print("➡️ CRS source déjà projeté → calcul direct (mètres).")
                return gdf.copy()
        except Exception:
            pass
        print("➡️ Passage en EPSG:32620 (UTM Zone 20N).")
        return gdf.to_crs(epsg=32620)


def process_ndvi(band_red, band_nir, output_dir, output_name, config=None):
    """
    Fonction principale de traitement NDVI → Shapefile
    
    Args:
        band_red: Chemin vers la bande rouge (B04)
        band_nir: Chemin vers la bande NIR (B08)
        output_dir: Dossier de sortie
        output_name: Nom du fichier shapefile de sortie
        config: Configuration (utilise DEFAULT_CONFIG si None)
    
    Returns:
        Path vers le shapefile créé
    """
    if config is None:
        config = DEFAULT_CONFIG.copy()
    
    print("\n" + "="*80)
    print("CALCUL DE SURFACE TERRESTRE (NDVI → SHAPEFILE)")
    print("="*80)
    
    # Convertir en Path
    band_red = Path(band_red)
    band_nir = Path(band_nir)
    output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 Bandes d'entrée:")
    print(f"   RED: {band_red.name}")
    print(f"   NIR: {band_nir.name}")
    
    # Charger les bandes
    print(f"\n📊 Chargement des données...")
    red, tr, crs, w, h = read_band(band_red)
    nir = reproject_match(band_nir, tr, crs, w, h, Resampling.bilinear)
    
    # Calculer NDVI
    print(f"   🔧 Calcul NDVI...")
    ndvi = compute_ndvi(nir, red)
    
    # Binarisation
    print(f"\n🔧 Binarisation...")
    mask_u8, thr = make_binary_from_ndvi(ndvi, config)
    print(f"   Seuil NDVI: {thr:.3f} ({config['threshold_mode']})")
    
    if mask_u8.max() == 0:
        raise RuntimeError("Aucun pixel sélectionné. Ajustez les paramètres.")
    
    # Filtrage anti-eau
    print(f"\n🌊 Filtrage anti-eau (raster)...")
    final_mask, dropped_mean, dropped_p90 = fast_label_filter_by_ndvi(
        mask_u8,
        ndvi,
        mean_min=config['mean_min'],
        p90_min=config['p90_min'],
        use_p90=(not config['FAST_MEAN_ONLY'])
    )
    
    if dropped_mean:
        print(f"   🚫 Composantes supprimées (mean NDVI): {dropped_mean}")
    if not config['FAST_MEAN_ONLY'] and dropped_p90:
        print(f"   🚫 Composantes supprimées (p90 NDVI): {dropped_p90}")
    
    if final_mask.max() == 0:
        raise RuntimeError("Tous les objets filtrés. Ajustez les paramètres.")
    
    # Vectorisation
    print(f"\n📐 Vectorisation...")
    gdf = polygonize(final_mask, tr, crs)
    
    if gdf.empty:
        raise RuntimeError("Vectorisation vide.")
    
    # Calcul des aires
    print(f"\n📏 Calcul des aires...")
    gdf_m = to_metric_for_area(gdf, config['TARGET_EPSG'])
    gdf_m["area_m2"] = gdf_m.geometry.area
    gdf_m = gdf_m[gdf_m["area_m2"] >= config['min_area_m2']].copy()
    gdf_m["area_km2"] = (gdf_m["area_m2"] / 1e6)
    
    # Champ total
    if config.get('ADD_TOTAL_FIELD', True) and not gdf_m.empty:
        total_km2 = float(gdf_m["area_km2"].sum())
        total_km2 = round(total_km2, int(config.get('TOTAL_DECIMALS', 4)))
        fld = str(config.get('TOTAL_FIELD_NAME', 'TOT_KM2'))[:10]
        gdf_m[fld] = total_km2
    
    # Arrondis
    gdf_m["area_km2"] = gdf_m["area_km2"].round(int(config.get('TOTAL_DECIMALS', 4)))
    
    # Retour CRS source
    gdf_out = gdf_m.to_crs(crs)
    
    # Export
    out_path = output_dir / output_name
    gdf_out.to_file(out_path)
    
    print(f"\n✅ Shapefile créé: {out_path}")
    print(f"🌿 Surface totale: {gdf_m['area_km2'].sum():.{config.get('TOTAL_DECIMALS',4)}f} km²")
    
    return out_path


if __name__ == "__main__":
    # Test avec arguments en ligne de commande
    if len(sys.argv) < 3:
        print("Usage: python code_de_surface.py <BAND_RED> <BAND_NIR> [OUTPUT_DIR] [OUTPUT_NAME]")
        sys.exit(1)
    
    band_red = sys.argv[1]
    band_nir = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output/shapefiles"
    output_name = sys.argv[4] if len(sys.argv) > 4 else "surface.shp"
    
    try:
        shapefile = process_ndvi(band_red, band_nir, output_dir, output_name)
        print(f"\n🎉 Succès!")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)