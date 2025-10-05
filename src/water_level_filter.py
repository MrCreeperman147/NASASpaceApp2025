import csv
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class WaterLevelFilter:
    def __init__(self, csv_file_path: str):
        """Initialize the water level filter with CSV file path."""
        self.csv_file_path = csv_file_path
        self.data = None
        self.original_data = None  # Garde une copie des données originales
    
    def load_csv_data(self, delimiter=';', encoding='utf-8') -> bool:
        """Load water level data from CSV file."""
        try:
            # Essayer différents délimiteurs si celui spécifié ne fonctionne pas
            delimiters_to_try = [delimiter, ',', ';', '\t']
            
            for delim in delimiters_to_try:
                try:
                    # Lire le CSV
                    self.data = pd.read_csv(
                        self.csv_file_path, 
                        sep=delim,
                        encoding=encoding
                    )
                    
                    # Vérifier qu'on a au moins 2 colonnes
                    if len(self.data.columns) >= 2:
                        break
                except Exception:
                    continue
            
            if self.data is None or len(self.data.columns) < 2:
                print(f"Error: Unable to parse CSV with any delimiter")
                return False
            
            # Détecter les colonnes de date et de niveau d'eau
            date_col = None
            level_col = None
            
            # Chercher la colonne de date
            for col in self.data.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['date', 'time', 'datetime', 'temps']):
                    date_col = col
                    break
            
            # Si pas trouvé, utiliser la première colonne
            if date_col is None:
                date_col = self.data.columns[0]
            
            # Chercher la colonne de niveau d'eau
            for col in self.data.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['water', 'level', 'tide', 'marée', 'maree', 'niveau']):
                    level_col = col
                    break
            
            # Si pas trouvé, utiliser la deuxième colonne
            if level_col is None:
                level_col = self.data.columns[1]
            
            # Renommer les colonnes pour standardiser
            self.data = self.data.rename(columns={
                date_col: 'date',
                level_col: 'water_level'
            })
            
            # Garder seulement les colonnes nécessaires
            self.data = self.data[['date', 'water_level']].copy()
            
            # Convertir la colonne de date
            # Essayer différents formats
            date_formats = [
                '%d/%m/%Y %H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%d/%m/%Y %H:%M:%S',
                '%m/%d/%Y %H:%M',
                '%Y/%m/%d %H:%M',
                '%d-%m-%Y %H:%M',
            ]
            
            date_converted = False
            for fmt in date_formats:
                try:
                    self.data['date'] = pd.to_datetime(self.data['date'], format=fmt)
                    date_converted = True
                    break
                except Exception:
                    continue
            
            # Si aucun format ne fonctionne, essayer la détection automatique
            if not date_converted:
                try:
                    self.data['date'] = pd.to_datetime(self.data['date'])
                except Exception as e:
                    print(f"Error: Unable to parse dates - {e}")
                    return False
            
            # Convertir la colonne de niveau d'eau en numérique
            # Remplacer les virgules par des points si nécessaire
            if self.data['water_level'].dtype == 'object':
                self.data['water_level'] = self.data['water_level'].str.replace(',', '.')
            
            self.data['water_level'] = pd.to_numeric(self.data['water_level'], errors='coerce')
            
            # Supprimer les lignes avec des valeurs manquantes
            initial_count = len(self.data)
            self.data = self.data.dropna()
            removed_count = initial_count - len(self.data)
            
            if removed_count > 0:
                print(f"Warning: Removed {removed_count} rows with missing values")
            
            # Trier par date
            self.data = self.data.sort_values('date').reset_index(drop=True)
            
            # Sauvegarder une copie des données originales
            self.original_data = self.data.copy()
            
            print(f"Successfully loaded {len(self.data)} records from {self.csv_file_path}")
            print(f"Date range: {self.data['date'].min()} to {self.data['date'].max()}")
            print(f"Water level range: {self.data['water_level'].min():.2f} to {self.data['water_level'].max():.2f}")
            
            return True
            
        except FileNotFoundError:
            print(f"Error: File {self.csv_file_path} not found.")
            return False
        except Exception as e:
            print(f"Error loading CSV: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def filter_by_level_range(self, min_level: float, max_level: float) -> pd.DataFrame:
        """Filter data by water level range."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return pd.DataFrame()
        
        filtered_data = self.data[
            (self.data['water_level'] >= min_level) & 
            (self.data['water_level'] <= max_level)
        ].copy()
        
        print(f"Filtered to {len(filtered_data)} records within range {min_level}-{max_level}")
        return filtered_data
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Filter data by date range (YYYY-MM-DD format)."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return pd.DataFrame()
        
        # Convertir les dates string en datetime
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        filtered_data = self.data[
            (self.data['date'] >= start_dt) & 
            (self.data['date'] <= end_dt)
        ].copy()
        
        print(f"Filtered to {len(filtered_data)} records between {start_date} and {end_date}")
        return filtered_data
    
    def filter_by_hour_range(self, start_hour: int, end_hour: int) -> pd.DataFrame:
        """Filter data by hour of day (0-23)."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return pd.DataFrame()
        
        filtered_data = self.data[
            (self.data['date'].dt.hour >= start_hour) & 
            (self.data['date'].dt.hour <= end_hour)
        ].copy()
        
        print(f"Filtered to {len(filtered_data)} records between hours {start_hour}-{end_hour}")
        return filtered_data
    
    def get_statistics(self) -> Dict[str, float]:
        """Get basic statistics for water level data."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return {}
        
        stats = {
            'count': len(self.data),
            'mean': self.data['water_level'].mean(),
            'median': self.data['water_level'].median(),
            'min': self.data['water_level'].min(),
            'max': self.data['water_level'].max(),
            'std': self.data['water_level'].std()
        }
        return stats
    
    def get_daily_statistics(self) -> pd.DataFrame:
        """Get daily statistics grouped by date."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return pd.DataFrame()
        
        daily_stats = self.data.groupby(self.data['date'].dt.date)['water_level'].agg([
            'count', 'mean', 'min', 'max', 'std'
        ]).round(3)
        return daily_stats
    
    def export_filtered_data(self, filtered_data: pd.DataFrame, output_file: str):
        """Export filtered data to a new CSV file."""
        try:
            # Créer le dossier si nécessaire
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Formater les données pour l'export
            export_data = filtered_data.copy()
            
            # Formater la date selon le format original si possible
            # Par défaut, utiliser le format ISO
            export_data['date'] = export_data['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Formater le niveau d'eau avec 3 décimales
            export_data['water_level'] = export_data['water_level'].round(3)
            
            # Export avec séparateur point-virgule pour compatibilité Excel français
            export_data.to_csv(
                output_file, 
                index=False, 
                sep=';',
                encoding='utf-8-sig'  # UTF-8 avec BOM pour Excel
            )
            
            print(f"Filtered data exported to {output_file}")
            print(f"Total records exported: {len(export_data)}")
            
        except Exception as e:
            print(f"Error exporting data: {e}")
            raise
    
    def plot_water_levels(self, filtered_data=None):
        """Create a simple plot of water levels over time."""
        try:
            import matplotlib.pyplot as plt
            
            if self.data is None:
                print("No data loaded. Please load CSV first.")
                return
            
            # Utiliser les données filtrées si fournies, sinon toutes les données
            data_to_plot = filtered_data if filtered_data is not None else self.data
            
            if data_to_plot.empty:
                print("No data to plot.")
                return
            
            plt.figure(figsize=(14, 6))
            plt.plot(data_to_plot['date'], data_to_plot['water_level'], linewidth=0.8)
            plt.title('Niveaux de Marée - Îles de la Madeleine', fontsize=14, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Niveau de Marée (m)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Ajouter des statistiques sur le graphique
            stats = {
                'Moyenne': data_to_plot['water_level'].mean(),
                'Min': data_to_plot['water_level'].min(),
                'Max': data_to_plot['water_level'].max()
            }
            
            stats_text = '\n'.join([f'{k}: {v:.2f}m' for k, v in stats.items()])
            plt.text(
                0.02, 0.98, stats_text,
                transform=plt.gca().transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            )
            
            plt.show()
            
        except ImportError:
            print("Matplotlib not available. Install with: pip install matplotlib")
        except Exception as e:
            print(f"Error creating plot: {e}")
    
    def reset_to_original(self):
        """Reset data to original loaded state."""
        if self.original_data is not None:
            self.data = self.original_data.copy()
            print("Data reset to original state")
        else:
            print("No original data available")


# Example usage
if __name__ == "__main__":
    import sys
    
    # Vérifier si un fichier CSV est fourni en argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # Utiliser un fichier par défaut
        csv_file = "marees.csv"
    
    # Initialiser le filtre
    filter_obj = WaterLevelFilter(csv_file)
    
    # Charger les données
    if filter_obj.load_csv_data():
        print("\n" + "="*80)
        print("DONNÉES CHARGÉES AVEC SUCCÈS")
        print("="*80)
        
        # Afficher les statistiques
        stats = filter_obj.get_statistics()
        print("\n📊 Statistiques globales:")
        for key, value in stats.items():
            if key == 'count':
                print(f"  {key}: {int(value)}")
            else:
                print(f"  {key}: {value:.3f}")
        
        # Afficher les statistiques journalières (10 premiers jours)
        print("\n📅 Statistiques journalières (10 premiers jours):")
        daily_stats = filter_obj.get_daily_statistics()
        print(daily_stats.head(10))
        
        # Exemple de filtrage
        print("\n" + "="*80)
        print("EXEMPLE DE FILTRAGE")
        print("="*80)
        
        # Filtrer par niveau de marée
        print("\n🌊 Filtrage par niveau (marée haute > 1.0m):")
        high_tide = filter_obj.filter_by_level_range(1.0, 999)
        
        if not high_tide.empty:
            print(f"  Enregistrements trouvés: {len(high_tide)}")
            print(f"  Niveau moyen: {high_tide['water_level'].mean():.3f}m")
            
            # Exporter
            output_dir = Path("data/csv")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "high_tide_example.csv"
            filter_obj.export_filtered_data(high_tide, str(output_file))
            print(f"  ✅ Exporté vers: {output_file}")
        
        # Exemple de filtrage par date
        if len(filter_obj.data) > 0:
            # Prendre le premier mois de données
            start_date = filter_obj.data['date'].min()
            end_date = start_date + pd.Timedelta(days=30)
            
            print(f"\n📅 Filtrage par date (premier mois):")
            print(f"  Du: {start_date.strftime('%Y-%m-%d')}")
            print(f"  Au: {end_date.strftime('%Y-%m-%d')}")
            
            monthly_data = filter_obj.filter_by_date_range(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if not monthly_data.empty:
                print(f"  Enregistrements trouvés: {len(monthly_data)}")
                output_file = output_dir / "first_month_example.csv"
                filter_obj.export_filtered_data(monthly_data, str(output_file))
                print(f"  ✅ Exporté vers: {output_file}")
        
        print("\n" + "="*80)
        print("Pour utiliser avec l'interface graphique, lancez:")
        print("  python src/main.py")
        print("="*80)
    
    else:
        print("\n❌ Échec du chargement du fichier CSV")
        print(f"Fichier: {csv_file}")
        print("\nVérifiez que le fichier existe et est au bon format")