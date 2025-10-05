"""
API Sentinel-2 et Données de Marée - Version Sécurisée
Credentials chargés depuis credentials.json
"""
import requests
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os
import pickle
import io
import requests

# ============================================================================
# CHARGEMENT SÉCURISÉ DES CREDENTIALS
# ============================================================================

def load_credentials(credentials_file="credentials.json"):
    """
    Charge les credentials depuis le fichier JSON
    
    Args:
        credentials_file: Chemin vers le fichier credentials.json
    
    Returns:
        Dict avec les credentials
    """
    try:
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
        
        # Vérifier que les credentials Copernicus sont présents
        if 'copernicus' not in creds:
            raise KeyError("Section 'copernicus' manquante dans credentials.json")
        
        if 'username' not in creds['copernicus'] or 'password' not in creds['copernicus']:
            raise KeyError("username ou password manquant dans credentials.copernicus")
        
        return creds
    
    except FileNotFoundError:
        print(f"❌ ERREUR: Fichier '{credentials_file}' introuvable!")
        print("\n💡 Créez un fichier credentials.json avec ce format:")
        print("""
{
  "copernicus": {
    "username": "votre_email@example.com",
    "password": "votre_mot_de_passe"
  },
  "installed": {
    "client_id": "...",
    "project_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "...",
    "redirect_uris": ["http://localhost"]
  }
}
        """)
        raise
    
    except json.JSONDecodeError as e:
        print(f"❌ ERREUR: Le fichier credentials.json n'est pas un JSON valide: {e}")
        raise
    
    except KeyError as e:
        print(f"❌ ERREUR: Credentials invalides - {e}")
        raise


# Scopes nécessaires pour Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ============================================================================
# PARTIE 1A: API IWLS - DONNÉES DE MARÉE (Pêches et Océans Canada)
# ============================================================================

def get_tide_data_from_api(station_id="5cebf1e33d0f4a073c4bc285", start_date=None, end_date=None):
    """
    Récupérer les données de marée depuis l'API IWLS
    
    Args:
        station_id: Code de la station (5cebf1e33d0f4a073c4bc285 = Cap-aux-Meules)
        start_date: Date de début (datetime ou string YYYY-MM-DD)
        end_date: Date de fin (datetime ou string YYYY-MM-DD)
    
    Returns:
        Liste des prédictions de marée au format standard
    """
    from datetime import timezone
    
    # NOUVELLE API IWLS (2024+)
    base_url = "https://api.iwls-sine.azure.cloud-nuage.dfo-mpo.gc.ca/api/v1"
    
    # Convertir les dates si nécessaire
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Si pas de dates, utiliser aujourd'hui + 7 jours
    if not start_date:
        start_date = datetime.now()
    if not end_date:
        end_date = start_date + timedelta(days=7)
    
    print(f"\n🌊 Récupération des données de marée depuis l'API IWLS...")
    print(f"   Station: Cap-aux-Meules ({station_id})")
    print(f"   Période: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    
    # Liste des codes de séries temporelles à essayer
    time_series_codes = [
        ('wlp', 'Prédictions'),
        ('wlp-hilo', 'Hautes/Basses eaux prédites'),
        ('wlo', 'Observations'),
        ('wlf', 'Prévisions'),
    ]
    
    for code, description in time_series_codes:
        # Endpoint pour les données de marée
        url = f"{base_url}/stations/{station_id}/data"
        
        # Formater les dates selon le format ISO 8601
        from_date = start_date.isoformat() + 'Z'
        to_date = end_date.isoformat() + 'Z'
        
        params = {
            'time-series-code': code,
            'from': from_date,
            'to': to_date
        }
        
        try:
            print(f"   Essai avec '{code}' ({description})...", end='')
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    print(f" ✓ {len(data)} enregistrements récupérés")
                    
                    # Convertir au format standard
                    tide_data = []
                    for record in data:
                        dt = datetime.fromisoformat(record['eventDate'].replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        
                        tide_data.append({
                            'datetime': dt,
                            'tide_level_m': record.get('value')
                        })
                    
                    return tide_data
                else:
                    print(f" ⚠️  Aucune donnée")
            else:
                print(f" ✗ Erreur {response.status_code}")
                
        except Exception as e:
            print(f" ✗ Erreur: {e}")
            continue
    
    print(f"\n   ✗ Aucune donnée de marée disponible pour cette station/période")
    return []


# ============================================================================
# PARTIE 1B: CHARGEMENT DES DONNÉES DE MARÉE DEPUIS CSV
# ============================================================================

def load_tide_data_from_csv(csv_file_path, date_column='A', tide_column='B', debug=False, show_errors=5, delimiter=None):
    """
    Charger les données de marée depuis un fichier CSV
    
    Format attendu du CSV:
    Colonne A: Date/Heure (formats acceptés: YYYY-MM-DD HH:MM:SS, DD/MM/YYYY HH:MM, etc.)
    Colonne B: Niveau de marée en mètres (nombre décimal)
    
    Args:
        csv_file_path: Chemin vers le fichier CSV
        date_column: Nom ou index de la colonne date (défaut: 'A' ou 0)
        tide_column: Nom ou index de la colonne marée (défaut: 'B' ou 1)
        debug: Si True, affiche les premières erreurs détectées
        show_errors: Nombre d'erreurs à afficher en mode debug
        delimiter: Séparateur (None = détection auto, ',' ou ';' ou '\t')
    
    Returns:
        Liste de dictionnaires avec 'datetime' et 'tide_level_m'
    """
    tide_data = []
    
    # Convertir les références de colonnes (A, B) en indices (0, 1)
    col_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7}
    date_idx = col_map.get(date_column.upper(), 0) if isinstance(date_column, str) and len(date_column) == 1 else int(date_column)
    tide_idx = col_map.get(tide_column.upper(), 1) if isinstance(tide_column, str) and len(tide_column) == 1 else int(tide_column)
    
    print(f"\n📂 CHARGEMENT DES DONNÉES DE MARÉE DEPUIS CSV")
    print(f"{'─'*80}")
    print(f"Fichier: {csv_file_path}")
    
    if not Path(csv_file_path).exists():
        print(f"❌ ERREUR: Le fichier '{csv_file_path}' n'existe pas!")
        return []
    
    # Détection automatique du délimiteur
    if delimiter is None:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline()
            if ';' in first_line:
                delimiter = ';'
            elif '\t' in first_line:
                delimiter = '\t'
            else:
                delimiter = ','
        print(f"Séparateur détecté: '{delimiter}'")
    
    print(f"Colonne date: {date_column} (index {date_idx})")
    print(f"Colonne marée: {tide_column} (index {tide_idx})")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=delimiter)
            
            # Détecter et sauter l'en-tête si présent
            first_row = next(reader)
            
            # Vérifier si c'est un en-tête (contient des lettres non numériques)
            is_header = False
            try:
                # Essayer de convertir la valeur de marée
                test_val = first_row[tide_idx].replace(',', '.').strip()
                float(test_val)
            except (ValueError, IndexError):
                is_header = True
                print(f"ℹ️  En-tête détecté: {' | '.join(first_row[:min(5, len(first_row))])}...")
            
            # Si ce n'est pas un en-tête, traiter la première ligne
            if not is_header:
                f.seek(0)
                reader = csv.reader(f, delimiter=delimiter)
            
            date_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y %H:%M',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y %H:%M',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%d-%m-%Y %H:%M:%S',
                '%d-%m-%Y %H:%M',
                '%Y%m%d %H:%M:%S',
                '%Y%m%d %H:%M',
                '%d.%m.%Y %H:%M:%S',
                '%d.%m.%Y %H:%M',
            ]
            
            skipped_rows = 0
            error_samples = []
            
            for row_num, row in enumerate(reader, start=2 if is_header else 1):
                if len(row) <= max(date_idx, tide_idx):
                    skipped_rows += 1
                    if debug and len(error_samples) < show_errors:
                        error_samples.append({
                            'row': row_num,
                            'reason': f'Ligne trop courte (colonnes: {len(row)})',
                            'content': str(row)[:100]
                        })
                    continue
                
                try:
                    # Extraire la date
                    date_str = row[date_idx].strip()
                    
                    if not date_str:
                        skipped_rows += 1
                        if debug and len(error_samples) < show_errors:
                            error_samples.append({
                                'row': row_num,
                                'reason': 'Date vide',
                                'content': str(row)[:100]
                            })
                        continue
                    
                    # Essayer différents formats
                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date is None:
                        skipped_rows += 1
                        if debug and len(error_samples) < show_errors:
                            error_samples.append({
                                'row': row_num,
                                'reason': f'Format de date non reconnu',
                                'content': f'Date: "{date_str}"'
                            })
                        continue
                    
                    # Rendre la date "timezone-aware" (UTC) pour comparaison avec Sentinel-2
                    from datetime import timezone
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    
                    # Extraire le niveau de marée
                    tide_str = row[tide_idx].strip().replace(',', '.')
                    
                    if not tide_str:
                        skipped_rows += 1
                        if debug and len(error_samples) < show_errors:
                            error_samples.append({
                                'row': row_num,
                                'reason': 'Niveau de marée vide',
                                'content': str(row)[:100]
                            })
                        continue
                    
                    tide_level = float(tide_str)
                    
                    tide_data.append({
                        'datetime': parsed_date,
                        'tide_level_m': tide_level
                    })
                    
                except (ValueError, IndexError) as e:
                    skipped_rows += 1
                    if debug and len(error_samples) < show_errors:
                        error_samples.append({
                            'row': row_num,
                            'reason': f'Erreur: {str(e)}',
                            'content': str(row)[:100]
                        })
                    continue
        
        print(f"\n✅ CHARGEMENT RÉUSSI")
        print(f"   📊 {len(tide_data)} enregistrements chargés")
        if skipped_rows > 0:
            print(f"   ⚠️  {skipped_rows} ligne(s) ignorée(s) (erreur de format)")
        
        # Afficher les erreurs en mode debug
        if debug and error_samples:
            print(f"\n🔍 EXEMPLES D'ERREURS (premières {len(error_samples)}):")
            for err in error_samples:
                print(f"\n   Ligne {err['row']}:")
                print(f"      Raison: {err['reason']}")
                print(f"      Contenu: {err['content']}")
        
        if tide_data:
            print(f"\n   📅 Période couverte:")
            print(f"      Début: {tide_data[0]['datetime'].strftime('%Y-%m-%d %H:%M')}")
            print(f"      Fin:   {tide_data[-1]['datetime'].strftime('%Y-%m-%d %H:%M')}")
            print(f"   🌊 Marée:")
            tide_levels = [t['tide_level_m'] for t in tide_data]
            print(f"      Min: {min(tide_levels):.2f} m")
            print(f"      Max: {max(tide_levels):.2f} m")
            print(f"      Moy: {sum(tide_levels)/len(tide_levels):.2f} m")
        
        # Suggestion si beaucoup d'erreurs
        if skipped_rows > len(tide_data) * 0.5:
            print(f"\n⚠️  ATTENTION: Plus de 50% des lignes ont été ignorées!")
            print(f"   💡 Suggestions:")
            print(f"      - Activez le mode debug: load_tide_data_from_csv(..., debug=True)")
            print(f"      - Vérifiez le format de vos données")
            print(f"      - Vérifiez les colonnes date_column='{date_column}' et tide_column='{tide_column}'")
        
        return tide_data
        
    except Exception as e:
        print(f"\n❌ ERREUR lors du chargement du CSV: {e}")
        return []


