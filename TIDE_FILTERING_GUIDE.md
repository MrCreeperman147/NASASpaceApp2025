# 🌊 Guide de Filtrage des Données de Marée

## 📋 Vue d'ensemble

Cette fonctionnalité permet de filtrer les données de marée selon plusieurs critères et d'exporter les résultats dans des fichiers CSV.

---

## 🚀 Utilisation avec l'Interface Graphique

### 1. Lancer l'Application

```bash
python src/main.py
```

### 2. Section "Filtrage des Données de Marée"

L'interface contient une section dédiée avec les éléments suivants :

#### 📁 **Import du CSV**
- Cliquez sur **"📁 Importer CSV"**
- Sélectionnez votre fichier de données de marée
- Le fichier doit contenir au minimum :
  - Une colonne de **date/heure**
  - Une colonne de **niveau de marée** (en mètres)

#### 📅 **Filtres de Date**
- **Date début** : Date de début de la période (format: YYYY-MM-DD)
- **Date fin** : Date de fin de la période (format: YYYY-MM-DD)
- Ces champs sont pré-remplis automatiquement avec les valeurs min/max du CSV

#### 🌊 **Filtres de Niveau**
- **Niveau min (m)** : Niveau de marée minimum à inclure
- **Niveau max (m)** : Niveau de marée maximum à inclure
- Ces champs sont pré-remplis avec les valeurs min/max du CSV

#### 🔘 **Boutons d'Action**
- **🔍 Filtrer Données** : Applique les filtres et exporte le résultat
- **📊 Voir Statistiques** : Affiche les statistiques détaillées
- **🗑️ Réinitialiser** : Réinitialise les filtres aux valeurs par défaut

---

## 📊 Fonctionnalités Détaillées

### Import CSV

**Formats acceptés :**
- Séparateurs : `;` (point-virgule), `,` (virgule), `\t` (tabulation)
- Encodage : UTF-8, UTF-8-sig
- Formats de date :
  - `DD/MM/YYYY HH:MM`
  - `YYYY-MM-DD HH:MM:SS`
  - `DD/MM/YYYY HH:MM:SS`
  - Autres formats courants (détection automatique)

**Colonnes requises :**
Le script détecte automatiquement les colonnes contenant :
- Date/heure : cherche "date", "time", "datetime", "temps"
- Niveau : cherche "water", "level", "tide", "marée", "niveau"

**Exemple de CSV valide :**
```csv
date;water_level
01/01/2020 00:00;0.856
01/01/2020 01:00;1.234
01/01/2020 02:00;1.567
```

### Filtrage

**Étapes :**
1. Importez votre CSV
2. Les champs sont pré-remplis avec :
   - Dates : première et dernière date du fichier
   - Niveaux : niveau minimum et maximum du fichier
3. Modifiez les valeurs selon vos besoins
4. Cliquez sur "🔍 Filtrer Données"

**Résultat :**
- Fichier exporté dans : `data/csv/filtered_tides_YYYYMMDD_HHMMSS.csv`
- Affichage des statistiques du filtrage
- Option d'ouvrir le dossier de sortie

### Statistiques

Cliquez sur **"📊 Voir Statistiques"** pour afficher :

#### Statistiques Globales
- Nombre d'enregistrements
- Niveau moyen
- Niveau médian
- Niveau minimum
- Niveau maximum
- Écart-type
- Amplitude totale

#### Période Couverte
- Date de début
- Date de fin
- Durée en jours

#### Statistiques Journalières
- Par jour : nombre, moyenne, min, max, écart-type
- Affichage des 10 premiers jours

---

## 💻 Utilisation en Ligne de Commande

### Script Autonome

```bash
# Avec un fichier spécifique
python src/water_level_filter.py marees.csv

# Avec le fichier par défaut (marees.csv)
python src/water_level_filter.py
```

### Utilisation Programmatique

```python
from water_level_filter import WaterLevelFilter

# Initialiser
filter_obj = WaterLevelFilter("marees.csv")

# Charger les données
if filter_obj.load_csv_data():
    # Obtenir les statistiques
    stats = filter_obj.get_statistics()
    print(f"Moyenne: {stats['mean']:.3f}m")
    
    # Filtrer par date
    filtered = filter_obj.filter_by_date_range('2020-01-01', '2020-12-31')
    
    # Filtrer par niveau
    high_tide = filter_obj.filter_by_level_range(1.5, 2.5)
    
    # Exporter
    filter_obj.export_filtered_data(high_tide, 'data/csv/output.csv')
```

