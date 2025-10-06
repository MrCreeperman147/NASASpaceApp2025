#!/usr/bin/env python3
"""
Pipeline Processor - NASA Space Apps Challenge 2025
Orchestre le téléchargement, traitement et génération de shapefiles
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import subprocess
import pickle
import skimage

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Scopes pour Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class PipelineProcessor:
    def __init__(self, base_folder_name='Sentinel-2_Iles_Madeleine'):
        self.base_folder_name = base_folder_name
        self.temp_dir = Path('temp')
        self.zips_dir = self.temp_dir / 'zips'
        self.extracts_dir = self.temp_dir / 'extracts'
        self.output_dir = Path('output/shapefiles')
        
        # Créer les dossiers nécessaires
        self.zips_dir.mkdir(parents=True, exist_ok=True)
        self.extracts_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.service = None
    
    def authenticate_drive(self):
        """Authentifie avec Google Drive"""
        creds = None
        
        # Token sauvegardé
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # Si pas de credentials valides
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Sauvegarder
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        print("✅ Authentification Google Drive réussie")
    
    def find_base_folder(self):
        """Trouve le dossier de base sur Drive"""
        query = f"name='{self.base_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print(f"❌ Dossier '{self.base_folder_name}' non trouvé sur Drive")
            return None
        
        return files[0]['id']
    
    def list_year_folders(self, parent_id):
        """Liste les dossiers d'années dans le dossier de base"""
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            orderBy='name'
        ).execute()
        
        files = results.get('files', [])
        
        # Filtrer pour ne garder que les années (format: YYYY)
        year_folders = []
        for file in files:
            try:
                year = int(file['name'])
                if 2000 <= year <= 2100:  # Validation année
                    year_folders.append({'id': file['id'], 'name': file['name'], 'year': year})
            except ValueError:
                continue
        
        return sorted(year_folders, key=lambda x: x['year'])
    
    def list_files_in_folder(self, folder_id):
        """Liste tous les fichiers ZIP dans un dossier"""
        query = f"'{folder_id}' in parents and trashed=false"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size)',
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        # Filtrer les ZIP
        zip_files = [f for f in files if f['name'].endswith('.zip')]
        
        return zip_files
    
    def download_file(self, file_id, file_name, destination):
        """Télécharge un fichier depuis Drive"""
        request = self.service.files().get_media(fileId=file_id)
        
        file_path = destination / file_name
        
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            
            print(f"   📥 Téléchargement: {file_name}")
            
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"\r      Progression: {progress}%", end='', flush=True)
            
            print()  # Nouvelle ligne
        
        return file_path
    
    def extract_zip(self, zip_path, extract_to):
        """Extrait un fichier ZIP"""
        print(f"   📦 Extraction: {zip_path.name}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        print(f"      ✅ Extrait dans: {extract_to}")
    
    def find_tci_files(self, extract_dir):
        """
        Trouve les fichiers TCI dans la structure GRANULE
        
        Structure attendue:
        extract_dir/
        └── PRODUCT.SAFE/
            └── GRANULE/
                └── L2A_TXXXXX_AXXXXXX_YYYYMMDDTHHMMSS/
                    └── IMG_DATA/
                        ├── TCI.jp2 (si fichiers directs)
                        └── R10m/ (ou R20m, R60m)
                            └── TCI_10m.jp2
        """
        tci_files = []
        
        # Chercher le dossier GRANULE
        granule_dirs = list(extract_dir.rglob('GRANULE'))
        
        if not granule_dirs:
            print(f"      ⚠️  Pas de dossier GRANULE trouvé")
            return tci_files
        
        for granule_dir in granule_dirs:
            # Lister les sous-dossiers dans GRANULE
            for subdir in granule_dir.iterdir():
                if not subdir.is_dir():
                    continue
                
                img_data_dir = subdir / 'IMG_DATA'
                
                if not img_data_dir.exists():
                    continue
                
                # Cas 1: Fichiers directement dans IMG_DATA
                direct_files = list(img_data_dir.glob('*TCI*.jp2'))
                
                if direct_files:
                    tci_files.extend(direct_files)
                    print(f"      📍 TCI trouvé (direct): {direct_files[0].name}")
                else:
                    # Cas 2: Dans des sous-dossiers de résolution
                    resolution_dirs = [d for d in img_data_dir.iterdir() if d.is_dir()]
                    
                    if resolution_dirs:
                        # Trier par résolution (R10m < R20m < R60m)
                        resolution_dirs.sort(key=lambda x: x.name)
                        
                        # Prendre le dossier de plus petite résolution
                        smallest_res_dir = resolution_dirs[0]
                        
                        res_tci_files = list(smallest_res_dir.glob('*TCI*.jp2'))
                        
                        if res_tci_files:
                            tci_files.extend(res_tci_files)
                            print(f"      📍 TCI trouvé ({smallest_res_dir.name}): {res_tci_files[0].name}")
        
        return tci_files
    
    def process_pair(self, year, tci_files):
        """Traite une paire de fichiers TCI"""
        if len(tci_files) < 2:
            print(f"      ⚠️  Pas assez de fichiers TCI ({len(tci_files)})")
            return None
        
        print(f"   🔧 Traitement QGIS...")
        
        # Appeler traitement_qgis.py
        tci_1 = str(tci_files[0])
        tci_2 = str(tci_files[1])
        
        try:
            # Importer et exécuter traitement_qgis
            sys.path.insert(0, 'src/qgis')
            import traitement_qgis
            
            # Appeler la fonction de traitement (à adapter selon votre code)
            mosaic_b04, mosaic_b08 = traitement_qgis.process_tci_pair(tci_1, tci_2)
            
            print(f"      ✅ Mosaïques créées")
            print(f"         B04: {mosaic_b04}")
            print(f"         B08: {mosaic_b08}")
            
            # Appeler code_de_surface.py
            print(f"   🔧 Calcul de surface...")
            
            import code_de_surface
            
            shapefile_path = code_de_surface.process_ndvi(
                band_red=mosaic_b04,
                band_nir=mosaic_b08,
                output_dir=self.output_dir,
                output_name=f"surface_{year}.shp"
            )
            
            print(f"      ✅ Shapefile créé: {shapefile_path}")
            
            return shapefile_path
            
        except Exception as e:
            print(f"      ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def cleanup_temp(self):
        """Nettoie les fichiers temporaires"""
        print("   🗑️  Nettoyage des fichiers temporaires...")
        
        if self.zips_dir.exists():
            shutil.rmtree(self.zips_dir)
            self.zips_dir.mkdir()
        
        if self.extracts_dir.exists():
            shutil.rmtree(self.extracts_dir)
            self.extracts_dir.mkdir()
        
        print("      ✅ Nettoyage terminé")
    
    def process_all_years(self, progress_callback=None):
        """Traite toutes les années disponibles sur Drive"""
        print("\n" + "="*80)
        print("🚀 DÉMARRAGE DU PIPELINE DE TRAITEMENT")
        print("="*80)
        
        # Authentification
        if not self.service:
            self.authenticate_drive()
        
        # Trouver le dossier de base
        print(f"\n📁 Recherche du dossier '{self.base_folder_name}'...")
        base_folder_id = self.find_base_folder()
        
        if not base_folder_id:
            return []
        
        print(f"   ✅ Dossier trouvé")
        
        # Lister les années
        print(f"\n📅 Liste des années disponibles...")
        year_folders = self.list_year_folders(base_folder_id)
        
        if not year_folders:
            print("   ⚠️  Aucun dossier d'année trouvé")
            return []
        
        print(f"   ✅ {len(year_folders)} année(s) trouvée(s)")
        for yf in year_folders:
            print(f"      • {yf['name']}")
        
        # Traiter chaque année
        results = []
        
        for idx, year_folder in enumerate(year_folders):
            year = year_folder['year']
            folder_id = year_folder['id']
            
            print(f"\n{'='*80}")
            print(f"📅 ANNÉE {year} ({idx + 1}/{len(year_folders)})")
            print(f"{'='*80}")
            
            # Callback de progression
            if progress_callback:
                progress_callback(idx + 1, len(year_folders), year)
            
            # Lister les fichiers
            print(f"\n   📋 Liste des fichiers...")
            files = self.list_files_in_folder(folder_id)
            
            if not files:
                print(f"      ⚠️  Aucun fichier ZIP trouvé")
                continue
            
            print(f"      ✅ {len(files)} fichier(s) ZIP trouvé(s)")
            
            # Télécharger les fichiers
            downloaded_zips = []
            
            for file in files:
                file_path = self.download_file(
                    file['id'],
                    file['name'],
                    self.zips_dir
                )
                downloaded_zips.append(file_path)
            
            # Extraire les fichiers
            print(f"\n   📦 Extraction des fichiers...")
            year_extract_dir = self.extracts_dir / str(year)
            year_extract_dir.mkdir(exist_ok=True)
            
            for zip_path in downloaded_zips:
                self.extract_zip(zip_path, year_extract_dir)
            
            # Trouver les fichiers TCI
            print(f"\n   🔍 Recherche des fichiers TCI...")
            tci_files = self.find_tci_files(year_extract_dir)
            
            if not tci_files:
                print(f"      ⚠️  Aucun fichier TCI trouvé")
                self.cleanup_temp()
                continue
            
            print(f"      ✅ {len(tci_files)} fichier(s) TCI trouvé(s)")
            
            # Traiter la paire
            print(f"\n   🔧 Traitement de la paire...")
            shapefile_path = self.process_pair(year, tci_files)
            
            if shapefile_path:
                results.append({
                    'year': year,
                    'shapefile': str(shapefile_path),
                    'status': 'success'
                })
            else:
                results.append({
                    'year': year,
                    'shapefile': None,
                    'status': 'failed'
                })
            
            # Nettoyage
            self.cleanup_temp()
        
        # Résumé final
        print(f"\n{'='*80}")
        print("📊 RÉSUMÉ DU TRAITEMENT")
        print(f"{'='*80}")
        
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        print(f"\n   ✅ Réussis: {len(successful)}/{len(results)}")
        print(f"   ❌ Échecs: {len(failed)}/{len(results)}")
        
        if successful:
            print(f"\n   📁 Shapefiles générés:")
            for r in successful:
                print(f"      • {r['year']}: {Path(r['shapefile']).name}")
        
        return results


if __name__ == "__main__":
    processor = PipelineProcessor()
    results = processor.process_all_years()
    
    # Sauvegarder les résultats
    results_file = Path('output/processing_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Résultats sauvegardés dans: {results_file}")