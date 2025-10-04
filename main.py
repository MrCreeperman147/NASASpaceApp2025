"""
Point d'entrée principal - NASASpaceApp2025
Interface graphique pour le traitement d'images
"""

import sys
from pathlib import Path
import tkinter as tk

# Import de la GUI
from src.gui import ImageProcessingGUI


def main():
    """Point d'entrée principal avec interface graphique"""
    print("=" * 70)
    print("NASA SPACE APP 2025 - TRAITEMENT D'IMAGES")
    print("=" * 70)
    print("Lancement de l'interface graphique...")
    
    try:
        root = tk.Tk()
        app = ImageProcessingGUI(root)
        
        print("✓ Interface graphique initialisée")
        print("✓ Vous pouvez maintenant utiliser l'application")
        print("=" * 70)
        
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()