---

## 📁 Structure des Fichiers de Sortie

### Emplacement
```
data/
└── csv/
    ├── filtered_tides_20250101_120000.csv
    ├── filtered_tides_20250102_153045.csv
    └── ...
```

### Format du Fichier Exporté

```csv
date;water_level
2020-01-01 00:00:00;0.856
2020-01-01 01:00:00;1.234
2020-01-01 02:00:00;1.567
```

**Caractéristiques :**
- Séparateur : `;` (point-virgule)
- Encodage : UTF-8 avec BOM (compatible Excel)
- Date : format ISO `YYYY-MM-DD HH:MM:SS`
- Niveau : 3 décimales

---

## 🎯 Cas d'Usage Typiques

### 1. Sélectionner les Marées Hautes

**Objectif :** Trouver tous les moments où la marée dépasse 1.5m

**Paramètres :**
- Date début : (première date du CSV)
- Date fin : (dernière date du CSV)
- Niveau min : `1.5`
- Niveau max : `999` (ou valeur max du CSV)

### 2. Analyser une Période Spécifique

**Objectif :** Étudier les marées de l'été 2020

**Paramètres :**
- Date début : `2020-06-01`
- Date fin : `2020-08-31`
- Niveau min : (min du CSV)
- Niveau max : (max du CSV)

### 3. Marées Extrêmes

**Objectif :** Identifier les marées très hautes et très basses

**Pour marée haute :**
- Niveau min : `1.8`
- Niveau max : `999`

**Pour marée basse :**
- Niveau min : `-999`
- Niveau max : `0.2`

### 4. Plage de Marée Spécifique

**Objectif :** Sélectionner les marées moyennes

**Paramètres :**
- Niveau min : `0.8`
- Niveau max : `1.4`

---

## 🔧 Dépannage

### ❌ "Impossible de charger le fichier CSV"

**Solutions :**
1. Vérifier que le fichier existe
2. Vérifier le format du fichier (doit être .csv)
3. Vérifier que le fichier contient au moins 2 colonnes
4. Essayer d'ouvrir le fichier dans un éditeur de texte pour voir le séparateur

### ❌ "Format de date invalide"

**Solutions :**
1. Utiliser le format `YYYY-MM-DD` (ex: 2020-12-31)
2. Ne pas mettre d'heure, juste la date
3. Vérifier qu'il n'y a pas d'espaces avant/après

### ❌ "Aucune donnée trouvée"

**Causes possibles :**
1. Les dates sont hors de la plage du CSV
2. Les niveaux sont hors de la plage du CSV
3. Vérifier les valeurs min/max avec "📊 Voir Statistiques"

### ❌ "Valeur invalide"

**Solutions :**
1. Utiliser le point `.` comme séparateur décimal (pas la virgule)
2. Ne pas mettre d'unités (ex: `1.5` pas `1.5m`)
3. Vérifier que les champs ne sont pas vides

---

## 📈 Exemple Complet

### Données d'Entrée (marees.csv)

```csv
date;water_level
01/01/2020 00:00;0.856
01/01/2020 01:00;1.234
01/01/2020 02:00;1.567
01/01/2020 03:00;1.823
01/01/2020 04:00;1.956
01/01/2020 05:00;1.823
01/01/2020 06:00;1.567
```

### Workflow

1. **Import**
   - Cliquer "📁 Importer CSV"
   - Sélectionner `marees.csv`
   - Message : "✅ CSV chargé: marees.csv - 7 enregistrements"

2. **Configuration des Filtres**
   - Date début : `2020-01-01`
   - Date fin : `2020-01-01`
   - Niveau min : `1.5`
   - Niveau max : `2.0`

3. **Filtrage**
   - Cliquer "🔍 Filtrer Données"
   - Message : "✅ Filtrage terminé: 4 enregistrements"

4. **Résultat (filtered_tides_20250101_120000.csv)**

```csv
date;water_level
2020-01-01 02:00:00;1.567
2020-01-01 03:00:00;1.823
2020-01-01 04:00:00;1.956
2020-01-01 05:00:00;1.823
```

---

## 🆘 Support

Pour toute question ou problème :
1. Consulter ce guide
2. Vérifier les messages d'erreur dans l'interface
3. Ouvrir une issue GitHub

---

**Version** : 1.0.0  
**Dernière mise à jour** : Octobre 2025