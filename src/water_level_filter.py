import csv
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

class WaterLevelFilter:
    def __init__(self, csv_file_path: str):
        """Initialize the water level filter with CSV file path."""
        self.csv_file_path = csv_file_path
        self.data = None
    
    def load_csv_data(self) -> bool:
        """Load water level data from CSV file."""
        try:
            # Use semicolon as delimiter for this specific CSV format
            self.data = pd.read_csv(self.csv_file_path, sep=';')
            
            # Convert date column to datetime with the specific format
            if 'date' in self.data.columns:
                self.data['date'] = pd.to_datetime(self.data['date'], format='%d/%m/%Y %H:%M')
            
            print(f"Successfully loaded {len(self.data)} records from {self.csv_file_path}")
            print(f"Date range: {self.data['date'].min()} to {self.data['date'].max()}")
            print(f"Water level range: {self.data['water_level'].min():.2f} to {self.data['water_level'].max():.2f}")
            return True
        except FileNotFoundError:
            print(f"Error: File {self.csv_file_path} not found.")
            return False
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return False
    
    def filter_by_level_range(self, min_level: float, max_level: float) -> pd.DataFrame:
        """Filter data by water level range."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return pd.DataFrame()
        
        filtered_data = self.data[
            (self.data['water_level'] >= min_level) & 
            (self.data['water_level'] <= max_level)
        ]
        print(f"Filtered to {len(filtered_data)} records within range {min_level}-{max_level}")
        return filtered_data
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Filter data by date range (YYYY-MM-DD format)."""
        if self.data is None:
            print("No data loaded. Please load CSV first.")
            return pd.DataFrame()
        
        filtered_data = self.data[
            (self.data['date'] >= start_date) & 
            (self.data['date'] <= end_date)
        ]
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
        ]
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
            # Export with semicolon delimiter to match original format
            filtered_data.to_csv(output_file, index=False, sep=';', 
                               date_format='%d/%m/%Y %H:%M')
            print(f"Filtered data exported to {output_file}")
        except Exception as e:
            print(f"Error exporting data: {e}")
    
    def plot_water_levels(self):
        """Create a simple plot of water levels over time."""
        try:
            import matplotlib.pyplot as plt
            
            if self.data is None:
                print("No data loaded. Please load CSV first.")
                return
            
            plt.figure(figsize=(12, 6))
            plt.plot(self.data['date'], self.data['water_level'])
            plt.title('Water Levels Over Time')
            plt.xlabel('Date')
            plt.ylabel('Water Level (m)')
            plt.xticks(rotation=45)
            plt.grid(True)
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("Matplotlib not available. Install with: pip install matplotlib")
        except Exception as e:
            print(f"Error creating plot: {e}")

# Example usage
if __name__ == "__main__":
    # Initialize the filter with the specific CSV file
    filter_obj = WaterLevelFilter("1970-01-JAN-2016_slev.csv")
    
    # Load data
    if filter_obj.load_csv_data():
        # Get statistics
        stats = filter_obj.get_statistics()
        print("\nWater Level Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value:.3f}")
        
        # Get daily statistics
        print("\nDaily Statistics:")
        daily_stats = filter_obj.get_daily_statistics()
        print(daily_stats.head())
        
        # Filter by level range (more realistic range for this data)
        filtered_data = filter_obj.filter_by_level_range(-0.90, 0.476)
        
        # Filter by hour range (e.g., morning hours)
        morning_data = filter_obj.filter_by_hour_range(6, 12)
        
        # Export filtered data
        if not filtered_data.empty:
            filter_obj.export_filtered_data(filtered_data, "filtered_water_levels.csv")
        
        if not morning_data.empty:
            filter_obj.export_filtered_data(morning_data, "morning_water_levels.csv")
        
        # Uncomment to create a plot
        # filter_obj.plot_water_levels()