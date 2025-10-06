#!/usr/bin/env python3
"""
Script pour diagnostiquer et corriger le problème PROJ_DATA
"""

import os
import sys
from pathlib import Path

def find_proj_db():
    """Trouve le fichier proj.db dans l'installation Python"""
    print("🔍 Recherche de proj.db...")
    
    # Chemins à vérifier
    candidates = [
        # Dans le venv
        Path(sys.prefix) / "share" / "proj" / "proj.db",
        Path(sys.prefix) / "Library" / "share" / "proj" / "proj.db",
        
        # Dans le système (conda)
        Path(sys.prefix).parent / "share" / "proj" / "proj.db",
        
        # Chemins Windows typiques
        Path("C:/") / "Users" / os.environ.get('USERNAME', '') / "anaconda3" / "Library" / "share" / "proj" / "proj.db",
        Path("C:/") / "ProgramData" / "Anaconda3" / "Library" / "share" / "proj" / "proj.db",
    ]
    
    # Chercher récursivement dans sys.prefix
    for path in Path(sys.prefix).rglob("proj.db"):
        if path.is_file():
            print(f"   ✅ Trouvé: {path}")
            return path.parent
    
    # Vérifier les candidats
    for candidate in candidates:
        if candidate.exists():
            print(f"   ✅ Trouvé: {candidate.parent}")
            return candidate.parent
    
    print("   ❌ proj.db introuvable!")
    return None

def setup_proj_env():
    """Configure les variables d'environnement PROJ"""
    print("\n📋 Configuration actuelle:")
    print(f"   Python prefix: {sys.prefix}")
    print(f"   PROJ_DATA: {os.environ.get('PROJ_DATA', 'Non défini')}")
    
    # Trouver proj.db
    proj_dir = find_proj_db()
    
    if proj_dir:
        # Définir PROJ_DATA
        os.environ['PROJ_DATA'] = str(proj_dir)
        print(f"\n✅ PROJ_DATA défini: {proj_dir}")
        
        # Vérifier avec pyproj
        try:
            from pyproj import datadir
            datadir.set_data_dir(str(proj_dir))
            print(f"✅ pyproj.datadir configuré")
            
            # Test
            from pyproj import CRS
            crs = CRS.from_epsg(4326)
            print(f"✅ Test CRS réussi: {crs.name}")
            
            return True
        except Exception as e:
            print(f"❌ Erreur pyproj: {e}")
            return False
    else:
        print("\n❌ Impossible de trouver proj.db")
        print("\n💡 Solutions:")
        print("   1. Réinstaller pyproj:")
        print("      pip uninstall pyproj")
        print("      pip install pyproj")
        print("\n   2. Ou avec conda:")
        print("      conda install -c conda-forge pyproj proj")
        
        return False

if __name__ == "__main__":
    success = setup_proj_env()
    sys.exit(0 if success else 1)