def find_closest_tide(tide_data, target_datetime, max_time_diff_minutes=60):
    """
    Trouver le niveau de marée le plus proche d'un moment donné
    
    Args:
        tide_data: Liste des données de marée (depuis load_tide_data_from_csv)
        target_datetime: Moment cible (datetime, timezone-aware)
        max_time_diff_minutes: Différence maximale acceptable en minutes
    
    Returns:
        Dict avec 'tide_level_m', 'tide_datetime', 'time_diff_minutes' ou None
    """
    if not tide_data:
        return None
    
    # S'assurer que target_datetime est timezone-aware
    from datetime import timezone
    if target_datetime.tzinfo is None:
        target_datetime = target_datetime.replace(tzinfo=timezone.utc)
    
    # Trouver l'enregistrement le plus proche
    closest = min(tide_data, key=lambda x: abs((x['datetime'] - target_datetime).total_seconds()))
    
    time_diff_seconds = abs((closest['datetime'] - target_datetime).total_seconds())
    time_diff_minutes = time_diff_seconds / 60
    
    # Vérifier si la différence est acceptable
    if time_diff_minutes > max_time_diff_minutes:
        return None
    
    return {
        'tide_level_m': closest['tide_level_m'],
        'tide_datetime': closest['datetime'],
        'time_diff_minutes': time_diff_minutes
    }


# ============================================================================
# PARTIE 2: API COPERNICUS - IMAGES SENTINEL-2
# ============================================================================

