"""
Interface graphique pour carte Folium interactive - NASASpaceApp2025
Vue satellitaire centrée sur les Îles de la Madeleine
Avec filtrage des données de marée
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

# Importer le filtre de marée
sys.path.insert(0, str(Path(__file__).parent))
from water_level_filter import WaterLevelFilter


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
        
        self.setup_gui()
        self.create_folium_map()
    
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
        
        # Section Filtrage des Marées
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
        
        # Style de carte - SUPPRIMÉ (sera dynamique sur la carte web)
        
        # Lieux prédéfinis - SUPPRIMÉ
        
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
            
            # Créer la carte Folium
            self.map_object = folium.Map(
                location=[lat, lon],
                zoom_start=zoom,
                tiles=None  # Nous ajouterons les tiles manuellement
            )
            
            # Ajouter le style de carte sélectionné
            self.add_map_tiles()
            
            # Ajouter les marqueurs des lieux prédéfinis
            self.add_location_markers()
            
            # Ajouter des plugins utiles
            self.add_map_plugins()
            
            # Afficher les informations de la carte
            self.show_map_preview()
            
            self.update_info(f"✅ Carte générée: centre ({lat}, {lon}), zoom {zoom}")
            self.update_info(f"🛰️ Satellite activé par défaut - Changez le style via le contrôle de couches sur la carte")
            
        except ValueError as e:
            messagebox.showerror("Erreur", f"Coordonnées invalides: {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la carte: {e}")
    
    def add_map_tiles(self):
        """Ajoute plusieurs styles de carte accessibles via le contrôle de couches"""
        
        # 1. Vue satellite Esri (par défaut, visible au démarrage)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='🛰️ Satellite',
            overlay=False,
            control=True,
            show=True  # Visible par défaut
        ).add_to(self.map_object)
        
        # 2. Satellite avec labels et routes
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
        
        # 3. OpenStreetMap
        folium.TileLayer(
            'OpenStreetMap',
            name='🗺️ OpenStreetMap',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 4. CartoDB Positron (clair)
        folium.TileLayer(
            'CartoDB positron',
            name='⚪ CartoDB Clair',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 5. CartoDB Dark Matter (sombre)
        folium.TileLayer(
            'CartoDB dark_matter',
            name='⚫ CartoDB Sombre',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 6. OpenTopoMap (relief)
        folium.TileLayer(
            'OpenTopoMap',
            name='🏔️ Relief (Topo)',
            overlay=False,
            control=True,
            show=False
        ).add_to(self.map_object)
        
        # 7. Stamen Terrain
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
    
    def update_info(self, message):
        """Met à jour le texte d'information"""
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)
    
    def __del__(self):
        """Nettoyage lors de la destruction"""
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try:
                os.unlink(self.temp_map_file)
            except:
                pass