# --- PATCH PROJ / pyproj (met-le tout en haut du fichier) --- 
import os, sys, warnings 
os.environ.setdefault("PROJ_DATA", os.path.join(sys.prefix, "share", "proj")) 
try: 
    from pyproj import datadir 
    datadir.set_data_dir(os.environ["PROJ_DATA"]) 
except Exception: 
    pass 
warnings.filterwarnings("ignore", category=UserWarning, module="pyproj") 
# ------------------------------------------------------------ 
 
import os 
import numpy as np 
import geopandas as gpd 
from shapely.geometry import shape 
 
import rasterio 
from rasterio.features import shapes, rasterize, geometry_mask 
from rasterio.enums import Resampling 
from rasterio.crs import CRS as RioCRS 
 
from skimage.filters import threshold_otsu 
from skimage.morphology import binary_opening, binary_closing, disk 
from skimage.morphology import remove_small_objects, remove_small_holes 
from skimage.measure import label  # labellisation rapide 
from scipy.ndimage import median_filter 
 
# ------------------ CONFIG (accents ok) ------------------ 
CONFIG = { 
    # Option A : NDVI déjà prêt (GeoTIFF) 
    "NDVI_PATH": None,  # ex: "/.../ndvi_2025.tif" 
 
    # Option B : calcul du NDVI à partir des bandes RED/NIR 
    "BAND_RED": "/Users/mstairi/Desktop/Nasa_Space_Apps/DATA/Mosaic_Magdalene_B04.tiff", 
    "BAND_NIR": "/Users/mstairi/Desktop/Nasa_Space_Apps/DATA/Mosaic_Magdalene_B08.tiff", 
 
    # AOI (facultatif) : polygone terre/îles ; None = toute l'image 
    "AOI_FILE": None,  # ex: "/Users/.../Contour_terre.gpkg" 
 
    # Binarisation NDVI (bas pour capter le sable) 
    "threshold_mode": "fixed",   # "fixed" ou "otsu" 
    "threshold_value": 0.05,     # baisse => plus de sable ; remonte si trop d'eau 
    "median_size": 5,            # 3 ou 5 
    "morph_radius": 2,           # 1=>3x3, 2=>5x5 
 
    # Nettoyage raster (pixels) 
    "min_object_pixels": 150,    # supprime petites composantes 
    "min_hole_pixels": 150,      # comble petits trous 
 
    # ⚡ Filtre anti-eau basé NDVI (raster → ultra rapide) 
    "FAST_MEAN_ONLY": True,      # True = mean NDVI uniquement (plus rapide) 
    "mean_min": 0.02,            # mean NDVI < 0.02 → eau probable 
    "p90_min": 0.05,             # utilisé seulement si FAST_MEAN_ONLY=False 
 
    # Aire (CRS métrique) + filtre vectoriel final 
    "min_area_m2": 3000,         # enlève petits polygones finaux 
    "TARGET_EPSG": 32198,        # MTM-8 / NAD83 (Îles-de-la-Madeleine) 
 
    # ➕ Champ "surface totale" dans la table attributaire (répété sur chaque entité) 
    "ADD_TOTAL_FIELD": True, 
    "TOTAL_FIELD_NAME": "TOT_KM2",  # ≤ 10 caractères (limite DBF) 
    "TOTAL_DECIMALS": 4, 
 
    # Sortie 
    "OUT_DIR": "/Users/mstairi/Desktop/Nasa_Space_Apps/test", 
    "OUT_SHP": "surface_denoised.shp", 
} 
# --------------------------------------------------------- 
 
os.makedirs(CONFIG["OUT_DIR"], exist_ok=True) 
 
# ------------------ I/O & NDVI ------------------ 
def read_band(path): 
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
    num = nir - red 
    den = nir + red 
    with np.errstate(divide='ignore', invalid='ignore'): 
        ndvi = np.where(den != 0, num/den, np.nan) 
    return ndvi.astype("float32") 
 
def load_or_make_ndvi_and_meta(): 
    if CONFIG["NDVI_PATH"]: 
        with rasterio.open(CONFIG["NDVI_PATH"]) as src: 
            ndvi = src.read(1).astype("float32") 
            tr, crs = src.transform, src.crs 
            ndvi[~np.isfinite(ndvi)] = np.nan 
        return ndvi, tr, crs, src.width, src.height 
    red, tr, crs, w, h = read_band(CONFIG["BAND_RED"]) 
    nir = reproject_match(CONFIG["BAND_NIR"], tr, crs, w, h, Resampling.bilinear) 
    ndvi = compute_ndvi(nir, red) 
    return ndvi, tr, crs, w, h 
 