def get_copernicus_token(username, password):
    """Obtenir un token OAuth2 pour Copernicus"""
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": "cdse-public"
    }
    
    response = requests.post(url, data=data, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def deduplicate_sentinel_images(products, strategy='keep_first'):
    """
    Dédupliquer les images Sentinel-2 prises au même moment (tuiles différentes)
    
    Args:
        products: Liste des produits enrichis
        strategy: Stratégie de déduplication
            - 'keep_first': Garde la première tuile trouvée
            - 'keep_all': Garde toutes les tuiles (pas de déduplication)
            - 'merge_tiles': Indique qu'il y a plusieurs tuiles
            - 'keep_only_duplicates': Garde UNIQUEMENT les acquisitions avec plusieurs tuiles
    
    Returns:
        Liste dédupliquée des produits
    """
    if strategy == 'keep_all':
        return products
    
    # Grouper par date/heure de capture (même satellite, même moment)
    from collections import defaultdict
    groups = defaultdict(list)
    
    for product in products:
        # Clé : satellite + date/heure (ignorer les tuiles)
        capture_key = product['capture_datetime'].strftime('%Y%m%d%H%M%S')
        satellite = product['name'][:3]  # S2A ou S2B
        key = f"{satellite}_{capture_key}"
        groups[key].append(product)
    
    deduplicated = []
    duplicates_count = 0
    singles_count = 0
    
    for key, group_products in groups.items():
        if len(group_products) > 1:
            # Plusieurs tuiles pour cette acquisition
            duplicates_count += len(group_products) - 1
            
            if strategy == 'keep_first':
                # Garder seulement la première tuile
                deduplicated.append(group_products[0])
            
            elif strategy == 'merge_tiles':
                # Créer une entrée combinée
                merged = group_products[0].copy()
                tiles = []
                for p in group_products:
                    # Extraire le code de tuile (ex: T20TPT)
                    tile_code = p['name'].split('_')[5]
                    tiles.append(tile_code)
                
                merged['tiles'] = tiles
                merged['tile_count'] = len(tiles)
                merged['name'] = merged['name'] + f" ({len(tiles)} tuiles)"
                deduplicated.append(merged)
            
            elif strategy == 'keep_only_duplicates':
                # Garder toutes les tuiles de cette acquisition multiple
                deduplicated.extend(group_products)
        else:
            # Une seule tuile pour cette acquisition
            singles_count += 1
            
            if strategy != 'keep_only_duplicates':
                deduplicated.append(group_products[0])
    
    if strategy == 'keep_only_duplicates':
        print(f"\n🔄 Filtrage des acquisitions multi-tuiles:")
        print(f"   Images totales: {len(products)}")
        print(f"   Acquisitions avec plusieurs tuiles: {len([g for g in groups.values() if len(g) > 1])}")
        print(f"   Acquisitions avec une seule tuile: {singles_count} (supprimées)")
        print(f"   Images conservées: {len(deduplicated)}")
    elif duplicates_count > 0:
        print(f"\n🔄 Déduplication:")
        print(f"   Images avant: {len(products)}")
        print(f"   Images après: {len(deduplicated)}")
        print(f"   Doublons supprimés: {duplicates_count}")
    
    return deduplicated


def filter_by_tile_pair(products, required_tiles=['T20TNT', 'T20TPT']):
    """
    Filtrer pour garder uniquement les acquisitions ayant TOUTES les tuiles requises
    
    Args:
        products: Liste des produits enrichis
        required_tiles: Liste des tuiles qui doivent TOUTES être présentes
    
    Returns:
        Liste filtrée contenant uniquement les images des acquisitions complètes
    """
    from collections import defaultdict
    
    # Grouper par acquisition (satellite + date/heure)
    groups = defaultdict(list)
    
    for product in products:
        capture_key = product['capture_datetime'].strftime('%Y%m%d%H%M%S')
        satellite = product['name'][:3]
        key = f"{satellite}_{capture_key}"
        groups[key].append(product)
    
    filtered = []
    complete_acquisitions = 0
    incomplete_acquisitions = 0
    
    for key, group_products in groups.items():
        # Extraire les codes de tuiles de ce groupe
        tiles_in_group = set()
        for product in group_products:
            try:
                tile_code = product['name'].split('_')[5]
                tiles_in_group.add(tile_code)
            except (IndexError, KeyError):
                continue
        
        # Vérifier si toutes les tuiles requises sont présentes
        has_all_tiles = all(tile in tiles_in_group for tile in required_tiles)
        
        if has_all_tiles:
            # Garder toutes les images de cette acquisition
            filtered.extend(group_products)
            complete_acquisitions += 1
        else:
            incomplete_acquisitions += 1
    
    print(f"\n Filtrage par paire de tuiles:")
    print(f"   Images totales: {len(products)}")
    print(f"   Tuiles requises: {' + '.join(required_tiles)}")
    print(f"   Acquisitions complètes (toutes les tuiles): {complete_acquisitions}")
    print(f"   Acquisitions incomplètes (ignorées): {incomplete_acquisitions}")
    print(f"   Images conservées: {len(filtered)}")
    
    return filtered


def search_sentinel2_from_csv_dates(username, password, csv_file_path, 
                                     date_column='A', tide_column='B', csv_delimiter=None,
                                     max_cloud_cover=20, time_window_hours=2,
                                     use_api_complement=False, api_station_id="5cebf1e33d0f4a073c4bc285",
                                     filter_tile_pair=None):
    """
    Rechercher des images Sentinel-2 UNIQUEMENT aux dates/heures présentes dans le CSV
    
    Args:
        username: Email Copernicus
        password: Mot de passe Copernicus
        csv_file_path: Chemin vers le fichier CSV des marées
        date_column: Colonne date dans le CSV (défaut: 'A')
        tide_column: Colonne marée dans le CSV (défaut: 'B')
        csv_delimiter: Séparateur CSV (None = auto)
        max_cloud_cover: Couverture nuageuse max en %
        time_window_hours: Fenêtre de recherche autour de chaque date CSV (heures)
        use_api_complement: Si True, complète avec l'API de marée si besoin
        api_station_id: ID de la station pour l'API
        deduplicate: Si True, supprime les tuiles dupliquées (même acquisition)
    
    Returns:
        Liste des images avec leurs données de marée
    """
    print("\n" + "="*80)
    print("RECHERCHE IMAGES SENTINEL-2 BASÉE SUR LES DATES DU CSV")
    print("="*80)
    
    # Charger le CSV
    tide_data = load_tide_data_from_csv(csv_file_path, date_column, tide_column, 
                                        debug=False, delimiter=csv_delimiter)
    
    if not tide_data:
        print("❌ Impossible de charger le CSV")
        return []
    
    # Extraire la période couverte
    start_date = min(d['datetime'] for d in tide_data)
    end_date = max(d['datetime'] for d in tide_data)
    
    print(f"\n📅 Période du CSV:")
    print(f"   Du:  {start_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Au:  {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Total: {len(tide_data)} enregistrements")
    
    # Obtenir le token Copernicus
    print(f"\n🔐 Authentification Copernicus...")
    token = get_copernicus_token(username, password)
    print(f"   ✓ Token obtenu")
    
    # Paramètres de recherche
    bbox = [-62.30, 47.10, -61.40, 47.60]  # Îles de la Madeleine
    
    # Rechercher les images par périodes (par mois pour éviter les requêtes trop larges)
    all_products = []
    current = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    print(f"\n📡 Recherche des images Sentinel-2...")
    print(f"   Fenêtre temporelle: ±{time_window_hours}h autour de chaque date CSV")
    
    while current <= end_date:
        # Fin du mois
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        
        month_end = min(next_month, end_date + timedelta(days=1))
        
        # Recherche pour ce mois
        url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        
        filter_query = (
            f"Collection/Name eq 'SENTINEL-2' and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(("
            f"{bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},"
            f"{bbox[2]} {bbox[3]},{bbox[0]} {bbox[3]},"
            f"{bbox[0]} {bbox[1]}))') and "
            f"ContentDate/Start gt {current.strftime('%Y-%m-%d')}T00:00:00.000Z and "
            f"ContentDate/Start lt {month_end.strftime('%Y-%m-%d')}T00:00:00.000Z and "
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {max_cloud_cover})"
        )
        
        params = {
            "$filter": filter_query,
            "$orderby": "ContentDate/Start desc",
            "$top": 100,
            "$expand": "Attributes"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()
            products = response.json().get('value', [])
            all_products.extend(products)
            print(f"   {current.strftime('%Y-%m')}: {len(products)} image(s)")
        except Exception as e:
            print(f"   {current.strftime('%Y-%m')}: Erreur - {e}")
        
        current = next_month
    
    print(f"\n   ✓ Total: {len(all_products)} images trouvées")
    
    # Filtrer les images pour ne garder que celles proches des dates CSV
    print(f"\n🔍 Filtrage des images selon les dates du CSV...")
    
    enriched_products = []
    images_matched = 0
    images_rejected = 0
    
    time_window = timedelta(hours=time_window_hours)
    
    # Créer un ensemble des timestamps CSV (arrondi à l'heure)
    csv_times = {d['datetime'].replace(minute=0, second=0, microsecond=0) for d in tide_data}
    
    for product in all_products:
        # Extraire l'heure de capture
        capture_time = datetime.fromisoformat(product['ContentDate']['Start'].replace('Z', '+00:00'))
        capture_hour = capture_time.replace(minute=0, second=0, microsecond=0)
        
        # Vérifier si cette heure (±fenêtre) existe dans le CSV
        is_in_csv = False
        closest_csv_time = None
        min_diff = timedelta(days=999)
        
        for csv_time_hour in csv_times:
            diff = abs(capture_hour - csv_time_hour)
            if diff <= time_window and diff < min_diff:
                is_in_csv = True
                closest_csv_time = csv_time_hour
                min_diff = diff
        
        if not is_in_csv:
            images_rejected += 1
            continue
        
        images_matched += 1
        
        # Trouver le niveau de marée exact
        tide_info = find_closest_tide(tide_data, capture_time, max_time_diff_minutes=time_window_hours * 60)
        
        # Extraire la couverture nuageuse
        cloud_cover = None
        for attr in product.get('Attributes', []):
            if attr.get('Name') == 'cloudCover':
                cloud_cover = attr.get('Value')
                break
        
        # Créer l'objet enrichi
        enriched = {
            'id': product['Id'],
            'name': product['Name'],
            'capture_date': product['ContentDate']['Start'],
            'capture_datetime': capture_time,
            'cloud_cover': cloud_cover,
            'size_mb': product.get('ContentLength', 0) / (1024 * 1024),
            'tide_level_m': tide_info['tide_level_m'] if tide_info else None,
            'tide_datetime': tide_info['tide_datetime'] if tide_info else None,
            'time_diff_minutes': tide_info['time_diff_minutes'] if tide_info else None
        }
        
        enriched_products.append(enriched)
    
    print(f"   ✓ Images correspondant aux dates CSV: {images_matched}")
    print(f"   ✗ Images rejetées (hors dates CSV): {images_rejected}")
    
    # Filtrer par paire de tuiles si demandé
    if filter_tile_pair:
        enriched_products = filter_by_tile_pair(enriched_products, required_tiles=filter_tile_pair)
    
    # Afficher les résultats
    print("\n" + "="*80)
    print("RÉSULTATS DÉTAILLÉS:")
    print("="*80)
    
    for i, enriched in enumerate(enriched_products, 1):
        print(f"\n{'─'*80}")
        print(f"IMAGE #{i}")
        print(f"  📅 Date capture: {enriched['capture_datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  📦 Nom: {enriched['name']}")
        
        if enriched['cloud_cover'] is not None:
            print(f"  ☁️  Nuages: {enriched['cloud_cover']:.1f}%")
        
        if enriched['tide_level_m'] is not None:
            print(f"  🌊 Niveau marée: {enriched['tide_level_m']:.3f} m")
            print(f"     Date marée: {enriched['tide_datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Différence: {enriched['time_diff_minutes']:.1f} minutes")
        else:
            print(f"  🌊 Niveau marée: Non disponible")
        
        print(f"  💾 Taille: {enriched['size_mb']:.0f} MB")
        print(f"  🆔 ID: {enriched['id']}")
    
    print("\n" + "="*80)
    
    return enriched_products


def search_sentinel2_with_tides_csv(username, password, start_date, end_date, 
                                    csv_file_path=None, max_cloud_cover=20, 
                                    max_tide_time_diff=60, date_column='A', tide_column='B',
                                    csv_delimiter=None, use_api=False, api_station_id="5cebf1e33d0f4a073c4bc285",
                                    use_both=False):
    """
    Rechercher des images Sentinel-2 et ajouter les données de marée depuis CSV et/ou API
    
    Args:
        username: Email Copernicus
        password: Mot de passe Copernicus
        start_date: Date de début (string YYYY-MM-DD ou YYYYMMDD)
        end_date: Date de fin (string YYYY-MM-DD ou YYYYMMDD)
        csv_file_path: Chemin vers le fichier CSV des marées (None si use_api=True uniquement)
        max_cloud_cover: Couverture nuageuse max en %
        max_tide_time_diff: Différence maximale entre image et marée (minutes)
        date_column: Colonne date dans le CSV (défaut: 'A')
        tide_column: Colonne marée dans le CSV (défaut: 'B')
        csv_delimiter: Séparateur CSV (None = auto, ',' ou ';' ou '\t')
        use_api: Si True, utilise l'API IWLS
        api_station_id: ID de la station pour l'API (défaut: Cap-aux-Meules)
        use_both: Si True, combine CSV + API (CSV prioritaire, API en complément)
    
    Returns:
        Liste des images avec leurs données de marée
    """
    print("\n" + "="*80)
    print("RECHERCHE IMAGES SENTINEL-2 + DONNÉES DE MARÉE - ÎLES DE LA MADELEINE")
    print("="*80)
    
    # Convertir les dates
    if len(start_date) == 8:
        start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    if len(end_date) == 8:
        end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    
    tide_start = datetime.strptime(start_date, '%Y-%m-%d')
    tide_end = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Charger les données de marée
    tide_data = []
    
    if use_both:
        print(f"Source des marées: API + CSV (API prioritaire)")
        
        # 1. Charger l'API d'abord (PRIORITAIRE)
        api_data = get_tide_data_from_api(api_station_id, tide_start, tide_end)
        if api_data:
            tide_data.extend(api_data)
            print(f"   ✓ API: {len(api_data)} enregistrements (PRIORITAIRE)")
        
        # 2. Compléter avec le CSV pour les dates non couvertes par l'API
        if csv_file_path:
            csv_data = load_tide_data_from_csv(csv_file_path, date_column, tide_column, 
                                               debug=False, delimiter=csv_delimiter)
            
            if csv_data:
                if api_data:
                    # Ne garder que les dates CSV non couvertes par l'API
                    api_dates = {d['datetime'].replace(second=0, microsecond=0) for d in api_data}
                    csv_data_filtered = [d for d in csv_data 
                                        if d['datetime'].replace(second=0, microsecond=0) not in api_dates]
                    tide_data.extend(csv_data_filtered)
                    print(f"   ✓ CSV: {len(csv_data_filtered)} enregistrements complémentaires")
                    print(f"   ℹ️  {len(csv_data) - len(csv_data_filtered)} enregistrement(s) CSV ignoré(s) (couverts par l'API)")
                else:
                    # Si l'API a échoué, utiliser tout le CSV
                    tide_data.extend(csv_data)
                    print(f"   ✓ CSV: {len(csv_data)} enregistrements (fallback)")
        
        # Trier par date
        tide_data.sort(key=lambda x: x['datetime'])
        print(f"   📊 TOTAL: {len(tide_data)} enregistrements combinés (API prioritaire)")
        
    elif use_api:
        print(f"Source des marées: API IWLS uniquement")
        tide_data = get_tide_data_from_api(api_station_id, tide_start, tide_end)
        
    else:
        print(f"Source des marées: CSV uniquement")
        if csv_file_path is None:
            print("❌ ERREUR: csv_file_path requis si use_api=False et use_both=False")
            return []
        tide_data = load_tide_data_from_csv(csv_file_path, date_column, tide_column, 
                                            debug=False, delimiter=csv_delimiter)
    
    if not tide_data:
        print("\n❌ Impossible de continuer sans données de marée")
        return []
    
    # Convertir les dates
    if len(start_date) == 8:
        start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    if len(end_date) == 8:
        end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    
    # Obtenir le token Copernicus
    print(f"\n🔐 Authentification Copernicus...")
    token = get_copernicus_token(username, password)
    print(f"   ✓ Token obtenu")
    
    # Paramètres de recherche Sentinel-2
    bbox = [-62.0, 47.2, -61.7, 47.5]  # Îles de la Madeleine
    
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    

    filter_query = (
        f"Collection/Name eq 'SENTINEL-2' and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(("
        f"{bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},"
        f"{bbox[2]} {bbox[3]},{bbox[0]} {bbox[3]},"
        f"{bbox[0]} {bbox[1]}))') and "
        f"ContentDate/Start gt {start_date}T00:00:00.000Z and "
        f"ContentDate/Start lt {end_date}T23:59:59.999Z and "
        f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {max_cloud_cover})"
        f"Attributes/OData.CSC.StringAttribute/any(att: att/Name eq 'tileID' and (att/Value eq '20TPT' or att/Value eq 'T20TNT' or att/Value eq 'T20TPT'))"
    )
    
    params = {
        "$filter": filter_query,
        "$orderby": "ContentDate/Start desc",
        "$top": 50,
        "$expand": "Attributes"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n📡 Recherche des images satellite...")
    response = requests.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    
    products = response.json().get('value', [])
    print(f"   ✓ {len(products)} image(s) trouvée(s)")
    
    # Enrichir chaque image avec les données de marée
    enriched_products = []
    images_with_tide = 0
    images_without_tide = 0
    
    print("\n" + "="*80)
    print("ASSOCIATION IMAGE ↔ MARÉE")
    print("="*80)
    
    for i, product in enumerate(products, 1):
        # Extraire l'heure de capture de l'image
        capture_time = datetime.fromisoformat(product['ContentDate']['Start'].replace('Z', '+00:00'))
        
        # Trouver le niveau de marée le plus proche
        tide_info = find_closest_tide(tide_data, capture_time, max_tide_time_diff)
        
        # Extraire la couverture nuageuse
        cloud_cover = None
        for attr in product.get('Attributes', []):
            if attr.get('Name') == 'cloudCover':
                cloud_cover = attr.get('Value')
                break
        
        # Créer l'objet enrichi
        enriched = {
            'id': product['Id'],
            'name': product['Name'],
            'capture_date': product['ContentDate']['Start'],
            'capture_datetime': capture_time,
            'cloud_cover': cloud_cover,
            'size_mb': product.get('ContentLength', 0) / (1024 * 1024)
        }
        
        # Ajouter les données de marée si disponibles
        if tide_info:
            enriched['tide_level_m'] = tide_info['tide_level_m']
            enriched['tide_datetime'] = tide_info['tide_datetime']
            enriched['time_diff_minutes'] = tide_info['time_diff_minutes']
            images_with_tide += 1
        else:
            enriched['tide_level_m'] = None
            enriched['tide_datetime'] = None
            enriched['time_diff_minutes'] = None
            images_without_tide += 1
        
        enriched_products.append(enriched)
    
    print(f"\n📊 Résultats:")
    print(f"   Images avec marée: {images_with_tide}")
    print(f"   Images sans marée: {images_without_tide} (différence > {max_tide_time_diff} min)")
    
    # Afficher les détails
    print("\n" + "="*80)
    print("RÉSULTATS DÉTAILLÉS:")
    print("="*80)
    
    for i, enriched in enumerate(enriched_products, 1):
        print(f"\n{'─'*80}")
        print(f"IMAGE #{i}")
        print(f"  📅 Date capture: {enriched['capture_datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  📦 Nom: {enriched['name']}")
        
        if enriched['cloud_cover'] is not None:
            print(f"  ☁️  Nuages: {enriched['cloud_cover']:.1f}%")
        
        if enriched['tide_level_m'] is not None:
            print(f"  🌊 Niveau marée: {enriched['tide_level_m']:.3f} m")
            print(f"     Date marée: {enriched['tide_datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Différence: {enriched['time_diff_minutes']:.1f} minutes")
        else:
            print(f"  🌊 Niveau marée: Non disponible (diff > {max_tide_time_diff} min)")
        
        print(f"  💾 Taille: {enriched['size_mb']:.0f} MB")
        print(f"  🆔 ID: {enriched['id']}")
    
    print("\n" + "="*80)
    
    return enriched_products


def download_sentinel2_product(product_id, token, output_path=None):
    """Télécharger une image Sentinel-2 complète"""
    if output_path is None:
        output_path = f"sentinel2_{product_id[:8]}.zip"
    
    url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n📥 TÉLÉCHARGEMENT IMAGE COMPLÈTE")
    print(f"{'─'*80}")
    print(f"ID: {product_id}")
    print(f"Destination: {output_path}")
    print(f"\n⚠️  ATTENTION: Les images Sentinel-2 font généralement 500-1000 MB")
    print(f"⏱️  Le téléchargement peut prendre plusieurs minutes...\n")
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r   ⏳ Progression: {progress:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='', flush=True)
        
        print(f"\n\n✅ IMAGE TÉLÉCHARGÉE AVEC SUCCÈS!")
        print(f"   📂 Fichier: {output_path}")
        print(f"   💾 Taille: {downloaded/(1024*1024):.1f} MB")
        return True
        
    except Exception as e:
        print(f"\n\n❌ ERREUR: {e}")
        return False


def download_quicklook(product_id, token, output_path=None):
    """Télécharger l'aperçu d'une image Sentinel-2"""
    if output_path is None:
        output_path = f"quicklook_{product_id[:8]}.jpg"
    
    print(f"\n🖼️  TÉLÉCHARGEMENT APERÇU (QUICKLOOK)")
    print(f"{'─'*80}")
    print(f"ID: {product_id}")
    print(f"Destination: {output_path}\n")
    
    try:
        info_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})?$expand=Attributes"
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(info_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        quicklook_url = None
        for attr in data.get('Attributes', []):
            if attr.get('Name') == 'quicklook':
                quicklook_url = attr.get('Value')
                break
        
        if not quicklook_url:
            print("❌ APERÇU NON DISPONIBLE")
            return False
        
        print(f"   ⏳ Téléchargement en cours...")
        ql_response = requests.get(quicklook_url, headers=headers, timeout=60)
        ql_response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(ql_response.content)
        
        size_mb = len(ql_response.content) / (1024 * 1024)
        
        print(f"\n✅ APERÇU TÉLÉCHARGÉ AVEC SUCCÈS!")
        print(f"   📂 Fichier: {output_path}")
        print(f"   💾 Taille: {size_mb:.2f} MB")
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        return False


def filter_by_tide_level(products, min_tide=None, max_tide=None, max_time_diff_minutes=60):
    """Filtrer les images par niveau de marée"""
    filtered = []
    
    for p in products:
        if p.get('tide_level_m') is None:
            continue
        
        if p.get('time_diff_minutes', 0) > max_time_diff_minutes:
            continue
        
        tide = p['tide_level_m']
        
        if min_tide is not None and tide < min_tide:
            continue
        
        if max_tide is not None and tide > max_tide:
            continue
        
        filtered.append(p)
    
    return filtered


def find_extreme_tides(products, max_time_diff_minutes=60):
    """Trouver les images à marée haute et basse"""
    valid_products = [p for p in products 
                     if p.get('tide_level_m') is not None 
                     and p.get('time_diff_minutes', 0) <= max_time_diff_minutes]
    
    if not valid_products:
        return {'high_tide': None, 'low_tide': None}
    
    high_tide = max(valid_products, key=lambda x: x['tide_level_m'])
    low_tide = min(valid_products, key=lambda x: x['tide_level_m'])
    
    return {'high_tide': high_tide, 'low_tide': low_tide}


def interactive_download_menu(products, username, password):
    """Menu interactif pour télécharger des images"""
    if not products:
        print("\n⚠️  Aucune image disponible")
        return
    
    print("\n" + "="*80)
    print("MENU DE TÉLÉCHARGEMENT")
    print("="*80)
    
    print(f"\n{len(products)} image(s) disponible(s)\n")
    
    for i, product in enumerate(products, 1):
        tide_str = f"{product.get('tide_level_m', 'N/A')}" if product.get('tide_level_m') else "N/A"
        if product.get('tide_level_m') is not None:
            tide_str = f"{product['tide_level_m']:.3f} m"
        
        cloud_str = f"{product.get('cloud_cover', 'N/A'):.1f}%" if product.get('cloud_cover') else "N/A"
        
        print(f"{i}. {product['capture_datetime'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Marée: {tide_str} | Nuages: {cloud_str}")
        print()
    
    print("="*80)
    print("\nOPTIONS:")
    print(f"  1-{len(products)}: Télécharger l'aperçu d'une image")
    print("  Q: Télécharger l'image complète")
    print("  H: Télécharger l'image à marée haute")
    print("  L: Télécharger l'image à marée basse")
    print("  A: Télécharger tous les aperçus")
    print("  X: Quitter")
    print("="*80)
    
    while True:
        choice = input("\nVotre choix: ").strip().upper()
        
        if choice == 'X':
            print("👋 Au revoir!")
            break
        
        elif choice in ['H', 'L']:
            extremes = find_extreme_tides(products)
            product = extremes['high_tide'] if choice == 'H' else extremes['low_tide']
            
            if product:
                tide_type = "HAUTE" if choice == 'H' else "BASSE"
                print(f"\n{'🔼' if choice == 'H' else '🔽'} IMAGE À MARÉE {tide_type} ({product['tide_level_m']:.3f} m)")
                print(f"   Date: {product['capture_datetime'].strftime('%Y-%m-%d %H:%M')}")
                
                dl_type = input("\n   Télécharger [Q]uicklook ou image [C]omplète? (Q/C): ").strip().upper()
                token = get_copernicus_token(username, password)
                
                fname_prefix = "high_tide" if choice == 'H' else "low_tide"
                if dl_type == 'C':
                    download_sentinel2_product(product['id'], token, 
                                             f"{fname_prefix}_{product['capture_datetime'].strftime('%Y%m%d')}.zip")
                else:
                    download_quicklook(product['id'], token, 
                                     f"{fname_prefix}_{product['capture_datetime'].strftime('%Y%m%d')}.jpg")
            else:
                print("❌ Aucune donnée disponible")
        
        elif choice == 'A':
            confirm = input(f"\n⚠️  Télécharger {len(products)} aperçu(s)? (O/N): ").strip().upper()
            if confirm == 'O':
                token = get_copernicus_token(username, password)
                success = 0
                
                for i, product in enumerate(products, 1):
                    print(f"\n[{i}/{len(products)}]")
                    fname = f"quicklook_{i}_{product['capture_datetime'].strftime('%Y%m%d_%H%M')}.jpg"
                    if download_quicklook(product['id'], token, fname):
                        success += 1
                
                print(f"\n✅ {success}/{len(products)} aperçu(s) téléchargé(s)!")
        
        elif choice == 'Q':
            try:
                num = int(input(f"\nNuméro (1-{len(products)}): "))
                if 1 <= num <= len(products):
                    product = products[num - 1]
                    confirm = input(f"\n⚠️  Fichier ~800 MB! Continuer? (O/N): ").strip().upper()
                    if confirm == 'O':
                        token = get_copernicus_token(username, password)
                        fname = f"sentinel2_full_{product['capture_datetime'].strftime('%Y%m%d_%H%M')}.zip"
                        download_sentinel2_product(product['id'], token, fname)
            except ValueError:
                print("❌ Numéro invalide")
        
        else:
            try:
                num = int(choice)
                if 1 <= num <= len(products):
                    product = products[num - 1]
                    token = get_copernicus_token(username, password)
                    fname = f"quicklook_{product['capture_datetime'].strftime('%Y%m%d_%H%M')}.jpg"
                    download_quicklook(product['id'], token, fname)
            except ValueError:
                print("❌ Commande non reconnue")


def select_best_pairs_per_year(products, required_tiles=['T20TNT', 'T20TPT']):
    """
    Pour chaque année, sélectionner la paire d'images avec la couverture nuageuse moyenne la plus faible
    
    Args:
        products: Liste des produits enrichis
        required_tiles: Liste des tuiles qui doivent être présentes ensemble
    
    Returns:
        Dict avec années comme clés et liste des images de la meilleure paire comme valeurs
    """
    from collections import defaultdict
    
    # Grouper par année et acquisition
    acquisitions_by_year = defaultdict(lambda: defaultdict(list))
    
    for product in products:
        # Extraire l'année
        year = product['capture_datetime'].year
        
        # Extraire les parties du nom du produit
        # Format: S2X_MSILXX_YYYYMMDDTHHMMSS_NXXXX_RXXX_TXXXXX_YYYYMMDDTHHMMSS.SAFE
        parts = product['name'].split('_')
        
        if len(parts) >= 6:
            satellite = parts[0]  # S2A ou S2B
            sensing_time = parts[2]  # Date/heure de capture
            processing_baseline = parts[3]  # N0510
            relative_orbit = parts[4]  # R125
            
            # Clé d'acquisition: ignorer le niveau de traitement et la tuile
            # Utiliser: satellite + sensing_time + baseline + orbit
            acq_key = f"{satellite}_{sensing_time}_{processing_baseline}_{relative_orbit}"
        else:
            # Fallback si le format est différent
            capture_key = product['capture_datetime'].strftime('%Y%m%d%H%M%S')
            satellite = product['name'][:3]
            acq_key = f"{satellite}_{capture_key}"
        
        acquisitions_by_year[year][acq_key].append(product)
    
    # Pour chaque année, trouver la meilleure paire
    best_pairs = {}
    
    print("\n" + "="*80)
    print("SÉLECTION DES MEILLEURES PAIRES PAR ANNÉE")
    print("="*80)
    
    for year in sorted(acquisitions_by_year.keys()):
        print(f"\n📅 ANNÉE {year}")
        print(f"{'─'*80}")
        
        acquisitions = acquisitions_by_year[year]
        valid_pairs = []
        
        # Filtrer pour ne garder que les paires complètes (exactement 1 TNT + 1 TPT)
        for acq_key, images in acquisitions.items():
            # Grouper par tuile et garder la meilleure image de chaque tuile (moins de nuages)
            tiles_dict = {}
            for img in images:
                try:
                    tile_code = img['name'].split('_')[5]
                    cloud = img.get('cloud_cover')
                    
                    # Si la tuile n'existe pas encore, ou si cette image a moins de nuages
                    if tile_code not in tiles_dict:
                        tiles_dict[tile_code] = img
                    elif cloud is not None:
                        existing_cloud = tiles_dict[tile_code].get('cloud_cover')
                        if existing_cloud is None or cloud < existing_cloud:
                            tiles_dict[tile_code] = img
                except (IndexError, KeyError):
                    continue
            
            # Vérifier qu'on a EXACTEMENT 1 TNT et 1 TPT (après déduplication)
            has_valid_pair = (
                'T20TNT' in tiles_dict and 
                'T20TPT' in tiles_dict and
                len(tiles_dict) == 2  # Pas d'autres tuiles
            )
            
            if has_valid_pair:
                # Récupérer les 2 images (une par tuile)
                tnt_img = tiles_dict['T20TNT']
                tpt_img = tiles_dict['T20TPT']
                
                # Calculer la couverture nuageuse moyenne
                cloud_tnt = tnt_img.get('cloud_cover')
                cloud_tpt = tpt_img.get('cloud_cover')
                
                if cloud_tnt is not None and cloud_tpt is not None:
                    avg_cloud = (cloud_tnt + cloud_tpt) / 2
                    valid_pairs.append({
                        'key': acq_key,
                        'images': [tnt_img, tpt_img],
                        'avg_cloud': avg_cloud,
                        'date': tnt_img['capture_datetime']
                    })
        
        if valid_pairs:
            # Trier par couverture nuageuse moyenne
            valid_pairs.sort(key=lambda x: x['avg_cloud'])
            
            # Sélectionner la meilleure
            best = valid_pairs[0]
            best_pairs[year] = best['images']
            
            print(f"   ✅ Meilleure paire trouvée (1 TNT + 1 TPT):")
            print(f"      Date: {best['date'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"      Couverture nuageuse moyenne: {best['avg_cloud']:.1f}%")
            
            # Détails des images de la paire
            for img in best['images']:
                tile = img['name'].split('_')[5]
                tide_str = f"{img['tide_level_m']:.3f} m" if img.get('tide_level_m') else "N/A"
                print(f"         • {tile}: Nuages {img.get('cloud_cover', 'N/A'):.1f}%, Marée {tide_str}")
            
            # Afficher les alternatives
            if len(valid_pairs) > 1:
                print(f"\n      ℹ️  Autres paires disponibles: {len(valid_pairs) - 1}")
                for i, pair in enumerate(valid_pairs[1:4], 1):  # Afficher max 3 alternatives
                    print(f"         {i}. {pair['date'].strftime('%Y-%m-%d')}: {pair['avg_cloud']:.1f}% nuages")
        else:
            print(f"   ⚠️  Aucune paire complète trouvée")
            best_pairs[year] = []
    
    print("\n" + "="*80)
    print(f"📊 RÉSUMÉ: {len([p for p in best_pairs.values() if p])} année(s) avec paires complètes")
    print("="*80)
    
    return best_pairs


def download_best_pairs(best_pairs, username, password, download_type='quicklook'):
    """
    Télécharger les meilleures paires sélectionnées
    
    Args:
        best_pairs: Dict retourné par select_best_pairs_per_year
        username: Email Copernicus
        password: Mot de passe Copernicus
        download_type: 'quicklook' ou 'full'
    """
    print("\n" + "="*80)
    print(f"📥 TÉLÉCHARGEMENT DES MEILLEURES PAIRES ({download_type.upper()})")
    print("="*80)
    
    total_images = sum(len(images) for images in best_pairs.values() if images)
    
    print(f"\nTotal d'images à télécharger: {total_images}")
    
    if download_type == 'full':
        size_estimate = total_images * 800  # MB
        print(f"⚠️  Taille estimée: ~{size_estimate} MB ({size_estimate/1024:.1f} GB)")
        confirm = input("\nContinuer? (O/N): ").strip().upper()
        if confirm != 'O':
            print("❌ Téléchargement annulé")
            return
    
    downloaded = 0
    failed = 0
    
    for year in sorted(best_pairs.keys()):
        images = best_pairs[year]
        if not images:
            continue
        
        print(f"\n{'─'*80}")
        print(f"📅 Année {year} - {len(images)} image(s)")
        print(f"{'─'*80}")
        
        for i, img in enumerate(images, 1):
            tile = img['name'].split('_')[5]
            date_str = img['capture_datetime'].strftime('%Y%m%d_%H%M')
            
            # Obtenir un nouveau token pour chaque image (évite l'expiration)
            try:
                token = get_copernicus_token(username, password)
            except Exception as e:
                print(f"\n❌ Erreur d'authentification: {e}")
                failed += 1
                continue
            
            if download_type == 'quicklook':
                filename = f"quicklook_{year}_{tile}_{date_str}.jpg"
                success = download_quicklook(img['id'], token, filename)
            else:
                filename = f"sentinel2_{year}_{tile}_{date_str}.zip"
                success = download_sentinel2_product(img['id'], token, filename)
            
            if success:
                downloaded += 1
            else:
                failed += 1
    
    print("\n" + "="*80)
    print(f"✅ Téléchargés: {downloaded}")
    if failed > 0:
        print(f"❌ Échecs: {failed}")
    print("="*80)


# ============================================================================
# PARTIE 3: API GOOGLE  - ENVOI DIRECT VERS GOOGLE DRIVE
# ============================================================================


def create_folder_if_not_exists(service, folder_name, parent_id=None):
    """
    Upload des images Sentinel-2 vers Google Drive organisées par année
    Nécessite: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
    Créer un dossier dans Google Drive s'il n'existe pas
    
    Args:
        service: Service Google Drive
        folder_name: Nom du dossier
        parent_id: ID du dossier parent (None = racine)
    
    Returns:
        ID du dossier
    """
    # Chercher si le dossier existe déjà
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    files = results.get('files', [])
    
    if files:
        print(f"   Dossier '{folder_name}' existe deja (ID: {files[0]['id']})")
        return files[0]['id']
    
    # Créer le dossier
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    print(f"   Dossier '{folder_name}' cree (ID: {folder.get('id')})")
    return folder.get('id')


def authenticate_google_drive(use_service_account=False, service_account_file='service_account.json'):
    """
    Authentifier avec Google Drive
    
    Args:
        use_service_account: Si True, utilise un compte de service (pas d'interaction)
        service_account_file: Chemin vers le fichier JSON du compte de service
    
    Méthode 1 - OAuth (utilisation personnelle):
    1. Aller sur https://console.cloud.google.com/
    2. Créer un projet
    3. Activer Google Drive API
    4. Créer des identifiants OAuth 2.0 (Desktop app)
    5. Télécharger le fichier credentials.json
    6. Ajouter votre email dans "Test users" (OAuth consent screen)
    
    Méthode 2 - Service Account (automatisation):
    1. APIs & Services → Credentials
    2. Create Credentials → Service Account
    3. Télécharger la clé JSON
    4. Renommer en service_account.json
    5. Partager le dossier Drive avec l'email du service account
    
    Returns:
        Service Google Drive authentifié
    """
    if use_service_account:
        # Utiliser un compte de service (pas d'interaction utilisateur)
        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    
    else:
        # Utiliser OAuth (interaction utilisateur nécessaire)
        creds = None
        
        # Le fichier token.pickle stocke les tokens d'accès
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # Si pas de credentials valides, demander l'authentification
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Sauvegarder les credentials
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)


def get_existing_files_in_drive(service, base_folder_id):
    """
    Récupérer la liste des fichiers existants dans Google Drive organisés par année
    
    Args:
        service: Service Google Drive
        base_folder_id: ID du dossier de base
    
    Returns:
        Dict {année: set(noms_fichiers)}
    """
    print("\n   Verification des fichiers existants dans Drive...")
    
    existing_files = {}
    
    try:
        # Lister les dossiers d'années
        query = f"'{base_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        year_folders = results.get('files', [])
        
        for folder in year_folders:
            try:
                year = int(folder['name'])
                folder_id = folder['id']
                
                # Lister les fichiers dans ce dossier
                query = f"'{folder_id}' in parents and trashed=false"
                files_result = service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(name)',
                    pageSize=1000
                ).execute()
                
                files = files_result.get('files', [])
                existing_files[year] = set(f['name'] for f in files)
                
                if files:
                    print(f"      Annee {year}: {len(files)} fichier(s)")
                
            except (ValueError, KeyError):
                continue
        
        total_files = sum(len(files) for files in existing_files.values())
        print(f"   Total fichiers existants: {total_files}")
        
    except Exception as e:
        print(f"   Erreur lors de la verification: {e}")
        print("   Continuera sans verification (peut creer des doublons)")
    
    return existing_files


