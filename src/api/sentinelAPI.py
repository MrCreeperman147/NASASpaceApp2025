"""
API Sentinel-2 et Données de Marée - Version Sécurisée
Credentials chargés depuis credentials.json
"""
import requests
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os
import pickle
import io

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


# [... Reste du code identique, juste modification de la fonction main ...]


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