# ------------------ Pipeline raster optimisé ------------------ 
def rasterize_aoi_if_any(aoi_file, tr, crs, shape_hw): 
    if not aoi_file: 
        return None 
    gdf = gpd.read_file(aoi_file) 
    if gdf.empty: 
        return None 
    gdf = gdf.to_crs(crs) 
    geom = gdf.dissolve().geometry.iloc[0] 
    aoi_r = rasterize( 
        [(geom, 1)], 
        out_shape=shape_hw, 
        transform=tr, 
        fill=0, 
        dtype="uint8" 
    ).astype(bool) 
    return aoi_r 
 
def make_binary_from_ndvi(ndvi): 
    # lissage (évite bruit) 
    if CONFIG["median_size"] and CONFIG["median_size"] > 1: 
        ndvi = median_filter(ndvi, size=CONFIG["median_size"]) 
    valid = np.isfinite(ndvi) 
 
    # seuil NDVI 
    if CONFIG["threshold_mode"].lower() == "otsu": 
        thr = threshold_otsu(ndvi[valid]) if valid.any() else 0.2 
    else: 
        thr = float(CONFIG["threshold_value"]) 
 
    mask = np.zeros_like(ndvi, dtype=bool) 
    mask[valid] = ndvi[valid] >= thr 
 
    # morpho légère 
    se = disk(CONFIG["morph_radius"]) if CONFIG["morph_radius"] > 0 else None 
    if se is not None: 
        mask = binary_opening(mask) 
        mask = binary_closing(mask, se) 
 
    # petit bruit / trous 
    if CONFIG["min_object_pixels"] > 0: 
        mask = remove_small_objects(mask, min_size=CONFIG["min_object_pixels"]) 
    if CONFIG["min_hole_pixels"] > 0: 
        mask = remove_small_holes(mask, area_threshold=CONFIG["min_hole_pixels"]) 
 
    return mask.astype(np.uint8), thr 
 
def fast_label_filter_by_ndvi(mask_u8, ndvi, mean_min=0.02, p90_min=0.05, use_p90=False): 
    """ 
    1) Label des composantes connexes sur le masque binaire. 
    2) Stats NDVI par label en raster (ultra rapide). 
       - mean NDVI : via np.bincount (poids) 
       - p90 NDVI : optionnel (boucle par label, plus lent) 
    3) Construit un nouveau masque gardant seulement les labels validés. 
    """ 
    if mask_u8.max() == 0: 
        return mask_u8, 0, 0 
 
    lbl = label(mask_u8.astype(bool), connectivity=1)  # int32 
    nlab = int(lbl.max()) 
    valid = np.isfinite(ndvi) 
    lbl_valid = lbl.copy() 
    lbl_valid[~valid] = 0 
 
    # Comptages par label 
    counts = np.bincount(lbl_valid.ravel()).astype(np.int64) 
    # Somme NDVI par label 
    vals = np.zeros_like(lbl_valid, dtype=np.float32) 
    vals[valid] = ndvi[valid] 
    sums = np.bincount(lbl_valid.ravel(), weights=vals.ravel()) 
 
    # mean NDVI par label 
    with np.errstate(invalid='ignore', divide='ignore'): 
        means = sums / np.maximum(counts, 1) 
 
    keep = np.ones(nlab + 1, dtype=bool)  # index 0 = fond 
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
 
# ------------------ Vectorisation + Aire ------------------ 
def polygonize(binary_arr, transform, crs): 
    geoms = [shape(geom) for geom, val in shapes( 
        binary_arr.astype("uint8"), 
        mask=(binary_arr == 1), 
        transform=transform 
    ) if val == 1] 
    if not geoms: 
        return gpd.GeoDataFrame(columns=["area_m2","area_km2"], geometry=[], crs=crs) 
    # Polygone par composante (pas de dissolve/explode pour aller vite) 
    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs) 
    return gdf 
 
def to_metric_for_area(gdf, target_epsg=32198): 
    try: 
        return gdf.to_crs(epsg=target_epsg) 
    except Exception as e: 
        print(f"⚠️ Reprojection EPSG:{target_epsg} impossible ({e}). Fallback…") 
        src_crs = gdf.crs 
        try: 
            if src_crs and RioCRS.from_string(str(src_crs)).is_projected: 
                print("➡️ CRS source déjà projeté → calcul des aires directement (mètres).") 
                return gdf.copy() 
        except Exception: 
            pass 
        print("➡️ Passage en EPSG:32620 (UTM Zone 20N) pour calculer les aires.") 
        return gdf.to_crs(epsg=32620) 
 