def get_missing_images(year_images, existing_files_set):
    """
    Identifier les images manquantes pour une année
    
    Args:
        year_images: Liste des images pour cette année
        existing_files_set: Set des noms de fichiers existants
    
    Returns:
        Liste des images manquantes
    """
    missing = []
    
    for img in year_images:
        tile = img['name'].split('_')[5]
        date_str = img['capture_datetime'].strftime('%Y%m%d_%H%M')
        filename = f"sentinel2_{img['capture_datetime'].year}_{tile}_{date_str}.zip"
        
        if filename not in existing_files_set:
            missing.append(img)
    
    return missing


def get_present_tiles(year_images, existing_files_set):
    """
    Identifier quelles tuiles sont déjà présentes dans Drive
    
    Args:
        year_images: Liste des images pour cette année
        existing_files_set: Set des noms de fichiers existants
    
    Returns:
        Set des tuiles présentes
    """
    tiles_present = set()
    
    for img in year_images:
        tile = img['name'].split('_')[5]
        date_str = img['capture_datetime'].strftime('%Y%m%d_%H%M')
        filename = f"sentinel2_{img['capture_datetime'].year}_{tile}_{date_str}.zip"
        
        if filename in existing_files_set:
            tiles_present.add(tile)
    
    return tiles_present


