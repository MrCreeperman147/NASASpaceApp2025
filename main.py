"""
Traitement de l'image amogus.png - NASASpaceApp2025
"""

import sys
from pathlib import Path
import numpy as np

# Import de la configuration
import config

# Import des modules du projet
from src.image_processing import ImageProcessor


def traiter_amogus():
    """Traite l'image amogus.png avec différents filtres"""
    print("\n" + "=" * 70)
    print("TRAITEMENT DE L'IMAGE AMOGUS.PNG")
    print("=" * 70 + "\n")
    
    # Créer une instance du processeur
    processor = ImageProcessor()
    
    # Chemin de l'image
    image_path = config.RAW_DATA_DIR / "amogus.png"
    
    # Vérifier que l'image existe
    if not image_path.exists():
        print(f"❌ Erreur : L'image n'existe pas à l'emplacement {image_path}")
        print("   Assurez-vous que amogus.png est dans data/raw/")
        return False
    
    try:
        # 1. Charger l'image
        print("1. Chargement de amogus.png...")
        img = processor.load_image(image_path)
        print(f"   ✓ Image chargée : {img.shape}, dtype={img.dtype}")
        print(f"   ✓ Dimensions : {img.shape[1]}x{img.shape[0]} pixels")
        if len(img.shape) == 3:
            print(f"   ✓ Canaux : {img.shape[2]} (couleur)")
        else:
            print(f"   ✓ Image en niveaux de gris")
        
        # 2. Sauvegarder une copie originale dans output
        print("\n2. Sauvegarde de la copie originale...")
        processor.save_image(img, config.OUTPUT_DIR / "amogus_original.png")
        
        # 3. Redimensionner (plusieurs tailles)
        print("\n3. Création de différentes tailles...")
        sizes = [(128, 128), (256, 256), (512, 512)]
        for size in sizes:
            resized = processor.resize(img, size)
            filename = f"amogus_resized_{size[0]}x{size[1]}.png"
            processor.save_image(resized, config.OUTPUT_DIR / filename)
            print(f"   ✓ {filename}")
        
        # 4. Appliquer différents filtres
        print("\n4. Application de filtres...")
        
        # Convertir en niveaux de gris si nécessaire pour certains filtres
        if len(img.shape) == 3:
            img_gray = img[:,:,0]  # Prendre le canal rouge
        else:
            img_gray = img
        
        # Filtre gaussien
        print("   • Filtre gaussien...")
        filtered_gaussian = processor.apply_filter(img_gray, 'gaussian')
        filtered_gaussian_uint8 = (filtered_gaussian * 255).astype('uint8')
        processor.save_image(filtered_gaussian_uint8, 
                           config.OUTPUT_DIR / "amogus_gaussian.png")
        
        # Filtre médian
        print("   • Filtre médian...")
        filtered_median = processor.apply_filter(img_gray, 'median')
        if filtered_median.max() <= 1.0:
            filtered_median = (filtered_median * 255).astype('uint8')
        processor.save_image(filtered_median, 
                           config.OUTPUT_DIR / "amogus_median.png")
        
        # Filtre Sobel (détection de gradients)
        print("   • Filtre Sobel (gradients)...")
        filtered_sobel = processor.apply_filter(img_gray, 'sobel')
        filtered_sobel_uint8 = (filtered_sobel * 255).astype('uint8')
        processor.save_image(filtered_sobel_uint8, 
                           config.OUTPUT_DIR / "amogus_sobel.png")
        
        # 5. Détection de contours
        print("\n5. Détection de contours...")
        edges = processor.detect_edges(img)
        processor.save_image(edges, config.OUTPUT_DIR / "amogus_edges.png")
        print("   ✓ amogus_edges.png")
        
        # 6. Amélioration du contraste
        print("\n6. Amélioration du contraste...")
        enhanced = processor.enhance_contrast(img_gray)
        enhanced_uint8 = (enhanced * 255).astype('uint8')
        processor.save_image(enhanced_uint8, 
                           config.OUTPUT_DIR / "amogus_enhanced.png")
        print("   ✓ amogus_enhanced.png")
        
        # 7. Statistiques sur l'image
        print("\n7. Statistiques de l'image...")
        print(f"   • Valeur minimale : {img.min()}")
        print(f"   • Valeur maximale : {img.max()}")
        print(f"   • Valeur moyenne : {img.mean():.2f}")
        print(f"   • Écart-type : {img.std():.2f}")
        
        print("\n" + "=" * 70)
        print("✅ TRAITEMENT TERMINÉ AVEC SUCCÈS !")
        print("=" * 70)
        print(f"\nRésultats sauvegardés dans : {config.OUTPUT_DIR}")
        print("\nFichiers créés :")
        print("  • amogus_original.png       - Copie de l'original")
        print("  • amogus_resized_*.png      - Différentes tailles")
        print("  • amogus_gaussian.png       - Filtre gaussien (lissage)")
        print("  • amogus_median.png         - Filtre médian (réduction bruit)")
        print("  • amogus_sobel.png          - Détection de gradients")
        print("  • amogus_edges.png          - Détection de contours")
        print("  • amogus_enhanced.png       - Contraste amélioré")
        print("=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur lors du traitement : {e}")
        import traceback
        traceback.print_exc()
        return False


def afficher_info_image():
    """Affiche des informations détaillées sur amogus.png"""
    processor = ImageProcessor()
    image_path = config.RAW_DATA_DIR / "amogus.png"
    
    if not image_path.exists():
        print(f"❌ Image introuvable : {image_path}")
        return
    
    print("\n" + "=" * 70)
    print("INFORMATIONS SUR AMOGUS.PNG")
    print("=" * 70 + "\n")
    
    # Charger avec PIL pour avoir plus d'infos
    from PIL import Image
    img_pil = Image.open(image_path)
    img_array = processor.load_image(image_path)
    
    print(f"Chemin complet : {image_path.absolute()}")
    print(f"Taille du fichier : {image_path.stat().st_size / 1024:.2f} Ko")
    print(f"\nFormat : {img_pil.format}")
    print(f"Mode : {img_pil.mode}")
    print(f"Dimensions : {img_pil.size[0]} x {img_pil.size[1]} pixels")
    print(f"Shape NumPy : {img_array.shape}")
    print(f"Type de données : {img_array.dtype}")
    print(f"Plage de valeurs : [{img_array.min()}, {img_array.max()}]")
    
    print("=" * 70 + "\n")


def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("NASA SPACE APPS CHALLENGE 2025")
    print("Traitement d'image : amogus.png")
    print("=" * 70 + "\n")
    
    try:
        # Afficher la configuration
        config.print_config()
        
        # Afficher les infos sur l'image
        afficher_info_image()
        
        # Traiter l'image
        success = traiter_amogus()
        
        if success:
            print("\n✅ Programme terminé avec succès !")
            print(f"Consultez les résultats dans : {config.OUTPUT_DIR}\n")
        else:
            print("\n❌ Le traitement a échoué.")
            sys.exit(1)
        
    except ImportError as e:
        print(f"\n❌ Erreur d'import : {e}")
        print("\nAssurez-vous que :")
        print("  1. Le fichier src/__init__.py existe")
        print("  2. Le fichier src/image_processing.py existe")
        print("  3. L'environnement virtuel est activé")
        print("  4. Toutes les librairies sont installées")
        print("\nCommande : venv\\Scripts\\activate")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()