# ------------------ MAIN ------------------ 
def main(): 
    ndvi, tr, crs, w, h = load_or_make_ndvi_and_meta() 
 
    # AOI rasterisé (si fourni) → masque True/False à appliquer dès le début 
    aoi_r = rasterize_aoi_if_any(CONFIG["AOI_FILE"], tr, crs, (h, w)) 
 
    # 1) NDVI -> binaire (rapide) 
    mask_u8, thr = make_binary_from_ndvi(ndvi) 
    print(f"Seuil NDVI utilisé : {thr:.3f} ({CONFIG['threshold_mode']})") 
 
    # 1.b) Appliquer AOI dès maintenant pour réduire le volume 
    if aoi_r is not None: 
        mask_u8 = (mask_u8.astype(bool) & aoi_r).astype("uint8") 
 
    if mask_u8.max() == 0: 
        raise RuntimeError("Aucun pixel sélectionné. Ajuste le seuil NDVI/morphologie/AOI.") 
 
    # 2) ⚡ Anti-eau au niveau raster (ultra rapide) 
    final_mask, dropped_mean, dropped_p90 = fast_label_filter_by_ndvi( 
        mask_u8, 
        ndvi, 
        mean_min=CONFIG["mean_min"], 
        p90_min=CONFIG["p90_min"], 
        use_p90=(not CONFIG["FAST_MEAN_ONLY"]) 
    ) 
    if dropped_mean: 
        print(f"🚫 Composantes supprimées par mean NDVI: {dropped_mean}") 
    if not CONFIG["FAST_MEAN_ONLY"] and dropped_p90: 
        print(f"🚫 Composantes supprimées par p90 NDVI: {dropped_p90}") 
 
    if final_mask.max() == 0: 
        raise RuntimeError("Tous les objets ont été filtrés (NDVI trop bas). " 
                           "Baisse mean_min/p90_min ou remonte légèrement threshold_value.") 
 
    # 3) Vectorisation (une seule fois, sur masque final réduit) 
    gdf = polygonize(final_mask, tr, crs) 
    if gdf.empty: 
        raise RuntimeError("Vectorisation vide après filtrage. Réglage des seuils nécessaire.") 
 
    # 4) Aire + filtre m² + champ total km² 
    gdf_m = to_metric_for_area(gdf, CONFIG["TARGET_EPSG"]) 
    gdf_m["area_m2"] = gdf_m.geometry.area 
    gdf_m = gdf_m[gdf_m["area_m2"] >= CONFIG["min_area_m2"]].copy() 
    gdf_m["area_km2"] = (gdf_m["area_m2"] / 1e6) 
 
    if CONFIG.get("ADD_TOTAL_FIELD", True) and not gdf_m.empty: 
        total_km2 = float(gdf_m["area_km2"].sum()) 
        total_km2 = round(total_km2, int(CONFIG.get("TOTAL_DECIMALS", 4))) 
        fld = str(CONFIG.get("TOTAL_FIELD_NAME", "TOT_KM2"))[:10]  # DBF ≤ 10 chars 
        gdf_m[fld] = total_km2 
 
    # Arrondis finaux pour la table 
    gdf_m["area_km2"] = gdf_m["area_km2"].round(int(CONFIG.get("TOTAL_DECIMALS", 4))) 
 
    # 5) Retour CRS source + export 
    gdf_out = gdf_m.to_crs(crs) 
    out_path = os.path.join(CONFIG["OUT_DIR"], CONFIG["OUT_SHP"]) 
    gdf_out.to_file(out_path) 
 
    print(f"✅ Shapefile écrit : {out_path}") 
    print(f"🌿 Surface totale = {gdf_m['area_km2'].sum():.{CONFIG.get('TOTAL_DECIMALS',4)}f} km²") 
    if CONFIG.get("ADD_TOTAL_FIELD", True): 
        print(f"🧾 Champ total ajouté : {CONFIG.get('TOTAL_FIELD_NAME','TOT_KM2')}") 
    print("⚡ Mode rapide activé :", "mean NDVI seul" if CONFIG["FAST_MEAN_ONLY"] else "mean + p90 NDVI") 
 
if __name__ == "__main__": 
    main() 
 