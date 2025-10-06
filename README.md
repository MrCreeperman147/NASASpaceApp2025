# 🌍 NASA Space Apps Challenge 2025 - Magdalen Islands Coastal Analysis

An interactive mapping and geospatial analysis application for studying coastal erosion and environmental changes in the Magdalen Islands using Sentinel-2 satellite imagery and tidal data.

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Usage](#-usage)
- [Data Processing Pipeline](#-data-processing-pipeline)
- [Security](#-security)
- [Technologies](#-technologies)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Overview

This project provides a comprehensive toolset for analyzing coastal changes in the Magdalen Islands (Îles de la Madeleine), Quebec, Canada. It combines:

- **Sentinel-2 satellite imagery** from Copernicus Data Space
- **Tidal data analysis** for coastal monitoring
- **NDVI calculations** for vegetation and land surface detection
- **Interactive web mapping** with Folium
- **Automated processing pipeline** for multi-year analysis

### Objectives

- Monitor coastal erosion and land surface changes over time
- Correlate satellite observations with tidal patterns
- Generate comparative shapefiles showing temporal evolution
- Provide an intuitive interface for data exploration
- Enable data-driven decision making for coastal management

## ✨ Features

### 🗺️ Interactive Mapping

- **Multiple map styles**: Satellite (Esri), OpenStreetMap, CartoDB, Terrain
- **Custom markers**: Add points of interest with descriptions
- **Layer control**: Toggle between different data layers
- **Advanced tools**: Distance measurement, geolocation, fullscreen mode
- **Coordinate display**: Real-time cursor position tracking

### 🛰️ Sentinel-2 Data Processing

- **Automated download**: Fetch imagery from Copernicus Data Space
- **Cloud filtering**: Configurable cloud cover thresholds
- **Tidal synchronization**: Match images with specific tidal conditions
- **Multi-tile support**: Handle multiple Sentinel-2 tiles (T20TNT, T20TPT)
- **NDVI calculation**: Vegetation index for land/water separation

### 🌊 Tidal Data Analysis

- **CSV import**: Load tidal measurements from various formats
- **Date range filtering**: Select specific time periods
- **Water level filtering**: Isolate high/low tide events
- **Statistical analysis**: Mean, median, min/max, standard deviation
- **Daily summaries**: Aggregated statistics by day
- **Export functionality**: Save filtered datasets

### 📊 Shapefile Generation

- **Automated vectorization**: Convert NDVI rasters to polygons
- **Area calculation**: Precise surface measurements in km²
- **Temporal comparison**: Multi-year shapefiles with color gradients
- **Quality filtering**: Remove small artifacts and noise
- **CRS handling**: Automatic reprojection to WGS84

### 🚀 Complete Processing Pipeline

- **Google Drive integration**: Download archived imagery
- **Batch processing**: Handle multiple years automatically
- **Progress tracking**: Real-time status updates
- **Error handling**: Robust processing with detailed logs
- **Result validation**: Verify outputs at each step

## 🚀 Installation

### Prerequisites

- **Python 3.8+** (recommended: 3.10 or 3.11)
- **GDAL/PROJ** libraries (for geospatial processing)
- **Git** (for repository cloning)

### Option A: Automated Installation (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/NASASpaceApp2025.git
cd NASASpaceApp2025

# 2. Make setup script executable
chmod +x setup.sh

# 3. Run installation
./setup.sh
```

The script will:
- ✅ Check Python and pip versions
- ✅ Install all dependencies
- ✅ Create credentials.json template
- ✅ Configure .gitignore
- ✅ Test the configuration

### Option B: Manual Installation

```bash
# 1. Clone and navigate
git clone https://github.com/your-username/NASASpaceApp2025.git
cd NASASpaceApp2025

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp credentials.json.example credentials.json
nano credentials.json  # Edit with your credentials

# 4. Verify configuration
python check_credentials.py
```

### Installing GDAL (if needed)

**Windows:**
```bash
# Download pre-built wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
pip install GDAL‑3.x.x‑cpXX‑cpXX‑win_amd64.whl
```

**macOS:**
```bash
brew install gdal
pip install gdal
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install gdal-bin libgdal-dev
pip install gdal
```

**Conda (recommended for all platforms):**
```bash
conda install -c conda-forge gdal rasterio geopandas
```

## 🔑 Quick Start

### 1. Configure Credentials

#### Copernicus Account (Required)

1. Create account at https://dataspace.copernicus.eu/
2. Verify your email
3. Edit `credentials.json`:

```json
{
  "copernicus": {
    "username": "your_email@example.com",
    "password": "your_password"
  }
}
```

#### Google Drive API (Optional)

Only needed for automated upload to Drive.

1. Go to https://console.cloud.google.com/
2. Create a project and enable Drive API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download JSON and copy values to `credentials.json`

See [SECURITY.md](SECURITY.md) for detailed instructions.

### 2. Verify Configuration

```bash
python check_credentials.py
```

Expected output:
```
✅ All checks passed (6/6)
🚀 You can use the project safely!
```

### 3. Launch the Application

```bash
python src/main.py
```

This opens the interactive GUI with:
- 🗺️ Interactive Folium map
- 🌊 Tidal data filtering
- 🛰️ Sentinel-2 processing pipeline
- 📊 Shapefile visualization

## 📁 Project Structure

```
NASASpaceApp2025/
│
├── src/                          # Source code
│   ├── main.py                   # GUI application entry point
│   ├── gui_folium.py             # Folium mapping interface
│   ├── water_level_filter.py    # Tidal data filtering
│   ├── pipeline_processor.py    # Complete processing pipeline
│   ├── tiff_to_tiles.py         # TIFF conversion for web
│   │
│   ├── api/                      # API interactions
│   │   └── sentinelAPI.py        # Copernicus Sentinel-2 API
│   │
│   └── qgis/                     # Geospatial processing
│       ├── traitement_qgis.py    # Mosaic creation
│       └── code_de_surface.py    # NDVI & shapefile generation
│
├── data/                         # Data directory
│   ├── csv/                      # Tidal data CSVs
│   ├── image/                    # Reference images
│   ├── radar/                    # Radar imagery
│   ├── raw/                      # Downloaded Sentinel-2 data
│   └── processed/                # Processed TIFF files
│       └── YYYY-MM-DD/           # Date-organized folders
│           ├── B04_*.tif         # Red band
│           ├── B08_*.tif         # NIR band
│           └── NDVI_*.tif        # Calculated NDVI
│
├── output/                       # Generated outputs
│   └── shapefiles/               # Generated shapefiles
│       └── surface_YYYY.shp      # Annual surface polygons
│
├── static/                       # Web resources
│   └── tiffs/                    # PNG conversions for web
│
├── logs/                         # Application logs
│
├── credentials.json              # API credentials (gitignored)
├── credentials.json.example      # Credentials template
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
├── setup.sh                      # Automated setup script
├── check_credentials.py          # Security verification script
│
├── README.md                     # This file
├── QUICKSTART.md                 # Quick start guide
├── TIDE_FILTERING_GUIDE.md       # Tidal filtering documentation
└── SECURITY.md                   # Security best practices
```

## 💻 Usage

### Interactive Mapping

```bash
python src/main.py
```

**Features:**
- 🗺️ Interactive map centered on Magdalen Islands
- 📍 Add custom markers
- 🎨 Change map styles (satellite, terrain, etc.)
- 📏 Measure distances
- 🌐 Export to HTML

### Download Sentinel-2 Imagery

```bash
# Edit parameters in sentinelAPI.py (line ~1100)
python src/api/sentinelAPI.py
```

**Configuration:**
```python
csv_file = "marees.csv"                      # Tidal data file
max_cloud_cover = 20                         # Max cloud % (0-100)
time_window_hours = 1                        # Time window around tide
filter_tile_pair = ['T20TNT', 'T20TPT']     # Required tiles together
```

### Filter Tidal Data

```python
from src.water_level_filter import WaterLevelFilter

# Load CSV
filter_obj = WaterLevelFilter("marees.csv")
filter_obj.load_csv_data()

# Filter by water level (high tide > 1.5m)
high_tide = filter_obj.filter_by_level_range(1.5, 2.5)

# Export
filter_obj.export_filtered_data(high_tide, "high_tide.csv")
```

### Calculate Surfaces (NDVI)

```bash
# 1. Create mosaics
python src/qgis/traitement_qgis.py

# 2. Calculate surfaces
python src/qgis/code_de_surface.py
```

## 🔄 Data Processing Pipeline

### Complete Workflow

```bash
# Launch from GUI
python src/main.py
# Click "🛰️ Launch Complete Pipeline"
```

**Pipeline Steps:**

1. **Download** - Fetch images from Google Drive or Copernicus
2. **Mosaic** - Combine multiple tiles into single images
3. **NDVI** - Calculate vegetation index
4. **Vectorize** - Convert rasters to shapefiles
5. **Visualize** - Display on interactive map

### Manual Processing

```python
from src.pipeline_processor import PipelineProcessor

# Initialize
processor = PipelineProcessor()

# Process all years
results = processor.process_all_years()

# Process specific year
result = processor.process_year(2020)
```

## 🔒 Security

### Critical Security Rules

- ✅ **NEVER** commit `credentials.json` to Git
- ✅ **ALWAYS** use `credentials.json.example` as template
- ✅ **CHECK** with `python check_credentials.py` before committing
- ✅ **VERIFY** `.gitignore` includes sensitive files

### Security Checklist

Before committing:

- [ ] Run `python check_credentials.py` → ✅ OK
- [ ] Check `git status` → credentials.json **absent**
- [ ] No hardcoded credentials in code
- [ ] `.gitignore` is up to date

### Protected Files

```
credentials.json       # API credentials
token.pickle          # Google OAuth token
.env                  # Environment variables
*.pyc                 # Python cache
__pycache__/          # Python cache directories
```

See [SECURITY.md](SECURITY.md) for complete security guide.

## 🛠️ Technologies

### Core Technologies

- **Python 3.8+** - Main programming language
- **Folium** - Interactive web mapping
- **GeoPandas** - Geospatial data manipulation
- **Rasterio** - Raster data processing
- **GDAL** - Geospatial Data Abstraction Library

### Key Libraries

```
folium==0.20.0          # Interactive maps
geopandas==1.1.1        # Vector data processing
rasterio==1.4.3         # Raster I/O
pandas==2.3.3           # Data analysis
numpy==2.3.3            # Numerical computing
requests==2.32.5        # HTTP requests
scikit-image==0.25.2    # Image processing
matplotlib==3.10.6      # Plotting
```

### APIs Used

- **Copernicus Data Space** - Sentinel-2 imagery
- **Google Drive API** - Data storage (optional)

## 📊 Example Workflows

### Workflow 1: Coastal Erosion Analysis

```bash
# 1. Download images at extreme tides
python src/api/sentinelAPI.py

# 2. Create mosaics
python src/qgis/traitement_qgis.py

# 3. Calculate emerged surfaces
python src/qgis/code_de_surface.py

# 4. Visualize on map
python src/main.py
```

### Workflow 2: Image Selection for Study

```python
from src.api.sentinelAPI import (
    load_credentials,
    search_sentinel2_from_csv_dates,
    select_best_pairs_per_year,
    download_best_pairs
)

# Load credentials
creds = load_credentials()
username = creds['copernicus']['username']
password = creds['copernicus']['password']

# Search images
products = search_sentinel2_from_csv_dates(
    username, password,
    csv_file_path="marees.csv",
    max_cloud_cover=20,
    filter_tile_pair=['T20TNT', 'T20TPT']
)

# Select best pairs per year
best_pairs = select_best_pairs_per_year(products)

# Download quicklooks only
download_best_pairs(best_pairs, username, password, 'quicklook')
```

### Workflow 3: Automated Upload to Drive

```python
from src.api.sentinelAPI import (
    load_credentials,
    search_sentinel2_from_csv_dates,
    select_best_pairs_per_year,
    upload_best_pairs_to_drive
)

# Configuration and search
creds = load_credentials()
products = search_sentinel2_from_csv_dates(...)
best_pairs = select_best_pairs_per_year(products)

# Direct upload to Google Drive
upload_best_pairs_to_drive(
    best_pairs,
    username,
    password,
    base_folder_name='Sentinel2_MagdalenIslands'
)
```

## 🔧 Important Parameters

### sentinelAPI.py

```python
# Image search
max_cloud_cover = 20              # 0-100%
time_window_hours = 2             # Tide window ±hours
max_tide_time_diff = 60           # Max difference (minutes)

# Filtering
filter_tile_pair = ['T20TNT', 'T20TPT']  # Required tiles together
```

### code_de_surface.py

```python
# NDVI threshold (water/land)
threshold_value = 0.05            # ⬇️ = more sand detected
mean_min = 0.02                   # Anti-water filter (NDVI mean)

# Cleanup
min_object_pixels = 150           # Min object size (pixels)
min_area_m2 = 3000                # Min final polygon size (m²)

# CRS
TARGET_EPSG = 32198               # MTM-8/NAD83 (Magdalen Islands)
```

## 🆘 Troubleshooting

### ❌ "Copernicus authentication error"

```bash
# Check credentials
cat credentials.json | grep copernicus -A 3

# Test manually
python check_credentials.py
```

**Solutions:**
- Verify username/password
- Ensure account is activated
- Try logging in on website

### ❌ "credentials.json not found"

```bash
# Check existence
ls -la credentials.json

# Create from template
cp credentials.json.example credentials.json
nano credentials.json
```

### ❌ "Module not found"

```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Verify installation
pip list | grep rasterio
pip list | grep geopandas
```

### ❌ "GDAL/PROJ errors"

```bash
# With conda (recommended)
conda install -c conda-forge gdal rasterio geopandas

# Verify paths
python -c "import rasterio; print(rasterio.__version__)"
```

### ❌ "Git tracking credentials.json"

```bash
# Remove from tracking
git rm --cached credentials.json
git commit -m "Remove credentials from tracking"

# Verify
git status | grep credentials
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add docstrings to functions
- Update documentation for new features
- Test before submitting
- Never commit credentials

## 📄 License

This project is part of the NASA Space Apps Challenge 2025.

## 📞 Support

**Questions?** Open a [GitHub Issue](https://github.com/your-username/NASASpaceApp2025/issues)

**Security concerns?** Contact privately (no public issues)

## 🙏 Acknowledgments

- **NASA Space Apps Challenge** - Challenge organizers and informations source
- **Copernicus Programme** - Sentinel-2 data
- **ESA** - Earth observation data
- **Folium** - Interactive mapping library
- **GDAL/OGR** - Geospatial tools

**EXPLORER_J1K2R1**
- Louisa Bekaddour - bekl4494@usherbrooke.ca
- Basile-Vladimir Fauconnier - bvfauconnier@gmail.com
- Guilhem Calas - guilhem.calas@usherbrooke.ca
- Bright Ogbeiwi - brightogbeiwi@gmail.com
- Meriem Sarra Tairi - tairisarra27@gmail.com
- Nathan Lunel - nathanhugo.lunel@gmail.com

---

**Last Updated**: October 2025  
**Version**: 1.0.0  
**Location**: Magdalen Islands, Quebec, Canada 🇨🇦