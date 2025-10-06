# 🌊 Tidal Data Filtering Guide

## 📋 Overview

This functionality allows you to filter tidal data according to multiple criteria and export results to CSV files.

---

## 🚀 Using the Graphical Interface

### 1. Launch the Application

```bash
python src/main.py
```

### 2. "Tidal Data Filtering" Section

The interface contains a dedicated section with the following elements:

#### 📁 **CSV Import**
- Click **"📁 Import CSV"**
- Select your tidal data file
- File must contain at minimum:
  - A **date/time** column
  - A **water level** column (in meters)

#### 📅 **Date Filters**
- **Start date**: Beginning of period (format: YYYY-MM-DD)
- **End date**: End of period (format: YYYY-MM-DD)
- These fields are auto-populated with min/max values from CSV

#### 🌊 **Level Filters**
- **Min level (m)**: Minimum water level to include
- **Max level (m)**: Maximum water level to include
- These fields are auto-populated with min/max values from CSV

#### 🔘 **Action Buttons**
- **🔍 Filter Data**: Apply filters and export result
- **📊 View Statistics**: Display detailed statistics
- **🗑️ Reset**: Reset filters to default values

---

## 📊 Detailed Features

### CSV Import

**Accepted formats:**
- Separators: `;` (semicolon), `,` (comma), `\t` (tab)
- Encoding: UTF-8, UTF-8-sig
- Date formats:
  - `DD/MM/YYYY HH:MM`
  - `YYYY-MM-DD HH:MM:SS`
  - `DD/MM/YYYY HH:MM:SS`
  - Other common formats (automatic detection)

**Required columns:**
The script automatically detects columns containing:
- Date/time: looks for "date", "time", "datetime", "temps"
- Level: looks for "water", "level", "tide", "marée", "niveau"

**Example valid CSV:**
```csv
date;water_level
01/01/2020 00:00;0.856
01/01/2020 01:00;1.234
01/01/2020 02:00;1.567
```

### Filtering

**Steps:**
1. Import your CSV
2. Fields are pre-filled with:
   - Dates: first and last date from file
   - Levels: minimum and maximum level from file
3. Modify values according to your needs
4. Click "🔍 Filter Data"

**Result:**
- File exported to: `data/csv/filtered_tides_YYYYMMDD_HHMMSS.csv`
- Display of filtering statistics
- Option to open output folder

### Statistics

Click **"📊 View Statistics"** to display:

#### Global Statistics
- Number of records
- Mean level
- Median level
- Minimum level
- Maximum level
- Standard deviation
- Total amplitude

#### Covered Period
- Start date
- End date
- Duration in days

#### Daily Statistics
- Per day: count, mean, min, max, standard deviation
- Display of first 10 days

---