"""
Point d'entrée principal - NASASpaceApp2025
Interface graphique pour visualisation de carte du monde
"""

import sys
from pathlib import Path
import tkinter as tk

# Import de la GUI
from src.gui import WorldMapGUI


def main():
    """Point d'entrée principal avec interface graphique de carte"""
    print("=" * 70)
    print("NASA SPACE APP 2025 - CARTE DU MONDE INTERACTIVE")
    print("=" * 70)
    print("Lancement de l'interface de carte...")
    
    try:
        root = tk.Tk()
        app = WorldMapGUI(root)
        
        print("✓ Interface de carte initialisée")
        print("✓ Vous pouvez maintenant explorer la carte")
        print("=" * 70)
        
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()