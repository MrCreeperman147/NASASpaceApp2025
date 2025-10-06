#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Code pour affichage réel des rasters TIFF sur la carte Folium
"""

# ============================================================================
# NOUVEAU FICHIER: src/tiff_to_tiles.py
# ============================================================================

"""
Convertit les fichiers TIFF NDVI en tuiles PNG pour affichage web
"""

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pathlib import Path
import json
import shutil
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def convert_tiff_to_png_with_palette(tiff_path, output_png, bounds_json=None):
    """
    Convertit un TIFF NDVI en PNG avec palette de couleurs
    
    Args:
        tiff_path: Chemin vers le TIFF NDVI
        output_png: Chemin de sortie pour le PNG
        bounds_json: Chemin pour sauvegarder les bounds (optionnel)
    
    Returns:
        Dict avec bounds et infos
    """
    with rasterio.open(tiff_path) as src:
        # Lire les données
        ndvi = src.read(1)
        
        # Récupérer les métadonnées
        bounds = src.bounds
        crs = src.crs
        
        # Reprojeter en Web Mercator (EPSG:3857) si nécessaire
        if crs != 'EPSG:3857':
            # Calculer la transformation
            transform, width, height = calculate_default_transform(
                crs, 'EPSG:3857', src.width, src.height, *bounds
            )
            
            # Créer un nouveau array
            ndvi_reproj = np.empty((height, width), dtype=np.float32)
            
            # Reprojeter
            reproject(
                source=ndvi,
                destination=ndvi_reproj,
                src_transform=src.transform,
                src_crs=crs,
                dst_transform=transform,
                dst_crs='EPSG:3857',
                resampling=Resampling.bilinear
            )
            
            ndvi = ndvi_reproj
            
            # Recalculer les bounds en Web Mercator
            from rasterio.warp import transform_bounds
            bounds = transform_bounds(crs, 'EPSG:3857', *bounds)
        
        # Créer une image RGB avec palette NDVI
        height, width = ndvi.shape
        rgb = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA
        
        # Masque des valeurs valides
        valid = np.isfinite(ndvi) & (ndvi != -9999)
        
        # Appliquer la palette de couleurs NDVI
        # Eau (< 0): Bleu
        mask_water = valid & (ndvi < 0)
        rgb[mask_water] = [0, 0, 255, 180]  # Bleu semi-transparent
        
        # Sol nu (0-0.2): Brun
        mask_bare = valid & (ndvi >= 0) & (ndvi < 0.2)
        rgb[mask_bare] = [165, 42, 42, 180]  # Brun
        
        # Végétation faible (0.2-0.4): Jaune-vert
        mask_low = valid & (ndvi >= 0.2) & (ndvi < 0.4)
        rgb[mask_low] = [255, 255, 0, 200]  # Jaune
        
        # Végétation moyenne (0.4-0.6): Vert clair
        mask_med = valid & (ndvi >= 0.4) & (ndvi < 0.6)
        rgb[mask_med] = [144, 238, 144, 220]  # Vert clair
        
        # Végétation dense (0.6+): Vert foncé
        mask_high = valid & (ndvi >= 0.6)
        rgb[mask_high] = [0, 128, 0, 240]  # Vert foncé
        
        # Sauvegarder comme PNG
        img = Image.fromarray(rgb, 'RGBA')
        img.save(output_png)
        
        # Sauvegarder les bounds si demandé
        bounds_dict = {
            'south': bounds.bottom,
            'west': bounds.left,
            'north': bounds.top,
            'east': bounds.right,
            'crs': 'EPSG:3857'
        }
        
        if bounds_json:
            with open(bounds_json, 'w') as f:
                json.dump(bounds_dict, f, indent=2)
        
        return bounds_dict


def prepare_tiffs_for_web(processed_dir='data/processed', output_dir='static/tiffs'):
    """
    Prépare tous les TIFF NDVI pour l'affichage web
    
    Args:
        processed_dir: Dossier contenant les TIFF organisés par date
        output_dir: Dossier de sortie pour les PNG
    
    Returns:
        Dict avec les infos de tous les TIFF convertis
    """
    processed_path = Path(processed_dir)
    output_path = Path(output_dir)
    
    # Créer le dossier de sortie
    output_path.mkdir(parents=True, exist_ok=True)
    
    tiff_info = {}
    
    # Scanner les dossiers de dates
    date_folders = sorted([d for d in processed_path.iterdir() 
                          if d.is_dir() and len(d.name) == 10])
    
    print(f"\n🔄 Conversion des TIFF en PNG pour le web...")
    print(f"   Dossiers trouvés: {len(date_folders)}")
    
    for date_folder in date_folders:
        date_str = date_folder.name
        
        # Chercher le fichier NDVI
        ndvi_files = list(date_folder.glob('NDVI_*.tif'))
        
        if not ndvi_files:
            continue
        
        tiff_path = ndvi_files[0]
        png_path = output_path / f"{date_str}.png"
        bounds_path = output_path / f"{date_str}_bounds.json"
        
        print(f"   📊 {date_str}...", end='', flush=True)
        
        try:
            # Convertir en PNG
            bounds = convert_tiff_to_png_with_palette(
                tiff_path, 
                png_path, 
                bounds_path
            )
            
            tiff_info[date_str] = {
                'png_path': str(png_path.relative_to(output_path.parent)),
                'bounds': bounds,
                'original_tiff': str(tiff_path)
            }
            
            print(f" ✅")
            
        except Exception as e:
            print(f" ❌ Erreur: {e}")
            continue
    
    # Sauvegarder l'index global
    index_path = output_path / 'index.json'
    with open(index_path, 'w') as f:
        json.dump(tiff_info, f, indent=2)
    
    print(f"\n✅ Conversion terminée: {len(tiff_info)} TIFF convertis")
    print(f"   📁 Dossier: {output_path}")
    
    return tiff_info





