"""
Script de visualisation des résultats du traitement d'amogus.png
Affiche toutes les images dans une grille
"""

import matplotlib.pyplot as plt
from pathlib import Path
import config
from src.image_processing import ImageProcessor

def visualiser_resultats():
    """Affiche tous les résultats du traitement dans une grille"""
    
    processor = ImageProcessor()
    output_dir = config.OUTPUT_DIR
    
    # Liste des images à afficher
    images_info = [
        ("amogus_original.png", "Original"),
        ("amogus_resized_256x256.png", "Redimensionné 256x256"),
        ("amogus_gaussian.png", "Filtre Gaussien"),
        ("amogus_median.png", "Filtre Médian"),
        ("amogus_sobel.png", "Sobel (gradients)"),
        ("amogus_edges.png", "Contours (Canny)"),
        ("amogus_enhanced.png", "Contraste amélioré"),
    ]
    
    # Créer la figure
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    fig.suptitle('Résultats du traitement de amogus.png', fontsize=16, fontweight='bold')
    
    axes = axes.flatten()
    
    # Afficher chaque image
    for idx, (filename, title) in enumerate(images_info):
        filepath = output_dir / filename
        
        if filepath.exists():
            img = processor.load_image(filepath)
            
            # Afficher en niveaux de gris si c'est une image 2D
            if len(img.shape) == 2:
                axes[idx].imshow(img, cmap='gray')
            else:
                axes[idx].imshow(img)
            
            axes[idx].set_title(title, fontweight='bold')
            axes[idx].axis('off')
        else:
            axes[idx].text(0.5, 0.5, f'Image\nmanquante:\n{filename}', 
                          ha='center', va='center', fontsize=10)
            axes[idx].axis('off')
    
    # Masquer les axes non utilisés
    for idx in range(len(images_info), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    # Sauvegarder la grille
    output_path = output_dir / "amogus_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ Grille de comparaison sauvegardée : {output_path}")
    
    # Afficher
    plt.show()


def comparer_original_traite(filter_name="edges"):
    """Compare l'original avec un traitement spécifique côte à côte"""
    
    processor = ImageProcessor()
    
    original_path = config.RAW_DATA_DIR / "amogus.png"
    processed_path = config.OUTPUT_DIR / f"amogus_{filter_name}.png"
    
    if not original_path.exists():
        print(f"❌ Image originale introuvable : {original_path}")
        return
    
    if not processed_path.exists():
        print(f"❌ Image traitée introuvable : {processed_path}")
        print("   Exécutez d'abord : python main.py")
        return
    
    original = processor.load_image(original_path)
    processed = processor.load_image(processed_path)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    ax1.imshow(original if len(original.shape) == 3 else original, 
               cmap=None if len(original.shape) == 3 else 'gray')
    ax1.set_title('Original', fontweight='bold', fontsize=14)
    ax1.axis('off')
    
    ax2.imshow(processed if len(processed.shape) == 3 else processed,
               cmap=None if len(processed.shape) == 3 else 'gray')
    ax2.set_title(f'Après traitement: {filter_name}', fontweight='bold', fontsize=14)
    ax2.axis('off')
    
    plt.tight_layout()
    plt.show()


def main():
    """Menu principal"""
    print("\n" + "=" * 70)
    print("VISUALISATION DES RÉSULTATS - AMOGUS.PNG")
    print("=" * 70 + "\n")
    
    print("Options :")
    print("  1. Afficher tous les résultats dans une grille")
    print("  2. Comparer original vs contours")
    print("  3. Comparer original vs filtre gaussien")
    print("  4. Comparer original vs contraste amélioré")
    print()
    
    try:
        choice = input("Votre choix (1-4) : ").strip()
        
        if choice == "1":
            visualiser_resultats()
        elif choice == "2":
            comparer_original_traite("edges")
        elif choice == "3":
            comparer_original_traite("gaussian")
        elif choice == "4":
            comparer_original_traite("enhanced")
        else:
            print("❌ Choix invalide")
            
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Vérifier si matplotlib est installé
    try:
        import matplotlib
        main()
    except ImportError:
        print("❌ matplotlib n'est pas installé")
        print("Installez-le avec : pip install matplotlib")