"""
Interface graphique pour carte Folium interactive - NASASpaceApp2025
Vue satellitaire centrée sur les Îles de la Madeleine
Avec filtrage des données de marée et affichage des shapefiles
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import folium
from folium import plugins
import webbrowser
import tempfile
import os
from pathlib import Path
import json
from datetime import datetime
import sys
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import threading
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Importer le filtre de marée et le pipeline
sys.path.insert(0, str(Path(__file__).parent))
try:
    from water_level_filter import WaterLevelFilter
    from pipeline_processor import PipelineProcessor
    PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Pipeline non disponible - {e}")
    WaterLevelFilter = None
    PipelineProcessor = None
    PIPELINE_AVAILABLE = False


class FoliumMapGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NASA Space App 2025 - Îles de la Madeleine")
        self.root.geometry("1400x900")
        
        # Coordonnées des Îles de la Madeleine
        self.ILES_MADELEINE_LAT = 47.40
        self.ILES_MADELEINE_LON = -61.85
        
        # Variables
        self.current_lat = self.ILES_MADELEINE_LAT
        self.current_lon = self.ILES_MADELEINE_LON
        self.zoom_level = 11  # Zoom approprié pour voir l'archipel
        
        # Liste vide pour les marqueurs personnalisés
        self.locations = []
        
        # Variables pour le filtrage des marées
        self.csv_file_path = None
        self.tide_filter = None
        
        # Fichier de carte temporaire
        self.temp_map_file = None
        self.map_object = None
        
        # Initialiser le dictionnaire des shapefiles
        self.shapefiles = {}
        # Dictionnaire pour stocker les TIFF NDVI par date
        self.tiff_data = {}
        # Variable pour stocker la date sélectionnée
        self.selected_tiff_date = None

        # Variables pour les widgets et couleurs
        self.shapefile_start_color = "#0000FF"  # Bleu par défaut
        self.shapefile_end_color = "#FF0000"    # Rouge par défaut
        
        # Dossiers pour les images et données radar
        self.images_dir = Path("data/image")
        self.radar_dir = Path("data/radar")
        
        # Créer les dossiers s'ils n'existent pas
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.radar_dir.mkdir(parents=True, exist_ok=True)

        # Initialiser le PipelineProcessor si disponible
        if PIPELINE_AVAILABLE and PipelineProcessor:
            try:
                self.PipelineProcessor = PipelineProcessor()
                print("✅ Pipeline processor initialisé")
            except Exception as e:
                self.PipelineProcessor = None
                print(f"⚠️ Erreur initialisation pipeline: {e}")
        else:
            self.PipelineProcessor = None
        
        self.setup_gui()

        # Charger les shapefiles existants
        print("🔍 Chargement des shapefiles...")
        self.load_existing_shapefiles()
        print(f"📊 Shapefiles chargés: {list(self.shapefiles.keys())}")

        self.create_folium_map()

        # Charger les shapefiles existants (after GUI setup for update_info)
        self.load_existing_shapefiles()
        
        self.create_folium_map()

        # Créer le dossier static pour les PNG
        static_dir = Path("static/tiffs")
        static_dir.mkdir(parents=True, exist_ok=True)

    
    def setup_gui(self):
        """Configure l'interface graphique"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration des poids
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Frame de contrôles
        control_frame = ttk.LabelFrame(main_frame, text="Contrôles - Îles de la Madeleine", padding="5")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Coordonnées et contrôles
        coord_frame = ttk.Frame(control_frame)
        coord_frame.grid(row=0, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(coord_frame, text="Centre:").grid(row=0, column=0, padx=(0, 5))
        ttk.Label(coord_frame, text="Lat:").grid(row=0, column=1, padx=(0, 2))
        self.lat_var = tk.StringVar(value=str(self.ILES_MADELEINE_LAT))
        self.lat_entry = ttk.Entry(coord_frame, textvariable=self.lat_var, width=8)
        self.lat_entry.grid(row=0, column=2, padx=(0, 10))
        
        ttk.Label(coord_frame, text="Lon:").grid(row=0, column=3, padx=(0, 2))
        self.lon_var = tk.StringVar(value=str(self.ILES_MADELEINE_LON))
        self.lon_entry = ttk.Entry(coord_frame, textvariable=self.lon_var, width=8)
        self.lon_entry.grid(row=0, column=4, padx=(0, 10))
        
        ttk.Label(coord_frame, text="Zoom:").grid(row=0, column=5, padx=(0, 2))
        self.zoom_var = tk.StringVar(value=str(self.zoom_level))
        self.zoom_spinbox = ttk.Spinbox(coord_frame, textvariable=self.zoom_var, 
                                       from_=8, to=18, width=5)
        self.zoom_spinbox.grid(row=0, column=6, padx=(0, 10))
        
        # Boutons de contrôle
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=0, columnspan=6, pady=(10, 0))
        
        ttk.Button(btn_frame, text="🗺️ Générer Carte", 
                  command=self.create_folium_map).grid(row=0, column=0, padx=2)
        
        ttk.Button(btn_frame, text="🌐 Ouvrir dans Navigateur", 
                  command=self.open_in_browser).grid(row=0, column=1, padx=2)
        
        ttk.Button(btn_frame, text="💾 Sauvegarder", 
                  command=self.save_map).grid(row=0, column=2, padx=2)
        
        ttk.Button(btn_frame, text="🏠 Reset Îles", 
                  command=self.reset_map).grid(row=0, column=3, padx=2)
        
        ttk.Button(btn_frame, text="📍 Ajouter Point", 
                  command=self.add_custom_marker).grid(row=0, column=4, padx=2)
        
        # Section Filtrage des Marées - ROW 2
        tide_frame = ttk.LabelFrame(control_frame, text="🌊 Filtrage des Données de Marée", padding="10")
        tide_frame.grid(row=2, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(10, 0))

        # Ligne 1: Import CSV
        csv_row = ttk.Frame(tide_frame)
        csv_row.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(csv_row, text="Fichier CSV:").grid(row=0, column=0, padx=(0, 5))
        self.csv_path_var = tk.StringVar(value="Aucun fichier sélectionné")
        csv_label = ttk.Label(csv_row, textvariable=self.csv_path_var, 
                            foreground="gray", width=40)
        csv_label.grid(row=0, column=1, padx=(0, 10))

        ttk.Button(csv_row, text="📁 Importer CSV", 
                command=self.import_csv).grid(row=0, column=2, padx=2)

        # Ligne 2: Dates limites
        date_row = ttk.Frame(tide_frame)
        date_row.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(date_row, text="Date début:").grid(row=0, column=0, padx=(0, 5))
        self.start_date_var = tk.StringVar(value="")
        start_date_entry = ttk.Entry(date_row, textvariable=self.start_date_var, width=15)
        start_date_entry.grid(row=0, column=1, padx=(0, 10))
        ttk.Label(date_row, text="(YYYY-MM-DD)", foreground="gray").grid(row=0, column=2, padx=(0, 20))

        ttk.Label(date_row, text="Date fin:").grid(row=0, column=3, padx=(0, 5))
        self.end_date_var = tk.StringVar(value="")
        end_date_entry = ttk.Entry(date_row, textvariable=self.end_date_var, width=15)
        end_date_entry.grid(row=0, column=4, padx=(0, 10))
        ttk.Label(date_row, text="(YYYY-MM-DD)", foreground="gray").grid(row=0, column=5)

        # Ligne 3: Niveaux de marée
        level_row = ttk.Frame(tide_frame)
        level_row.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(level_row, text="Niveau min (m):").grid(row=0, column=0, padx=(0, 5))
        self.min_level_var = tk.StringVar(value="")
        min_level_entry = ttk.Entry(level_row, textvariable=self.min_level_var, width=10)
        min_level_entry.grid(row=0, column=1, padx=(0, 20))

        ttk.Label(level_row, text="Niveau max (m):").grid(row=0, column=2, padx=(0, 5))
        self.max_level_var = tk.StringVar(value="")
        max_level_entry = ttk.Entry(level_row, textvariable=self.max_level_var, width=10)
        max_level_entry.grid(row=0, column=3, padx=(0, 20))

        # Ligne 4: Boutons d'action
        action_row = ttk.Frame(tide_frame)
        action_row.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E))

        ttk.Button(action_row, text="🔍 Filtrer Données", 
                command=self.filter_tide_data).grid(row=0, column=0, padx=2)

        ttk.Button(action_row, text="📊 Voir Statistiques", 
                command=self.show_statistics).grid(row=0, column=1, padx=2)

        ttk.Button(action_row, text="🗑️ Réinitialiser", 
                command=self.reset_tide_filters).grid(row=0, column=2, padx=2)

        # ====================================================================
        # Section Personnalisation des Couleurs - ROW 3 (changé de 2 à 3)
        # ====================================================================
        color_frame = ttk.LabelFrame(control_frame, text="🎨 Couleurs des Shapefiles", padding="10")
        color_frame.grid(row=3, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(10, 0))

        # Ligne de sélection des couleurs
        color_row = ttk.Frame(color_frame)
        color_row.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E))

        ttk.Label(color_row, text="Couleur ancienne (début):").grid(row=0, column=0, padx=(0, 5))
        self.start_color_var = tk.StringVar(value=self.shapefile_start_color)
        start_color_entry = ttk.Entry(color_row, textvariable=self.start_color_var, width=10)
        start_color_entry.grid(row=0, column=1, padx=(0, 5))

        # Bouton pour sélectionner la couleur de début
        def choose_start_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(initialcolor=self.start_color_var.get())
            if color[1]:
                self.start_color_var.set(color[1])
                self.shapefile_start_color = color[1]

        ttk.Button(color_row, text="🎨", command=choose_start_color, width=3).grid(row=0, column=2, padx=(0, 20))

        ttk.Label(color_row, text="Couleur récente (fin):").grid(row=0, column=3, padx=(0, 5))
        self.end_color_var = tk.StringVar(value=self.shapefile_end_color)
        end_color_entry = ttk.Entry(color_row, textvariable=self.end_color_var, width=10)
        end_color_entry.grid(row=0, column=4, padx=(0, 5))

        # Bouton pour sélectionner la couleur de fin
        def choose_end_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(initialcolor=self.end_color_var.get())
            if color[1]:
                self.end_color_var.set(color[1])
                self.shapefile_end_color = color[1]

        ttk.Button(color_row, text="🎨", command=choose_end_color, width=3).grid(row=0, column=5, padx=(0, 10))

        # Aperçu du gradient
        gradient_canvas = tk.Canvas(color_row, width=200, height=20)
        gradient_canvas.grid(row=0, column=6, padx=(10, 0))

        def update_gradient_preview():
            gradient_canvas.delete("all")
            for i in range(200):
                ratio = i / 200
                # Interpoler entre start et end color
                start_rgb = tuple(int(self.start_color_var.get()[j:j+2], 16) for j in (1, 3, 5))
                end_rgb = tuple(int(self.end_color_var.get()[j:j+2], 16) for j in (1, 3, 5))
                
                r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
                g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
                b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
                
                color = f"#{r:02x}{g:02x}{b:02x}"
                gradient_canvas.create_line(i, 0, i, 20, fill=color)

        # Lier les changements de couleur à la mise à jour du gradient
        self.start_color_var.trace('w', lambda *args: update_gradient_preview())
        self.end_color_var.trace('w', lambda *args: update_gradient_preview())

        # Initialiser l'aperçu
        update_gradient_preview()

        # Bouton pour appliquer
        ttk.Button(color_frame, text="✅ Appliquer les couleurs", 
                command=self.apply_color_gradient).grid(row=1, column=0, pady=(10, 0))

        # ====================================================================
        # Section Pipeline de Traitement - ROW 4 (changé de 3 à 4)
        # ====================================================================
        pipeline_frame = ttk.LabelFrame(control_frame, text="🚀 Pipeline de Traitement Sentinel-2", padding="10")
        pipeline_frame.grid(row=4, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(10, 0))

        # Bouton de lancement du pipeline
        ttk.Button(pipeline_frame, text="🛰️ Lancer Pipeline Complet", 
                command=self.run_pipeline, 
                style='Accent.TButton').grid(row=0, column=0, padx=5, pady=5)

        ttk.Label(pipeline_frame, text="(Télécharge, traite et génère les shapefiles)", 
                foreground="gray").grid(row=0, column=1, padx=5)

        # Barre de progression
        self.pipeline_progress_var = tk.DoubleVar()
        self.pipeline_progress = ttk.Progressbar(
            pipeline_frame, 
            variable=self.pipeline_progress_var,
            maximum=100,
            mode='determinate',
            length=300
        )
        self.pipeline_progress.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        self.pipeline_status_var = tk.StringVar(value="Prêt")
        ttk.Label(pipeline_frame, textvariable=self.pipeline_status_var).grid(
            row=2, column=0, columnspan=2, pady=2
        )
        
        # Frame pour l'aperçu de la carte
        preview_frame = ttk.LabelFrame(main_frame, text="Aperçu de la Carte", padding="5")
        preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Zone de texte pour afficher les informations
        self.preview_text = tk.Text(preview_frame, height=15, width=80, wrap=tk.WORD)
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.preview_text.configure(yscrollcommand=scrollbar.set)
        
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # Frame d'informations
        info_frame = ttk.LabelFrame(main_frame, text="Informations", padding="5")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.info_text = tk.Text(info_frame, height=6, width=100)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        info_scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
        
        # Message de bienvenue
        self.update_info("🗺️ Interface Folium initialisée")
        self.update_info("🏝️ Vue centrée sur les Îles de la Madeleine, Québec")
        self.update_info("🛰️ Mode satellitaire activé par défaut")
        self.update_info("🌐 Cliquez sur 'Ouvrir dans Navigateur' pour voir la carte interactive")
    
    def create_folium_map(self):
        """Crée une carte Folium avec vue satellitaire"""
        try:
            # Récupérer les coordonnées et zoom
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())
            zoom = int(self.zoom_var.get())
            
            print(f"🗺️ Création carte: lat={lat}, lon={lon}, zoom={zoom}")
            
            # Créer la carte Folium
            self.map_object = folium.Map(
                location=[lat, lon],
                zoom_start=zoom,
                tiles=None
            )
            
            print(f"✅ Objet carte créé")
            
            # Ajouter le style de carte sélectionné
            self.add_map_tiles()
            print(f"✅ Tiles ajoutés")
            
            # Ajouter les marqueurs des lieux prédéfinis
            self.add_location_markers()
            print(f"✅ Marqueurs ajoutés: {len(self.locations)}")
            
            # Ajouter les shapefiles
            print(f"📊 Shapefiles disponibles: {len(self.shapefiles)}")
            self.add_shapefiles_to_map()
            print(f"✅ Shapefiles ajoutés")
            
            # Ajouter des plugins utiles
            self.add_map_plugins()
            print(f"✅ Plugins ajoutés")
            
            # Charger les TIFF disponibles
            self.load_existing_tiffs()
            print(f"📊 TIFF disponibles: {len(self.tiff_data)}")
            
            # Ajouter le widget de visualisation TIFF
            self.add_tiff_viewer_widget()
            print(f"✅ Widget TIFF ajouté")

            # Afficher les informations de la carte
            self.show_map_preview()
            
            self.update_info(f"✅ Carte générée avec {len(self.shapefiles)} shapefile(s)")
            
        except ValueError as e:
            messagebox.showerror("Erreur", f"Coordonnées invalides: {e}")
        except Exception as e:
            print(f"❌ ERREUR create_folium_map: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la création de la carte: {e}")
    
    def add_map_tiles(self):
        """Ajoute plusieurs styles de carte accessibles via le contrôle de couches"""
        
        """
        # 1. Vue satellite VIIRS True Color (daily, time-enabled; NASA)
        folium.TileLayer(
            tiles="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{date}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg",
            attr="Imagery © NASA EOSDIS GIBS",
            name="🛰️ NASA VIIRS True Color",
            overlay=False,
            control=True,
            show=True  # Visible par défaut
        ).add_to(self.map_object)

        # 2. Vue satellite Esri (par défaut, visible au démarrage)
        folium.TileLayer(
            tiles="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/2004-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
            attr="NASA Blue Marble",
            name='🛰️ Imagery © NASA EOSDIS GIBS',
            overlay=False,
            control=True,
            show=True  # Visible par défaut
        ).add_to(self.map_object)
        """
        # 3. Vue satellite Esri
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='🛰️ Satellite',
            overlay=False,
            control=True,
            show=True  # Visible par défaut
        ).add_to(self.map_object)
        
        # 4. Satellite avec labels et routes
        satellite_hybrid = folium.FeatureGroup(name='🗺️ Satellite + Routes', show=False)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            overlay=False
        ).add_to(satellite_hybrid)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            overlay=True
        ).add_to(satellite_hybrid)
        satellite_hybrid.add_to(self.map_object)
        
        # 5. OpenStreetMap
        folium.TileLayer(
            'OpenStreetMap',
            name='🗺️ OpenStreetMap',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 6. CartoDB Positron (clair)
        folium.TileLayer(
            'CartoDB positron',
            name='⚪ CartoDB Clair',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 8. CartoDB Dark Matter (sombre)
        folium.TileLayer(
            'CartoDB dark_matter',
            name='⚫ CartoDB Sombre',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 9. OpenTopoMap (relief)
        folium.TileLayer(
            'OpenTopoMap',
            name='🏔️ Relief (Topo)',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 10. Stamen Terrain
        folium.TileLayer(
            tiles='https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png',
            attr='Stamen Terrain',
            name='🌄 Terrain',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
    
    def add_location_markers(self):
        """Ajoute les marqueurs des lieux prédéfinis"""
        for location in self.locations:
            # Créer un popup avec les informations
            popup_html = f"""
            <div style='width: 250px; font-family: Arial;'>
                <h3 style='margin: 0 0 10px 0; color: #2c3e50;'>
                    {location['emoji']} {location['name']}
                </h3>
                <hr style='margin: 10px 0;'>
                <p style='margin: 5px 0;'>
                    <b>📍 Coordonnées:</b><br>
                    Lat: {location['lat']:.4f}°<br>
                    Lon: {location['lon']:.4f}°
                </p>
                <p style='margin: 5px 0;'>
                    <b>ℹ️ Info:</b><br>
                    {location['info']}
                </p>
            </div>
            """
            
            # Ajouter le marqueur
            folium.Marker(
                location=[location['lat'], location['lon']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{location['emoji']} {location['name']}",
                icon=folium.Icon(color=location['color'], icon='info-sign')
            ).add_to(self.map_object)
    
    def add_map_plugins(self):
        """Ajoute des plugins utiles à la carte"""
        # Plugin de mesure de distance
        plugins.MeasureControl(
            position='topleft',
            primary_length_unit='meters',
            secondary_length_unit='kilometers',
            primary_area_unit='sqmeters',
            secondary_area_unit='acres'
        ).add_to(self.map_object)
        
        # Plugin de mini-carte
        minimap = plugins.MiniMap(
            toggle_display=True,
            tile_layer='OpenStreetMap'
        )
        self.map_object.add_child(minimap)
        
        # Plugin de géolocalisation
        plugins.LocateControl().add_to(self.map_object)
        
        # Plugin de plein écran
        plugins.Fullscreen(
            position='topright',
            title='Plein écran',
            title_cancel='Quitter plein écran',
            force_separate_button=True
        ).add_to(self.map_object)
        
        # Widget d'affichage des coordonnées du curseur
        plugins.MousePosition(
            position='bottomleft',
            separator=' | ',
            empty_string='NaN',
            lng_first=False,
            num_digits=4,
            prefix='Coordonnées: ',
            lat_formatter="function(num) {return L.Util.formatNum(num, 4) + ' °N';}",
            lng_formatter="function(num) {return L.Util.formatNum(num, 4) + ' °O';}"
        ).add_to(self.map_object)
        
        # Ajouter un contrôle de couches
        folium.LayerControl(position='topright').add_to(self.map_object)

  #======================================================================================

    def add_tiff_viewer_widget(self):
        """Timeline par année + Widgets masquables pour images et TIFF - disposition optimisée"""
        if not self.tiff_data:
            return
        
        # Préparer les TIFF pour le web
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent))
            from tiff_to_tiles import prepare_tiffs_for_web
        except ImportError:
            try:
                from src.tiff_to_tiles import prepare_tiffs_for_web
            except ImportError as e:
                print(f"⚠️  Erreur import tiff_to_tiles: {e}")
                return
        
        print("\n🔄 Préparation des TIFF pour l'affichage web...")
        web_tiffs = prepare_tiffs_for_web()
        
        if not web_tiffs:
            print("⚠️  Aucun TIFF converti")
            return
        
        # Organiser les données par année
        tiff_by_year = {}
        for date_str in sorted(web_tiffs.keys()):
            year = date_str[:4]
            if year not in tiff_by_year:
                tiff_by_year[year] = []
            
            info = web_tiffs[date_str]
            tiff_by_year[year].append({
                'date': date_str,
                'png_path': info['png_path'],
                'bounds': info['bounds']
            })
        
        # Créer la liste des années
        years = sorted(tiff_by_year.keys())
        year_data = []
        for year in years:
            year_data.append({
                'year': year,
                'dates': tiff_by_year[year],
                'selected': year == years[-1] if years else False
            })
        
        # Lister les images PNG dans data/image
        image_files = []
        if self.images_dir.exists():
            for img in sorted(self.images_dir.glob('*.png')):
                image_files.append({
                    'name': img.name,
                    'path': str(img.relative_to(Path.cwd()))
                })
            for img in sorted(self.images_dir.glob('*.jpg')):
                image_files.append({
                    'name': img.name,
                    'path': str(img.relative_to(Path.cwd()))
                })
        
        # Créer le dossier static/tiffs s'il n'existe pas
        static_tiffs = Path('static/tiffs')
        static_tiffs.mkdir(parents=True, exist_ok=True)
        
        # Lister les TIFF générés dans data/processed
        tiff_images = []
        processed_path = Path('data/processed')
        if processed_path.exists():
            for date_folder in sorted(processed_path.glob('*')):
                if not date_folder.is_dir():
                    continue
                
                date_str = date_folder.name
                
                tiff_files = {
                    'B04': list(date_folder.glob('B04_*.tif')),
                    'B08': list(date_folder.glob('B08_*.tif')),
                    'NDVI': list(date_folder.glob('NDVI_*.tif'))
                }
                
                for tiff_type, files in tiff_files.items():
                    if files:
                        tiff_path = files[0]
                        png_path = static_tiffs / f"{date_str}_{tiff_type}.png"
                        
                        try:
                            if not png_path.exists():
                                from tiff_to_tiles import convert_tiff_to_png_with_palette
                                convert_tiff_to_png_with_palette(tiff_path, png_path)
                            
                            tiff_images.append({
                                'date': date_str,
                                'type': tiff_type,
                                'path': str(png_path.relative_to(Path.cwd())),
                                'name': f"{tiff_type} - {date_str}",
                                'original': str(tiff_path)
                            })
                        except Exception as e:
                            print(f"   ⚠️  Erreur conversion {tiff_type}: {e}")
        
        # Générer le JavaScript avec disposition optimisée
        widget_js = f"""
        <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.css">
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://code.jquery.com/ui/1.13.2/jquery-ui.min.js"></script>
        
        <style>
            .widget-container {{
                position: absolute;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                z-index: 1000;
                font-family: Arial, sans-serif;
                max-height: 90vh;
                display: flex;
                flex-direction: column;
            }}
            
            .widget-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 15px;
                color: white;
                border-radius: 8px 8px 0 0;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
                flex-shrink: 0;
            }}
            
            .widget-content {{
                padding: 15px;
                overflow-y: auto;
                flex: 1;
                max-height: calc(90vh - 50px);
            }}
            
            .image-thumb {{
                width: 100%;
                max-width: 150px;
                margin: 5px 0;
                border-radius: 4px;
                cursor: pointer;
                transition: transform 0.2s;
            }}
            
            .image-thumb:hover {{
                transform: scale(1.05);
            }}
        </style>
        
        <script>
            const yearData = {json.dumps(year_data)};
            const imageFiles = {json.dumps(image_files)};
            const tiffImages = {json.dumps(tiff_images)};
            
            let currentTiffLayer = null;
            let currentYearIndex = yearData.length - 1;
            
            const widgetsHTML = `
                <!-- Timeline Widget (haut droite) -->
                <div class="widget-container" style="top: 80px; right: 20px; width: 320px; max-height: 500px;">
                    <div class="widget-header" style="background: #4CAF50;">
                        📅 Timeline par Année
                    </div>
                    <div class="widget-content">
                        <div style="margin-bottom: 15px;">
                            <div id="current-year-display" style="
                                font-size: 18px;
                                font-weight: bold;
                                color: #4CAF50;
                                text-align: center;
                                margin-bottom: 10px;
                            "></div>
                            
                            <div id="current-date-display" style="
                                font-size: 14px;
                                color: #666;
                                text-align: center;
                                margin-bottom: 15px;
                            "></div>
                        </div>
                        
                        <!-- Slider pour les années -->
                        <div style="margin: 20px 10px;">
                            <label style="font-size: 12px; color: #666; margin-bottom: 5px; display: block;">
                                Année:
                            </label>
                            <div id="year-slider"></div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #999; margin-top: 5px;">
                                <span id="year-start"></span>
                                <span id="year-end"></span>
                            </div>
                        </div>
                        
                        <!-- Slider pour les dates -->
                        <div id="date-slider-container" style="margin: 20px 10px;">
                            <label style="font-size: 12px; color: #666; margin-bottom: 5px; display: block;">
                                Date:
                            </label>
                            <div id="date-slider"></div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #999; margin-top: 5px;">
                                <span id="date-start"></span>
                                <span id="date-end"></span>
                            </div>
                        </div>
                        
                        <!-- Contrôle opacité -->
                        <div style="margin: 15px 10px;">
                            <label style="font-size: 12px; color: #666;">
                                Opacité:
                                <input type="range" id="tiff-opacity-slider" min="0" max="100" value="70" 
                                    style="width: 100%;">
                                <span id="tiff-opacity-value">70%</span>
                            </label>
                        </div>
                        
                        <!-- Légende compacte -->
                        <div style="margin-top: 15px; padding: 10px; background: #f9f9f9; border-radius: 4px; font-size: 10px;">
                            <div style="font-weight: bold; margin-bottom: 5px;">Légende NDVI:</div>
                            <div style="display: grid; grid-template-columns: auto 1fr; gap: 3px; line-height: 1.6;">
                                <span style="width:12px; height:12px; background:rgba(0,0,255,0.7); display:inline-block;"></span><span>Eau</span>
                                <span style="width:12px; height:12px; background:rgba(165,42,42,0.7); display:inline-block;"></span><span>Sol nu</span>
                                <span style="width:12px; height:12px; background:rgba(255,255,0,0.8); display:inline-block;"></span><span>Vég. faible</span>
                                <span style="width:12px; height:12px; background:rgba(144,238,144,0.9); display:inline-block;"></span><span>Vég. moyenne</span>
                                <span style="width:12px; height:12px; background:rgba(0,128,0,0.9); display:inline-block;"></span><span>Vég. dense</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Widget Images (bas gauche) -->
                <div class="widget-container" style="bottom: 20px; left: 20px; width: 250px; max-height: 350px;">
                    <div class="widget-header" style="background: #2196F3;" onclick="toggleWidget('images')">
                        <span>🖼️ Images</span>
                        <span id="images-toggle">▼</span>
                    </div>
                    <div id="images-content" class="widget-content">
                        <div id="images-list"></div>
                    </div>
                </div>
                
                <!-- Widget TIFF (bas centre) -->
                <div class="widget-container" style="bottom: 20px; left: 290px; width: 250px; max-height: 350px;">
                    <div class="widget-header" style="background: #FF9800;" onclick="toggleWidget('tiff-images')">
                        <span>📊 TIFF NDVI</span>
                        <span id="tiff-images-toggle">▼</span>
                    </div>
                    <div id="tiff-images-content" class="widget-content">
                        <div id="tiff-images-list"></div>
                    </div>
                </div>
            `;
            
            document.addEventListener('DOMContentLoaded', function() {{
                const mapContainer = document.querySelector('.folium-map');
                if (mapContainer) {{
                    mapContainer.insertAdjacentHTML('beforeend', widgetsHTML);
                    
                    initTimeline();
                    populateImagesList();
                    populateTiffImagesList();
                    
                    const opacitySlider = document.getElementById('tiff-opacity-slider');
                    const opacityValue = document.getElementById('tiff-opacity-value');
                    
                    opacitySlider.oninput = function() {{
                        const opacity = this.value / 100;
                        opacityValue.textContent = this.value + '%';
                        if (currentTiffLayer) {{
                            currentTiffLayer.setOpacity(opacity);
                        }}
                    }};
                }}
            }});
            
            function initTimeline() {{
                if (yearData.length === 0) return;
                
                const years = yearData.map(y => y.year);
                document.getElementById('year-start').textContent = years[0];
                document.getElementById('year-end').textContent = years[years.length - 1];
                
                $("#year-slider").slider({{
                    min: 0,
                    max: yearData.length - 1,
                    value: currentYearIndex,
                    slide: function(event, ui) {{ updateYear(ui.value); }},
                    change: function(event, ui) {{ updateYear(ui.value); }}
                }});
                
                updateYear(currentYearIndex);
            }}
            
            function updateYear(yearIndex) {{
                currentYearIndex = yearIndex;
                const yearInfo = yearData[yearIndex];
                
                document.getElementById('current-year-display').textContent = yearInfo.year;
                
                const dates = yearInfo.dates;
                if (dates.length === 0) return;
                
                document.getElementById('date-start').textContent = dates[0].date;
                document.getElementById('date-end').textContent = dates[dates.length - 1].date;
                
                $("#date-slider").slider('destroy').slider({{
                    min: 0,
                    max: dates.length - 1,
                    value: dates.length - 1,
                    slide: function(event, ui) {{ updateDate(yearIndex, ui.value); }},
                    change: function(event, ui) {{ updateDate(yearIndex, ui.value); }}
                }});
                
                updateDate(yearIndex, dates.length - 1);
            }}
            
            function updateDate(yearIndex, dateIndex) {{
                const yearInfo = yearData[yearIndex];
                const dateInfo = yearInfo.dates[dateIndex];
                
                document.getElementById('current-date-display').textContent = dateInfo.date;
                loadTiffOverlay(dateInfo);
            }}
            
            function loadTiffOverlay(item) {{
                try {{
                    if (currentTiffLayer) {{
                        map.removeLayer(currentTiffLayer);
                        currentTiffLayer = null;
                    }}
                    
                    const bounds = L.latLngBounds(
                        L.latLng(item.bounds.south, item.bounds.west),
                        L.latLng(item.bounds.north, item.bounds.east)
                    );
                    
                    currentTiffLayer = L.imageOverlay(
                        item.png_path,
                        bounds,
                        {{
                            opacity: document.getElementById('tiff-opacity-slider').value / 100,
                            interactive: true,
                            alt: `NDVI ${{item.date}}`
                        }}
                    );
                    
                    currentTiffLayer.addTo(map);
                    map.fitBounds(bounds, {{ padding: [50, 50] }});
                    
                    currentTiffLayer.on('click', function(e) {{
                        L.popup()
                            .setLatLng(e.latlng)
                            .setContent(`<div style="padding:10px;"><h4 style="margin:0 0 10px 0;">📊 NDVI</h4><p style="margin:5px 0;"><b>Date:</b> ${{item.date}}</p></div>`)
                            .openOn(map);
                    }});
                    
                }} catch (error) {{
                    console.error('Erreur chargement TIFF:', error);
                }}
            }}
            
            function populateImagesList() {{
                const list = document.getElementById('images-list');
                
                if (imageFiles.length === 0) {{
                    list.innerHTML = '<p style="color:#999;font-size:11px;text-align:center;padding:10px;">Aucune image</p>';
                    return;
                }}
                
                imageFiles.forEach(img => {{
                    const div = document.createElement('div');
                    div.style.cssText = 'margin:8px 0;text-align:center;';
                    div.innerHTML = `
                        <div style="margin-bottom:3px;font-size:11px;font-weight:bold;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${{img.name}}">${{img.name}}</div>
                        <img src="${{img.path}}" class="image-thumb" onclick="showImagePopup('${{img.path}}','${{img.name}}')">
                    `;
                    list.appendChild(div);
                }});
            }}
            
            function populateTiffImagesList() {{
                const list = document.getElementById('tiff-images-list');
                
                if (tiffImages.length === 0) {{
                    list.innerHTML = '<p style="color:#999;font-size:11px;text-align:center;padding:10px;">Aucun TIFF</p>';
                    return;
                }}
                
                const byDate = {{}};
                tiffImages.forEach(img => {{
                    if (!byDate[img.date]) byDate[img.date] = [];
                    byDate[img.date].push(img);
                }});
                
                Object.keys(byDate).sort().reverse().forEach(date => {{
                    const dateDiv = document.createElement('div');
                    dateDiv.style.cssText = 'margin:10px 0;border-bottom:1px solid #eee;padding-bottom:8px;';
                    
                    let html = `<div style="font-size:11px;font-weight:bold;color:#FF9800;margin-bottom:5px;">📅 ${{date}}</div>`;
                    
                    byDate[date].forEach(img => {{
                        html += `
                            <div style="margin:5px 0;padding:3px;background:#f9f9f9;border-radius:3px;">
                                <div style="font-size:10px;font-weight:bold;margin-bottom:2px;">${{img.type}}</div>
                                <img src="${{img.path}}" class="image-thumb" onclick="showImagePopup('${{img.path}}','${{img.name}}')" style="max-width:100%;">
                            </div>
                        `;
                    }});
                    
                    dateDiv.innerHTML = html;
                    list.appendChild(dateDiv);
                }});
            }}
            
            function toggleWidget(widgetName) {{
                const content = document.getElementById(widgetName + '-content');
                const toggle = document.getElementById(widgetName + '-toggle');
                
                if (content.style.display === 'none') {{
                    content.style.display = 'block';
                    toggle.textContent = '▼';
                }} else {{
                    content.style.display = 'none';
                    toggle.textContent = '▶';
                }}
            }}
            
            function showImagePopup(path, name) {{
                L.popup({{ maxWidth: 600, maxHeight: 500 }})
                .setLatLng(map.getCenter())
                .setContent(`<div style="text-align:center;"><h4 style="margin:0 0 10px 0;">${{name}}</h4><img src="${{path}}" style="max-width:100%;max-height:400px;border-radius:4px;"/></div>`)
                .openOn(map);
            }}
        </script>
        """
        
        from folium import Element
        self.map_object.get_root().html.add_child(Element(widget_js))
        
        print(f"✅ Timeline et widgets ajoutés (disposition optimisée)")
        print(f"   📅 {len(year_data)} année(s)")
        print(f"   🖼️ {len(image_files)} images")
        print(f"   📊 {len(tiff_images)} TIFF NDVI")
# =============================================================================

    def show_map_preview(self):
        """Affiche un aperçu des informations de la carte"""
        if self.map_object:
            # Informations sur la carte
            markers_count = len(self.locations)
            markers_text = f"({markers_count} marqueur(s) personnalisé(s))" if markers_count > 0 else "(aucun marqueur)"
            
            info = f"""
🏝️ CARTE INTERACTIVE - ÎLES DE LA MADELEINE

📍 LOCALISATION:
   Centre: {self.lat_var.get()}, {self.lon_var.get()}
   Zoom: {self.zoom_var.get()}

🗺️ À PROPOS DES ÎLES:
   • Archipel du golfe du Saint-Laurent
   • Province: Québec, Canada
   • Superficie: ~202 km²
   • Population: ~13,000 habitants
   • 7 îles principales reliées par routes et ponts

🎨 STYLES DE CARTE DISPONIBLES (changeable sur la carte web):
   🛰️ Satellite - Vue satellite haute résolution (PAR DÉFAUT)
   🗺️ Satellite + Routes - Avec labels et routes
   🗺️ OpenStreetMap - Carte standard
   ⚪ CartoDB Clair - Style minimaliste clair
   ⚫ CartoDB Sombre - Style sombre
   🏔️ Relief (Topo) - Carte topographique
   🌄 Terrain - Relief et nature

📍 MARQUEURS:
   {markers_text}

🔧 PLUGINS INCLUS:
  • Mesure de distance (mètres/kilomètres)
  • Mini-carte de navigation
  • Géolocalisation
  • Mode plein écran
  • Affichage coordonnées curseur
  • Contrôle des couches (en haut à droite)

🛰️ SOURCE IMAGERIE:
  • Esri World Imagery (vue satellite haute résolution)
  • Mise à jour régulière
  • Idéal pour analyse géospatiale

💡 UTILISATION:
  • Cliquez sur 'Ouvrir dans Navigateur' pour explorer
  • Utilisez le contrôle des couches (🗂️ en haut à droite) pour changer le style
  • Utilisez la molette pour zoomer
  • Cliquez sur les marqueurs pour plus d'infos
  • Utilisez l'outil de mesure pour calculer distances
            """
            
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, info)
    
    def open_in_browser(self):
        """Ouvre la carte dans le navigateur web"""
        if not self.map_object:
            messagebox.showwarning("Attention", "Veuillez d'abord générer une carte")
            return
        
        try:
            # Créer un fichier temporaire
            if self.temp_map_file:
                try:
                    os.unlink(self.temp_map_file)
                except:
                    pass
            
            self.temp_map_file = tempfile.mktemp(suffix='.html')
            
            # Sauvegarder la carte
            self.map_object.save(self.temp_map_file)
            
            # Ouvrir dans le navigateur
            webbrowser.open(f'file://{os.path.abspath(self.temp_map_file)}')
            
            self.update_info(f"🌐 Carte ouverte dans le navigateur: {self.temp_map_file}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir la carte: {e}")
    
    def save_map(self):
        """Sauvegarde la carte dans un fichier"""
        if not self.map_object:
            messagebox.showwarning("Attention", "Veuillez d'abord générer une carte")
            return
        
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="Sauvegarder la carte",
            defaultextension=".html",
            initialfile="iles_madeleine_map.html",
            filetypes=[("HTML files", "*.html"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            try:
                self.map_object.save(file_path)
                self.update_info(f"💾 Carte sauvegardée: {file_path}")
                messagebox.showinfo("Succès", f"Carte sauvegardée avec succès!\n{file_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def reset_map(self):
        """Remet la carte sur les Îles de la Madeleine"""
        self.lat_var.set(str(self.ILES_MADELEINE_LAT))
        self.lon_var.set(str(self.ILES_MADELEINE_LON))
        self.zoom_var.set("11")
        self.create_folium_map()
        self.update_info("🔄 Carte remise sur les Îles de la Madeleine")
    
    def go_to_location(self, location):
        """Va à un lieu spécifique"""
        self.lat_var.set(str(location['lat']))
        self.lon_var.set(str(location['lon']))
        self.zoom_var.set("14")  # Zoom plus rapproché
        self.create_folium_map()
        self.update_info(f"🎯 Navigation vers {location['emoji']} {location['name']}")
    
    def add_custom_marker(self):
        """Ajoute un marqueur personnalisé"""
        # Fenêtre de dialogue pour ajouter un marqueur
        dialog = tk.Toplevel(self.root)
        dialog.title("Ajouter un marqueur")
        dialog.geometry("350x280")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Variables
        name_var = tk.StringVar(value="Nouveau lieu")
        lat_var = tk.StringVar(value=self.lat_var.get())
        lon_var = tk.StringVar(value=self.lon_var.get())
        color_var = tk.StringVar(value="red")
        info_var = tk.StringVar(value="Description du lieu")
        
        # Interface
        ttk.Label(dialog, text="Nom:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=name_var, width=25).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Latitude:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=lat_var, width=25).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Longitude:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=lon_var, width=25).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Couleur:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        color_combo = ttk.Combobox(dialog, textvariable=color_var, 
                                  values=["red", "blue", "green", "purple", "orange", "darkred", "lightred", "beige", "darkblue"])
        color_combo.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Description:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=info_var, width=25).grid(row=4, column=1, padx=5, pady=5)
        
        def add_marker():
            try:
                new_location = {
                    "name": name_var.get(),
                    "lat": float(lat_var.get()),
                    "lon": float(lon_var.get()),
                    "color": color_var.get(),
                    "emoji": "📍",
                    "info": info_var.get()
                }
                self.locations.append(new_location)
                self.create_folium_map()
                self.update_info(f"📍 Marqueur ajouté: {new_location['name']}")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Erreur", "Coordonnées invalides")
        
        ttk.Button(dialog, text="Ajouter", command=add_marker).grid(row=5, column=0, padx=5, pady=10)
        ttk.Button(dialog, text="Annuler", command=dialog.destroy).grid(row=5, column=1, padx=5, pady=10)
    
    def import_csv(self):
        """Importe un fichier CSV de données de marée"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV de marées",
            filetypes=[
                ("Fichiers CSV", "*.csv"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Créer un objet WaterLevelFilter
                self.tide_filter = WaterLevelFilter(file_path)
                
                # Charger les données
                if self.tide_filter.load_csv_data():
                    self.csv_file_path = file_path
                    filename = Path(file_path).name
                    self.csv_path_var.set(filename)
                    
                    # Obtenir les statistiques
                    stats = self.tide_filter.get_statistics()
                    
                    # Pré-remplir les champs avec les valeurs du CSV
                    if self.tide_filter.data is not None and len(self.tide_filter.data) > 0:
                        # Dates
                        min_date = self.tide_filter.data['date'].min()
                        max_date = self.tide_filter.data['date'].max()
                        self.start_date_var.set(min_date.strftime('%Y-%m-%d'))
                        self.end_date_var.set(max_date.strftime('%Y-%m-%d'))
                        
                        # Niveaux (arrondi à 2 décimales)
                        self.min_level_var.set(f"{stats['min']:.2f}")
                        self.max_level_var.set(f"{stats['max']:.2f}")
                    
                    self.update_info(f"✅ CSV chargé: {filename}")
                    self.update_info(f"   📊 {stats['count']} enregistrements")
                    self.update_info(f"   📅 Période: {min_date.strftime('%Y-%m-%d')} → {max_date.strftime('%Y-%m-%d')}")
                    self.update_info(f"   🌊 Marée: {stats['min']:.2f}m à {stats['max']:.2f}m")
                    
                    messagebox.showinfo(
                        "CSV Chargé", 
                        f"Fichier chargé avec succès!\n\n"
                        f"Enregistrements: {stats['count']}\n"
                        f"Période: {min_date.strftime('%Y-%m-%d')} → {max_date.strftime('%Y-%m-%d')}\n"
                        f"Marée: {stats['min']:.2f}m à {stats['max']:.2f}m"
                    )
                else:
                    messagebox.showerror("Erreur", "Impossible de charger le fichier CSV")
                    
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement:\n{str(e)}")
                self.update_info(f"❌ Erreur: {str(e)}")
    
    def filter_tide_data(self):
        """Filtre les données de marée selon les paramètres"""
        if self.tide_filter is None or self.tide_filter.data is None:
            messagebox.showwarning(
                "Attention",
                "Veuillez d'abord importer un fichier CSV"
            )
            return
        
        try:
            # Récupérer les paramètres
            start_date = self.start_date_var.get().strip()
            end_date = self.end_date_var.get().strip()
            min_level = self.min_level_var.get().strip()
            max_level = self.max_level_var.get().strip()
            
            # Validation
            if not all([start_date, end_date, min_level, max_level]):
                messagebox.showwarning(
                    "Attention",
                    "Veuillez remplir tous les champs"
                )
                return
            
            # Convertir les valeurs
            min_level = float(min_level)
            max_level = float(max_level)
            
            # Valider les dates
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror(
                    "Erreur",
                    "Format de date invalide. Utilisez YYYY-MM-DD"
                )
                return
            
            # Filtrer par date
            self.update_info(f"🔍 Filtrage en cours...")
            filtered_data = self.tide_filter.filter_by_date_range(start_date, end_date)
            
            if filtered_data.empty:
                messagebox.showwarning(
                    "Aucun résultat",
                    "Aucune donnée trouvée pour cette période"
                )
                return
            
            # Filtrer par niveau
            filtered_data = filtered_data[
                (filtered_data['water_level'] >= min_level) & 
                (filtered_data['water_level'] <= max_level)
            ]
            
            if filtered_data.empty:
                messagebox.showwarning(
                    "Aucun résultat",
                    f"Aucune donnée trouvée entre {min_level}m et {max_level}m"
                )
                return
            
            # Créer le dossier de sortie si nécessaire
            output_dir = Path("data/csv")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Générer le nom du fichier de sortie
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"filtered_tides_{timestamp}.csv"
            
            # Exporter les données filtrées
            self.tide_filter.export_filtered_data(filtered_data, str(output_file))
            
            # Afficher les résultats
            result_msg = (
                f"Filtrage terminé!\n\n"
                f"Paramètres:\n"
                f"  • Période: {start_date} → {end_date}\n"
                f"  • Niveau: {min_level}m → {max_level}m\n\n"
                f"Résultats:\n"
                f"  • {len(filtered_data)} enregistrements trouvés\n"
                f"  • Fichier: {output_file.name}\n\n"
                f"Statistiques filtrées:\n"
                f"  • Moyenne: {filtered_data['water_level'].mean():.3f}m\n"
                f"  • Min: {filtered_data['water_level'].min():.3f}m\n"
                f"  • Max: {filtered_data['water_level'].max():.3f}m"
            )
            
            messagebox.showinfo("Filtrage Réussi", result_msg)
            
            self.update_info(f"✅ Filtrage terminé: {len(filtered_data)} enregistrements")
            self.update_info(f"💾 Fichier exporté: {output_file}")
            
            # Demander si l'utilisateur veut ouvrir le dossier
            open_folder = messagebox.askyesno(
                "Ouvrir le dossier?",
                f"Voulez-vous ouvrir le dossier contenant le fichier?\n\n{output_dir}"
            )
            
            if open_folder:
                import platform
                if platform.system() == 'Windows':
                    os.startfile(output_dir)
                elif platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{output_dir}"')
                else:  # Linux
                    os.system(f'xdg-open "{output_dir}"')
            
        except ValueError as e:
            messagebox.showerror(
                "Erreur",
                f"Valeur invalide:\n{str(e)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors du filtrage:\n{str(e)}"
            )
            self.update_info(f"❌ Erreur: {str(e)}")
    
    def show_statistics(self):
        """Affiche les statistiques des données de marée"""
        if self.tide_filter is None or self.tide_filter.data is None:
            messagebox.showwarning(
                "Attention",
                "Veuillez d'abord importer un fichier CSV"
            )
            return
        
        try:
            # Obtenir les statistiques globales
            stats = self.tide_filter.get_statistics()
            daily_stats = self.tide_filter.get_daily_statistics()
            
            # Créer une fenêtre de statistiques
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Statistiques des Marées")
            stats_window.geometry("600x500")
            stats_window.transient(self.root)
            
            # Frame principal avec scrollbar
            main_frame = ttk.Frame(stats_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Zone de texte
            stats_text = tk.Text(main_frame, wrap=tk.WORD, width=70, height=25)
            stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=stats_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            stats_text.configure(yscrollcommand=scrollbar.set)
            
            # Construire le texte des statistiques
            stats_content = f"""
📊 STATISTIQUES DES DONNÉES DE MARÉE

📁 Fichier: {Path(self.csv_file_path).name}

🔢 STATISTIQUES GLOBALES:
{'='*60}
  • Nombre d'enregistrements: {stats['count']}
  • Niveau moyen: {stats['mean']:.3f} m
  • Niveau médian: {stats['median']:.3f} m
  • Niveau minimum: {stats['min']:.3f} m
  • Niveau maximum: {stats['max']:.3f} m
  • Écart-type: {stats['std']:.3f} m
  • Amplitude totale: {stats['max'] - stats['min']:.3f} m

📅 PÉRIODE COUVERTE:
{'='*60}
"""
            if len(self.tide_filter.data) > 0:
                min_date = self.tide_filter.data['date'].min()
                max_date = self.tide_filter.data['date'].max()
                duration = (max_date - min_date).days
                
                stats_content += f"""  • Date début: {min_date.strftime('%Y-%m-%d %H:%M')}
  • Date fin: {max_date.strftime('%Y-%m-%d %H:%M')}
  • Durée: {duration} jours

📈 STATISTIQUES JOURNALIÈRES (10 premiers jours):
{'='*60}
"""
                # Afficher les 10 premiers jours
                daily_head = daily_stats.head(10)
                stats_content += "\n  Date       | Nb  | Moyenne | Min   | Max   | Écart\n"
                stats_content += "  " + "-"*58 + "\n"
                
                for date, row in daily_head.iterrows():
                    stats_content += f"  {date} | {int(row['count']):3d} | {row['mean']:7.3f} | {row['min']:5.3f} | {row['max']:5.3f} | {row['std']:5.3f}\n"
                
                if len(daily_stats) > 10:
                    stats_content += f"\n  ... et {len(daily_stats) - 10} jour(s) supplémentaire(s)\n"
            
            stats_content += f"""

💡 INFORMATIONS:
{'='*60}
  • Utilisez les filtres pour affiner les données
  • Les statistiques sont calculées sur toutes les données chargées
  • Le filtrage créera un nouveau fichier CSV dans data/csv/
"""
            
            # Insérer le texte
            stats_text.insert(1.0, stats_content)
            stats_text.configure(state='disabled')  # Lecture seule
            
            # Bouton fermer
            ttk.Button(
                stats_window, 
                text="Fermer", 
                command=stats_window.destroy
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur lors du calcul des statistiques:\n{str(e)}"
            )
    
    def reset_tide_filters(self):
        """Réinitialise les filtres de marée"""
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.min_level_var.set("")
        self.max_level_var.set("")
        
        if self.tide_filter is not None and self.tide_filter.data is not None:
            # Recharger les valeurs par défaut du CSV
            stats = self.tide_filter.get_statistics()
            min_date = self.tide_filter.data['date'].min()
            max_date = self.tide_filter.data['date'].max()
            
            self.start_date_var.set(min_date.strftime('%Y-%m-%d'))
            self.end_date_var.set(max_date.strftime('%Y-%m-%d'))
            self.min_level_var.set(f"{stats['min']:.2f}")
            self.max_level_var.set(f"{stats['max']:.2f}")
        
        self.update_info("🗑️ Filtres réinitialisés")
    
    def load_existing_shapefiles(self):
        """Charge les shapefiles existants dans output/shapefiles"""
        shapefile_dir = Path("output/shapefiles")
        
        if not shapefile_dir.exists():
            return
        
        # Chercher tous les fichiers .shp
        shapefiles = list(shapefile_dir.glob("surface_*.shp"))
        
        for shp_file in shapefiles:
            # Extraire l'année du nom de fichier
            try:
                year_str = shp_file.stem.replace('surface_', '')
                year = int(year_str)
                
                self.shapefiles[year] = {
                    'path': str(shp_file),
                    'layer': None
                }
                
                self.update_info(f"📁 Shapefile trouvé: {year}")
                
            except ValueError:
                continue
    
    def load_existing_tiffs(self):
        """Charge les fichiers TIFF NDVI existants dans data/processed"""
        processed_dir = Path("data/processed")
        
        if not processed_dir.exists():
            self.update_info("📁 Création du dossier data/processed/")
            processed_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Chercher tous les dossiers de dates (format: YYYY-MM-DD)
        date_folders = [d for d in processed_dir.iterdir() 
                    if d.is_dir() and len(d.name) == 10 and d.name.count('-') == 2]
        
        for date_folder in sorted(date_folders):
            date_str = date_folder.name
            
            # Chercher les fichiers NDVI
            ndvi_files = list(date_folder.glob('NDVI_*.tif'))
            
            if ndvi_files:
                self.tiff_data[date_str] = {
                    'ndvi_path': str(ndvi_files[0]),
                    'b04_path': None,
                    'b08_path': None
                }
                
                # Chercher aussi B04 et B08 si présents
                b04_files = list(date_folder.glob('B04_*.tif'))
                b08_files = list(date_folder.glob('B08_*.tif'))
                
                if b04_files:
                    self.tiff_data[date_str]['b04_path'] = str(b04_files[0])
                if b08_files:
                    self.tiff_data[date_str]['b08_path'] = str(b08_files[0])
                
                self.update_info(f"📊 TIFF trouvé: {date_str}")
        
        if self.tiff_data:
            # Sélectionner la date la plus récente par défaut
            self.selected_tiff_date = max(self.tiff_data.keys())
            self.update_info(f"✅ {len(self.tiff_data)} date(s) TIFF chargée(s)")
        else:
            self.update_info("ℹ️  Aucun TIFF NDVI trouvé dans data/processed/")

    def run_pipeline(self):
        """Lance le pipeline complet de traitement"""
        
        
        # Vérifier que le pipeline est disponible
        if not PIPELINE_AVAILABLE or not self.PipelineProcessor:
            messagebox.showerror(
                "Pipeline Non Disponible",
                "Le module pipeline_processor n'est pas disponible.\n\n"
                "Vérifiez que le fichier src/pipeline_processor.py existe\n"
                "et que toutes les dépendances sont installées."
            )
            return
        
        confirm = messagebox.askyesno(
            "Lancer le Pipeline",
            "Cette opération va:\n"
            "• Télécharger les images depuis Google Drive\n"
            "• Les traiter avec QGIS\n"
            "• Générer les shapefiles\n\n"
            "Cela peut prendre plusieurs heures.\n\n"
            "Continuer?"
        )
        
        if not confirm:
            return
        
        # Désactiver le bouton pendant le traitement
        self.update_info("🚀 Démarrage du pipeline...")
        self.pipeline_status_var.set("Initialisation...")
        self.pipeline_progress_var.set(0)
        
        try:
            # Le processeur est déjà initialisé dans __init__
            # Définir le callback de progression
            def progress_callback(current, total, year):
                progress = (current / total) * 100
                self.pipeline_progress_var.set(progress)
                self.pipeline_status_var.set(f"Traitement année {year} ({current}/{total})")
                self.root.update_idletasks()
            
            # Lancer le traitement
            results = self.PipelineProcessor.process_all_years(progress_callback)
            
            # Mettre à jour l'interface
            self.pipeline_progress_var.set(100)
            self.pipeline_status_var.set("Terminé!")
            
            # Recharger les shapefiles
            self.load_existing_shapefiles()

            # Recharger les TIFF
            self.load_existing_tiffs()

            # Régénérer la carte avec les nouveaux shapefiles
            self.create_folium_map()
            
            messagebox.showinfo(
                "Pipeline Terminé",
                f"Traitement terminé!\n\n"
                f"Réussis: {len([r for r in results if r['status'] == 'success'])}\n"
                f"Échecs: {len([r for r in results if r['status'] == 'failed'])}"
            )
            
            self.update_info("✅ Pipeline terminé avec succès")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur pendant le pipeline:\n{str(e)}")
            self.update_info(f"❌ Erreur pipeline: {str(e)}")
            self.pipeline_status_var.set("Erreur")
    
    def get_color_for_year(self, year, min_year, max_year):
        """
        Génère une couleur avec gradient pour une année
        Plus ancien = moins visible (transparent)
        Plus récent = plus visible (opaque)
        """
        if min_year == max_year:
            return '#FF0000', 0.7
        
        # Normaliser l'année entre 0 et 1
        normalized = (year - min_year) / (max_year - min_year)
        
        # Utiliser un gradient de couleur (bleu ancien -> rouge récent)
        # Et augmenter l'opacité pour les années récentes
        cmap = plt.cm.get_cmap('RdYlBu_r')  # Rouge = récent, Bleu = ancien
        rgba = cmap(normalized)
        
        # Convertir en hex
        hex_color = mcolors.rgb2hex(rgba[:3])
        
        # Opacité : 0.3 (ancien) à 0.9 (récent)
        opacity = 0.3 + (normalized * 0.6)
        
        return hex_color, opacity
    
    def add_shapefiles_to_map(self):
        """Ajoute tous les shapefiles à la carte avec gradient de couleur"""
        if not self.shapefiles:
            return
        
        import geopandas as gpd
        
        years = sorted(self.shapefiles.keys())
        min_year = min(years)
        max_year = max(years)
        
        print(f"\n📊 Ajout des shapefiles ({len(years)} années)")
        
        # Pour calculer les bounds globaux
        all_bounds = []
        
        for year in years:
            shp_info = self.shapefiles[year]
            shp_path = Path(shp_info['path'])
            
            if not shp_path.exists():
                print(f"   ⚠️  Fichier manquant: {shp_path}")
                continue
            
            try:
                # Lire le shapefile
                gdf = gpd.read_file(shp_path)
                
                if gdf.empty:
                    print(f"   ⚠️  Shapefile vide: {year}")
                    continue
                
                # DIAGNOSTIC: Afficher le CRS et les bounds
                print(f"   📍 {year}: CRS = {gdf.crs}")
                print(f"        Bounds = {gdf.total_bounds}")
                print(f"        Polygones = {len(gdf)}")
                
                # Reprojeter en WGS84 (EPSG:4326) pour Folium
                if gdf.crs and gdf.crs != 'EPSG:4326':
                    print(f"        🔄 Reprojection vers WGS84...")
                    gdf = gdf.to_crs('EPSG:4326')
                    print(f"        ✅ Bounds WGS84 = {gdf.total_bounds}")
                
                # Sauvegarder les bounds
                all_bounds.append(gdf.total_bounds)
                
                # Obtenir la couleur et l'opacité
                color, opacity = self.get_color_for_year(year, min_year, max_year)
                
                # Créer un FeatureGroup pour cette année
                fg = folium.FeatureGroup(name=f"📅 {year}", show=True)
                
                # Ajouter chaque polygone
                for idx, row in gdf.iterrows():
                    area_km2 = row.get('area_km2', 0)
                    
                    popup_html = f"""
                    <div style='width: 200px; font-family: Arial;'>
                        <h4 style='margin: 0 0 10px 0; color: #2c3e50;'>
                            📅 Année {year}
                        </h4>
                        <hr style='margin: 10px 0;'>
                        <p style='margin: 5px 0;'>
                            <b>📐 Surface:</b> {area_km2:.4f} km²
                        </p>
                    </div>
                    """
                    
                    # Ajouter le polygone
                    folium.GeoJson(
                        row.geometry,
                        style_function=lambda x, c=color, o=opacity: {
                            'fillColor': c,
                            'color': c,
                            'weight': 2,
                            'fillOpacity': o,
                            'opacity': 1.0
                        },
                        popup=folium.Popup(popup_html, max_width=250),
                        tooltip=f"Année {year}"
                    ).add_to(fg)
                
                # Ajouter le FeatureGroup à la carte
                fg.add_to(self.map_object)
                shp_info['layer'] = fg
                
                print(f"   ✅ {year}: {len(gdf)} polygone(s) ajouté(s)")
                
            except Exception as e:
                print(f"   ❌ Erreur pour {year}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Zoomer sur les shapefiles
        if all_bounds:
            print(f"\n🔍 Ajustement du zoom sur les shapefiles...")
            # Calculer les bounds globaux
            min_x = min(b[0] for b in all_bounds)
            min_y = min(b[1] for b in all_bounds)
            max_x = max(b[2] for b in all_bounds)
            max_y = max(b[3] for b in all_bounds)
            
            bounds = [[min_y, min_x], [max_y, max_x]]
            print(f"   Bounds globaux: {bounds}")
            
            # Ajouter fit_bounds à la carte
            self.map_object.fit_bounds(bounds, padding=[50, 50])
            print(f"   ✅ Zoom ajusté")
            
    def update_info(self, message):
        """Met à jour le texte d'information"""
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)
    
    def load_existing_tiffs(self):
        """Charge les fichiers TIFF NDVI existants dans data/processed"""
        processed_dir = Path("data/processed")
        
        if not processed_dir.exists():
            self.update_info("📁 Création du dossier data/processed/")
            processed_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Chercher tous les dossiers de dates (format: YYYY-MM-DD)
        date_folders = [d for d in processed_dir.iterdir() 
                    if d.is_dir() and len(d.name) == 10 and d.name.count('-') == 2]
        
        for date_folder in sorted(date_folders):
            date_str = date_folder.name
            
            # Chercher les fichiers NDVI
            ndvi_files = list(date_folder.glob('NDVI_*.tif'))
            
            if ndvi_files:
                self.tiff_data[date_str] = {
                    'ndvi_path': str(ndvi_files[0]),
                    'b04_path': None,
                    'b08_path': None
                }
                
                # Chercher aussi B04 et B08 si présents
                b04_files = list(date_folder.glob('B04_*.tif'))
                b08_files = list(date_folder.glob('B08_*.tif'))
                
                if b04_files:
                    self.tiff_data[date_str]['b04_path'] = str(b04_files[0])
                if b08_files:
                    self.tiff_data[date_str]['b08_path'] = str(b08_files[0])
                
                self.update_info(f"📊 TIFF trouvé: {date_str}")
        
        if self.tiff_data:
            # Sélectionner la date la plus récente par défaut
            self.selected_tiff_date = max(self.tiff_data.keys())
            self.update_info(f"✅ {len(self.tiff_data)} date(s) TIFF chargée(s)")
        else:
            self.update_info("ℹ️  Aucun TIFF NDVI trouvé dans data/processed/")

    def apply_color_gradient(self):
        """Applique le gradient de couleur personnalisé aux shapefiles"""
        try:
            # Mettre à jour les variables
            self.shapefile_start_color = self.start_color_var.get()
            self.shapefile_end_color = self.end_color_var.get()
            
            # Régénérer la carte
            self.create_folium_map()
            
            self.update_info(f"🎨 Gradient appliqué: {self.shapefile_start_color} → {self.shapefile_end_color}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'application des couleurs:\n{e}")

    def __del__(self):
        """Nettoyage lors de la destruction"""
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try:
                os.unlink(self.temp_map_file)
            except:
                pass