def check_year_complete(year_images, existing_files_set, required_tiles=['T20TNT', 'T20TPT']):
    """
    Vérifier si une année a toutes ses tuiles dans Drive
    
    Args:
        year_images: Liste des images pour cette année
        existing_files_set: Set des noms de fichiers existants
        required_tiles: Tuiles requises
    
    Returns:
        Tuple (is_complete, missing_images)
    """
    missing = get_missing_images(year_images, existing_files_set)
    tiles_present = get_present_tiles(year_images, existing_files_set)
    is_complete = all(tile in tiles_present for tile in required_tiles)
    
    return is_complete, missing


def upload_stream_to_drive(service, file_stream, filename, folder_id, mime_type='application/zip'):
    """
    Uploader un flux de données vers Google Drive avec reprise en cas d'erreur
    
    Args:
        service: Service Google Drive
        file_stream: Flux de données (io.BytesIO)
        filename: Nom du fichier
        folder_id: ID du dossier de destination
        mime_type: Type MIME du fichier
    
    Returns:
        ID du fichier uploadé ou None si erreur
    """
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    # Taille du chunk augmentée pour les gros fichiers
    chunksize = 50*1024*1024  # 50 MB chunks
    
    media = MediaIoBaseUpload(
        file_stream,
        mimetype=mime_type,
        resumable=True,
        chunksize=chunksize
    )
    
    max_retries = 5
    retry_delay = 5  # secondes
    
    for attempt in range(max_retries):
        try:
            request = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            response = None
            last_progress = 0
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        if progress != last_progress:
                            print(f"\r      Upload Google Drive: {progress}%", end='', flush=True)
                            last_progress = progress
                except Exception as chunk_error:
                    # Erreur pendant un chunk, réessayer
                    if attempt < max_retries - 1:
                        print(f"\n      Erreur chunk: {chunk_error}")
                        print(f"      Nouvelle tentative dans {retry_delay}s...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Backoff exponentiel
                        break
                    else:
                        raise
            
            if response:
                print()  # Nouvelle ligne
                return response.get('id')
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"\n      Erreur tentative {attempt + 1}/{max_retries}: {e}")
                print(f"      Nouvelle tentative dans {retry_delay}s...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2
                # Remettre le curseur au début du flux
                file_stream.seek(0)
                # Recréer le media upload
                media = MediaIoBaseUpload(
                    file_stream,
                    mimetype=mime_type,
                    resumable=True,
                    chunksize=chunksize
                )
            else:
                print(f"\n      Erreur finale apres {max_retries} tentatives: {e}")
                return None
    
    return None


def download_and_upload_to_drive(product_id, token, year, tile, date_str, service, base_folder_id):
    """
    Télécharger une image Sentinel-2 et l'uploader directement vers Google Drive
    
    Args:
        product_id: ID du produit Sentinel-2
        token: Token Copernicus
        year: Année (pour l'organisation)
        tile: Code de la tuile (T20TNT ou T20TPT)
        date_str: Date formatée (YYYYMMDD_HHMM)
        service: Service Google Drive
        base_folder_id: ID du dossier de base
    
    Returns:
        True si succès, False sinon
    """
    filename = f"sentinel2_{year}_{tile}_{date_str}.zip"
    
    print(f"\n   Telechargement et upload: {filename}")
    print(f"   ID Produit: {product_id}")
    
    # Créer le dossier de l'année
    year_folder_id = create_folder_if_not_exists(service, str(year), base_folder_id)
    
    # URL de téléchargement
    url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Télécharger en streaming
        response = requests.get(url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        print(f"      Taille: {total_size/(1024*1024):.1f} MB")
        print(f"      Telechargement et upload en cours...")
        
        # Créer un buffer en mémoire
        file_stream = io.BytesIO()
        downloaded = 0
        
        # Télécharger chunk par chunk
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_stream.write(chunk)
                downloaded += len(chunk)
                
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\r      Progression: {progress:.1f}%", end='', flush=True)
        
        print()  # Nouvelle ligne après la progression
        
        # Remettre le curseur au début du flux
        file_stream.seek(0)
        
        # Uploader vers Google Drive
        print(f"      Upload vers Google Drive...")
        file_id = upload_stream_to_drive(
            service, 
            file_stream, 
            filename, 
            year_folder_id,
            mime_type='application/zip'
        )
        
        if file_id:
            print(f"      Succes! File ID: {file_id}")
            return True
        else:
            print(f"      Echec de l'upload")
            return False
        
    except Exception as e:
        print(f"\n      Erreur: {e}")
        return False


def upload_best_pairs_to_drive(best_pairs, username, password, base_folder_name='Sentinel-2', 
                              use_service_account=False, force_redownload=False):
    """
    Télécharger et uploader les meilleures paires vers Google Drive
    Vérifie ce qui existe déjà et ne télécharge que ce qui manque
    
    Args:
        best_pairs: Dict retourné par select_best_pairs_per_year
        username: Email Copernicus
        password: Mot de passe Copernicus
        base_folder_name: Nom du dossier de base dans Google Drive
        use_service_account: Si True, utilise un compte de service au lieu d'OAuth
        force_redownload: Si True, ignore les fichiers existants et retélécharge tout
    """
    print("\n" + "="*80)
    print("UPLOAD VERS GOOGLE DRIVE")
    print("="*80)
    
    # Authentifier avec Google Drive
    print("\nAuthentification Google Drive...")
    try:
        service = authenticate_google_drive(use_service_account=use_service_account)
        print("   Authentification reussie!")
    except Exception as e:
        print(f"   Erreur d'authentification: {e}")
        print("\nVeuillez verifier:")
        if use_service_account:
            print("1. Le fichier service_account.json existe")
            print("2. Le dossier Drive est partage avec l'email du service account")
        else:
            print("1. Le fichier credentials.json existe")
            print("2. L'API Google Drive est activee")
            print("3. Votre email est dans 'Test users' (OAuth consent screen)")
            print("4. Supprimez token.pickle et reessayez")
        return
    
    # Créer le dossier de base
    print(f"\nCreation du dossier de base '{base_folder_name}'...")
    base_folder_id = create_folder_if_not_exists(service, base_folder_name)
    
    # Vérifier les fichiers existants
    existing_files = {}
    if not force_redownload:
        existing_files = get_existing_files_in_drive(service, base_folder_id)
    
    # Analyser ce qui doit être téléchargé
    years_to_process = {}
    stats = {
        'complete': 0,
        'incomplete': 0,
        'missing': 0,
        'total_to_download': 0
    }
    
    print("\n" + "="*80)
    print("ANALYSE DES ANNEES")
    print("="*80)
    
    for year in sorted(best_pairs.keys()):
        images = best_pairs[year]
        if not images:
            continue
        
        existing_in_year = existing_files.get(year, set())
        is_complete, missing_images = check_year_complete(images, existing_in_year)
        
        print(f"\nAnnee {year}:")
        print(f"   Paire requise: {len(images)} image(s)")
        print(f"   Fichiers existants: {len(existing_in_year)}")
        
        if force_redownload:
            years_to_process[year] = images
            stats['total_to_download'] += len(images)
            print(f"   Status: FORCE REDOWNLOAD - {len(images)} image(s) a telecharger")
        elif is_complete:
            stats['complete'] += 1
            print(f"   Status: COMPLETE (paire complete presente)")
        elif existing_in_year and not is_complete:
            # Paire incomplète
            stats['incomplete'] += 1
            years_to_process[year] = missing_images
            stats['total_to_download'] += len(missing_images)
            tiles_missing = [img['name'].split('_')[5] for img in missing_images]
            print(f"   Status: INCOMPLETE - {len(missing_images)} image(s) manquante(s)")
            print(f"   Tuiles manquantes: {', '.join(tiles_missing)}")
        else:
            # Année complètement absente
            stats['missing'] += 1
            years_to_process[year] = images
            stats['total_to_download'] += len(images)
            print(f"   Status: ABSENTE - {len(images)} image(s) a telecharger")
    
    # Résumé
    print("\n" + "="*80)
    print("RESUME")
    print("="*80)
    print(f"Annees completes: {stats['complete']}")
    print(f"Annees incompletes: {stats['incomplete']}")
    print(f"Annees absentes: {stats['missing']}")
    print(f"Total images a telecharger: {stats['total_to_download']}")
    
    if stats['total_to_download'] == 0:
        print("\nTous les fichiers sont deja presents dans Google Drive!")
        print("Utilisez force_redownload=True pour forcer le re-telechargement")
        return
    
    size_estimate = stats['total_to_download'] * 800  # MB
    print(f"Taille estimee: ~{size_estimate} MB ({size_estimate/1024:.1f} GB)")
    
    confirm = input("\nContinuer le telechargement? (O/N): ").strip().upper()
    if confirm != 'O':
        print("Operation annulee")
        return
    
    # Télécharger et uploader
    uploaded = 0
    failed = 0
    skipped = 0
    
    for year in sorted(years_to_process.keys()):
        images = years_to_process[year]
        
        print(f"\n{'='*80}")
        print(f"ANNEE {year} - {len(images)} image(s) a traiter")
        print(f"{'='*80}")
        
        for i, img in enumerate(images, 1):
            tile = img['name'].split('_')[5]
            date_str = img['capture_datetime'].strftime('%Y%m%d_%H%M')
            filename = f"sentinel2_{year}_{tile}_{date_str}.zip"
            
            # Vérification finale (au cas où uploadé entre temps)
            if not force_redownload and filename in existing_files.get(year, set()):
                print(f"\n[{uploaded + failed + skipped + 1}/{stats['total_to_download']}] SKIP: {filename} (deja present)")
                skipped += 1
                continue
            
            print(f"\n[{uploaded + failed + skipped + 1}/{stats['total_to_download']}] Image {i}/{len(images)} de {year}")
            
            # Obtenir un nouveau token
            try:
                token = get_copernicus_token(username, password)
            except Exception as e:
                print(f"   Erreur d'authentification Copernicus: {e}")
                failed += 1
                continue
            
            # Télécharger et uploader
            success = download_and_upload_to_drive(
                img['id'], 
                token, 
                year, 
                tile, 
                date_str, 
                service, 
                base_folder_id
            )
            
            if success:
                uploaded += 1
                # Ajouter aux fichiers existants pour éviter les doublons
                if year not in existing_files:
                    existing_files[year] = set()
                existing_files[year].add(filename)
            else:
                failed += 1
    
    print("\n" + "="*80)
    print("RESUME FINAL")
    print("="*80)
    print(f"Uploads reussis: {uploaded}")
    print(f"Deja presents (skip): {skipped}")
    if failed > 0:
        print(f"Echecs: {failed}")
    print(f"\nDossier Google Drive: {base_folder_name}")
    print("="*80)



# ============================================================================
# EXEMPLE D'UTILISATION AVEC CREDENTIALS SÉCURISÉS
# ============================================================================

if __name__ == "__main__":
    # CHARGEMENT SÉCURISÉ DES CREDENTIALS
    try:
        creds = load_credentials("credentials.json")
        username = creds['copernicus']['username']
        password = creds['copernicus']['password']
        
        print(f"✅ Credentials chargés pour: {username}")
        
    except Exception as e:
        print(f"❌ Impossible de charger les credentials: {e}")
        exit(1)
    
    # Vos configurations habituelles
    csv_file = "marees.csv"
    max_cloud_cover = 20
    max_tide_time_diff = 60
    time_window_hours = 1
    
    # Le reste de votre code fonctionne normalement avec username/password
    # ...