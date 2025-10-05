"""
Point d'entrée principal - NASASpaceApp2025
Carte du monde interactive avec Folium
"""

import sys
from pathlib import Path

# Import de la GUI Folium
from gui_folium import FoliumMapGUI
import tkinter as tk


def main():
    """Point d'entrée principal avec interface Folium"""
    print("=" * 70)
    print("NASA SPACE APP 2025 - CARTE INTERACTIVE FOLIUM")
    print("=" * 70)
    print("Lancement de l'interface de carte Folium...")
    
    try:
        root = tk.Tk()
        app = FoliumMapGUI(root)
        
        print("✓ Interface Folium initialisée")
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