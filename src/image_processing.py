"""
Module de traitement d'images pour NASASpaceApp2025
"""
import numpy as np
from PIL import Image
import cv2
from skimage import filters, exposure, transform
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
import config

class ImageProcessor:
    """Classe pour le traitement d'images"""
    
    def __init__(self):
        self.supported_formats = config.SUPPORTED_IMAGE_FORMATS
    
    def load_image(self, filepath, as_array=True):
        """
        Charge une image depuis un fichier
        
        Args:
            filepath: Chemin vers l'image
            as_array: Si True, retourne un array NumPy, sinon un objet PIL
        
        Returns:
            Image chargée
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Le fichier {filepath} n'existe pas")
        
        if filepath.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
        
        img = Image.open(filepath)
        
        if as_array:
            return np.array(img)
        return img
    
    def save_image(self, image, filepath):
        """
        Sauvegarde une image
        
        Args:
            image: Image (array NumPy ou objet PIL)
            filepath: Chemin de destination
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(image, np.ndarray):
            # Convertir array NumPy en image PIL
            if len(image.shape) == 2:
                # Image en niveaux de gris
                pil_image = Image.fromarray(image.astype('uint8'), mode='L')
            else:
                # Image couleur
                pil_image = Image.fromarray(image.astype('uint8'))
        else:
            pil_image = image
        
        pil_image.save(filepath)
        print(f"✓ Image sauvegardée : {filepath}")
    
    def resize(self, image, size):
        """
        Redimensionne une image
        
        Args:
            image: Image (array NumPy)
            size: Tuple (largeur, hauteur)
        
        Returns:
            Image redimensionnée
        """
        return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
    
    def apply_filter(self, image, filter_type='gaussian'):
        """
        Applique un filtre à l'image
        
        Args:
            image: Image (array NumPy)
            filter_type: Type de filtre ('gaussian', 'median', 'sobel')
        
        Returns:
            Image filtrée
        """
        if filter_type == 'gaussian':
            return filters.gaussian(image, sigma=1.0)
        elif filter_type == 'median':
            return filters.median(image)
        elif filter_type == 'sobel':
            return filters.sobel(image)
        else:
            raise ValueError(f"Filtre non supporté: {filter_type}")
    
    def enhance_contrast(self, image):
        """Améliore le contraste de l'image"""
        return exposure.equalize_adapthist(image)
    
    def detect_edges(self, image):
        """Détecte les contours dans l'image"""
        # Convertir en niveaux de gris si nécessaire
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Détection de contours avec Canny
        edges = cv2.Canny(gray.astype('uint8'), 50, 150)
        return edges
    
    def batch_process(self, input_dir, output_dir, operation):
        """Traitement par lot d'images"""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for img_file in input_dir.glob("*"):
            if img_file.suffix.lower() in self.supported_formats:
                try:
                    image = self.load_image(img_file)
                    processed = operation(image)
                    output_path = output_dir / img_file.name
                    self.save_image(processed, output_path)
                    print(f"✓ Traité: {img_file.name}")
                except Exception as e:
                    print(f"❌ Erreur avec {img_file.name}: {e}")


def example_usage():
    """Exemple d'utilisation du module"""
    processor = ImageProcessor()
    
    print("Exemple d'utilisation du module de traitement d'images")
    print("=" * 60)
    
    # Créer une image de test
    test_image = np.random.randint(0, 255, (512, 512, 3), dtype='uint8')
    test_path = config.OUTPUT_DIR / "test_image.png"
    
    # Sauvegarder
    processor.save_image(test_image, test_path)
    
    # Charger
    loaded = processor.load_image(test_path)
    print(f"Image chargée : shape={loaded.shape}, dtype={loaded.dtype}")
    
    # Redimensionner
    resized = processor.resize(loaded, (256, 256))
    print(f"Image redimensionnée : shape={resized.shape}")
    
    # Appliquer un filtre
    filtered = processor.apply_filter(loaded[:,:,0], 'gaussian')
    print(f"Filtre appliqué : shape={filtered.shape}")
    
    print("=" * 60)
    print("✅ Exemple terminé")


if __name__ == "__main__":
    example_usage()