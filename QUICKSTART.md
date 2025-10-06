# ⚡ Quick Start Guide

**NASA Space Apps Challenge 2025 - Interactive World Map**

---

## 🚀 Installation in 3 Minutes

### Option A: Automated Installation (Recommended)

```bash
# 1. Clone the project
git clone https://github.com/your-username/NASASpaceApp2025.git
cd NASASpaceApp2025

# 2. Make script executable
chmod +x setup.sh

# 3. Run installation
./setup.sh
```

The script will:
- ✅ Check Python and pip
- ✅ Install dependencies
- ✅ Create credentials.json
- ✅ Configure .gitignore
- ✅ Test configuration

---

### Option B: Manual Installation

```bash
# 1. Clone and install
git clone https://github.com/your-username/NASASpaceApp2025.git
cd NASASpaceApp2025
pip install -r requirements.txt

# 2. Configure credentials
cp credentials.json.example credentials.json
nano credentials.json  # Edit with your credentials

# 3. Verify configuration
python check_credentials.py
```

---

## 🔑 Credentials Configuration

### Step 1: Copernicus Account (Required)

1. **Create account**: https://dataspace.copernicus.eu/
2. **Activate account**: Check your email
3. **Edit `credentials.json`**:

```json
{
  "copernicus": {
    "username": "your_email@example.com",
    "password": "your_password"
  }
}
```

### Step 2: Google Drive (Optional)

Only if you want automated Drive upload.

1. **Google Cloud Console**: https://console.cloud.google.com/
2. **Create project** and enable Drive API
3. **Create OAuth 2.0 credentials** (type: Desktop app)
4. **Download JSON** and copy to `credentials.json`

See [SECURITY.md](SECURITY.md) for detailed guide.

---

## ✅ Verify Configuration

```bash
# Run verification script
python check_credentials.py
```

**Expected result:**
```
✅ All checks passed (6/6)
🚀 You can use the project safely!
```

**If errors appear:**
- ❌ Missing credentials → Edit `credentials.json`
- ❌ Tracked by Git → Run `git rm --cached credentials.json`
- ❌ API connection failed → Check username/password

---

## 🎯 Quick Usage

### 1. Interactive Map Interface

```bash
python src/main.py
```

**Features:**
- 🗺️ Interactive Folium map
- 📍 Custom markers
- 🌐 Opens in browser
- 💾 HTML export

### 2. Download Sentinel-2 Images

```bash
# Edit parameters in sentinelAPI.py (line ~1100)
python src/api/sentinelAPI.py
```

**Configuration:**
```python
csv_file = "marees.csv"           # Tidal data file
max_cloud_cover = 20              # Max cloud %
time_window_hours = 1             # Time window
filter_tile_pair = ['T20TNT', 'T20TPT']  # Required tiles
```

### 3. Filter Tidal Data

```python
from src.water_level_filter import WaterLevelFilter

# Load CSV
filter_obj = WaterLevelFilter("marees.csv")
filter_obj.load_csv_data()

# Filter by level (high tide > 1.5m)
high_tide = filter_obj.filter_by_level_range(1.5, 2.5)

# Export
filter_obj.export_filtered_data(high_tide, "high_tide.csv")
```

### 4. Calculate Surfaces (NDVI)

```bash
# 1. Prepare mosaics
python src/qgis/traitement_qgis.py

# 2. Calculate surfaces
python src/qgis/code_de_surface.py
```

---

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

### Workflow 3: Automated Drive Upload

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

---

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
threshold_value = 0.05            # ⬇️ = more sand
mean_min = 0.02                   # Anti-water filter (mean NDVI)

# Cleanup
min_object_pixels = 150           # Min object size (pixels)
min_area_m2 = 3000                # Min final polygon size (m²)

# CRS
TARGET_EPSG = 32198               # MTM-8/NAD83 (Magdalen Islands)
```

---

## 🆘 Quick Troubleshooting

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

# Check installation
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

---

## 📚 Documentation

| File | Description |
|------|-------------|
| [README.md](README.md) | Complete project documentation |
| [SECURITY.md](SECURITY.md) | Detailed security guide |
| [TIDE_FILTERING_GUIDE.md](TIDE_FILTERING_GUIDE.md) | Tidal filtering documentation |
| [check_credentials.py](check_credentials.py) | Verification script |
| [setup.sh](setup.sh) | Automated installation script |

---

## 🔒 Security Checklist

Before committing:

- [ ] `python check_credentials.py` → ✅ OK
- [ ] `git status` → credentials.json **absent**
- [ ] No hardcoded credentials in code
- [ ] .gitignore up to date

---

## 📞 Help

**Questions?** Open a [GitHub Issue](https://github.com/your-username/NASASpaceApp2025/issues)

**Security issue?** Contact privately (no public issue)

---

## 🎉 Ready!

You're now ready to use the project!

```bash
# Launch interface
python src/main.py

# Happy exploring! 🚀
```

---

**Last Updated**: October 2025  
**Version**: 1.0.0