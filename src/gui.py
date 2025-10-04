"""
Interface graphique pour carte du monde interactive - NASASpaceApp2025
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import cartopy.crs as ccrs
import cartopy.feature as cfeature


class WorldMapGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NASA Space App 2025 - Carte du Monde Interactive")
        self.root.geometry("1400x900")
        
        # Variables
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.zoom_level = 1.0
        
        # Variables pour les limites de la vue
        self.view_bounds = {
            'lon_min': -180,
            'lon_max': 180,
            'lat_min': -90,
            'lat_max': 90
        }
        
        # Lieux prédéfinis avec marqueurs
        self.locations = [
            ("Paris", 48.8566, 2.3522, "red", "🗼"),
            ("New York", 40.7128, -74.0060, "blue", "🏙️"),
            ("Tokyo", 35.6762, 139.6503, "green", "🏯"),
            ("Sydney", -33.8688, 151.2093, "orange", "🏖️"),
            ("Le Caire", 30.0444, 31.2357, "purple", "🏛️"),
            ("Brasília", -15.7939, -47.8828, "brown", "🌴")
        ]
        
        self.markers = []  # Liste pour stocker les références des marqueurs
        
        self.setup_gui()
        self.create_world_map()
    
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
        control_frame = ttk.LabelFrame(main_frame, text="Contrôles de Navigation", padding="5")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Coordonnées actuelles
        coord_frame = ttk.Frame(control_frame)
        coord_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(coord_frame, text="Latitude:").grid(row=0, column=0, padx=(0, 5))
        self.lat_label = ttk.Label(coord_frame, text="0.000°", font=("Arial", 12, "bold"))
        self.lat_label.grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(coord_frame, text="Longitude:").grid(row=0, column=2, padx=(0, 5))
        self.lon_label = ttk.Label(coord_frame, text="0.000°", font=("Arial", 12, "bold"))
        self.lon_label.grid(row=0, column=3, padx=(0, 20))
        
        ttk.Label(coord_frame, text="Zoom:").grid(row=0, column=4, padx=(0, 5))
        self.zoom_label = ttk.Label(coord_frame, text="1.0x", font=("Arial", 12, "bold"))
        self.zoom_label.grid(row=0, column=5)
        
        # Affichage des limites de vue
        ttk.Label(coord_frame, text="Vue:").grid(row=0, column=6, padx=(20, 5))
        self.bounds_label = ttk.Label(coord_frame, text="Global", font=("Arial", 10))
        self.bounds_label.grid(row=0, column=7)
        
        # Boutons de navigation
        nav_frame = ttk.Frame(control_frame)
        nav_frame.grid(row=1, column=0, columnspan=4, pady=(5, 0))
        
        ttk.Button(nav_frame, text="Reset Vue", 
                  command=self.reset_view).grid(row=0, column=0, padx=2)
        
        ttk.Button(nav_frame, text="Zoom +", 
                  command=self.zoom_in).grid(row=0, column=1, padx=2)
        
        ttk.Button(nav_frame, text="Zoom -", 
                  command=self.zoom_out).grid(row=0, column=2, padx=2)
        
        ttk.Button(nav_frame, text="Centrer 0,0", 
                  command=self.center_origin).grid(row=0, column=3, padx=2)
        
        ttk.Button(nav_frame, text="Afficher/Masquer Marqueurs", 
                  command=self.toggle_markers).grid(row=0, column=4, padx=2)
        
        # Sélection de lieu prédéfinis
        location_frame = ttk.LabelFrame(control_frame, text="Lieux", padding="5")
        location_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        for i, (name, lat, lon, color, emoji) in enumerate(self.locations):
            btn_text = f"{emoji} {name}"
            ttk.Button(location_frame, text=btn_text,
                      command=lambda l=lat, lo=lon, n=name: self.go_to_location(l, lo, n)).grid(
                      row=i//3, column=i%3, padx=2, pady=2)
        
        # Frame pour la carte
        map_frame = ttk.LabelFrame(main_frame, text="Carte du Monde", padding="5")
        map_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(0, weight=1)
        
        # Canvas pour la carte
        self.map_canvas = tk.Canvas(map_frame, bg='lightblue', width=1200, height=600)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Liaison des événements souris
        self.map_canvas.bind("<Motion>", self.on_mouse_move)
        self.map_canvas.bind("<Button-1>", self.on_click)
        self.map_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
        # Frame d'informations
        info_frame = ttk.LabelFrame(main_frame, text="Informations", padding="5")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.info_text = tk.Text(info_frame, height=4, width=100)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        # Variables pour l'affichage des marqueurs
        self.show_markers = True
        
        # Message de bienvenue
        self.update_info("Carte du monde initialisée. Déplacez la souris pour voir les coordonnées.")
        self.update_info("Cliquez pour centrer, utilisez la molette pour zoomer.")
        self.update_info("Marqueurs visibles sur les lieux préenregistrés.")
    
    def is_location_in_view(self, lat, lon):
        """Vérifie si une coordonnée est dans la vue actuelle"""
        return (self.view_bounds['lat_min'] <= lat <= self.view_bounds['lat_max'] and
                self.view_bounds['lon_min'] <= lon <= self.view_bounds['lon_max'])
    
    def update_view_bounds(self):
        """Met à jour les limites de la vue"""
        if hasattr(self, 'ax'):
            # Pour matplotlib, récupérer les limites actuelles
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            self.view_bounds = {
                'lon_min': xlim[0],
                'lon_max': xlim[1],
                'lat_min': ylim[0],
                'lat_max': ylim[1]
            }
        else:
            # Pour la carte simple, calculer basé sur le zoom et la position
            extent = 180 / self.zoom_level
            self.view_bounds = {
                'lon_min': max(-180, self.current_lon - extent),
                'lon_max': min(180, self.current_lon + extent),
                'lat_min': max(-90, self.current_lat - extent/2),
                'lat_max': min(90, self.current_lat + extent/2)
            }
        
        # Mettre à jour l'affichage des limites
        bounds_text = (f"Lat: {self.view_bounds['lat_min']:.1f}°→{self.view_bounds['lat_max']:.1f}°, "
                      f"Lon: {self.view_bounds['lon_min']:.1f}°→{self.view_bounds['lon_max']:.1f}°")
        self.bounds_label.config(text=bounds_text)
    
    def create_world_map(self):
        """Crée une carte du monde basique"""
        try:
            # Créer une carte simple avec matplotlib
            self.create_matplotlib_map()
        except Exception as e:
            # Fallback vers une carte simple dessinée
            self.create_simple_map()
            self.update_info(f"Carte simplifiée utilisée: {e}")
    
    def create_matplotlib_map(self):
        """Crée une carte avec matplotlib et cartopy"""
        try:
            # Créer une figure matplotlib
            self.fig = Figure(figsize=(12, 6), dpi=100)
            self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            
            # Ajouter les features de la carte
            self.ax.add_feature(cfeature.COASTLINE)
            self.ax.add_feature(cfeature.BORDERS)
            self.ax.add_feature(cfeature.OCEAN, color='lightblue')
            self.ax.add_feature(cfeature.LAND, color='lightgray')
            
            # Ajouter des lignes de grille
            self.ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
            
            # Définir les limites globales
            self.ax.set_global()
            
            # Mettre à jour les limites de vue
            self.update_view_bounds()
            
            # Ajouter les marqueurs pour les lieux
            self.add_matplotlib_markers()
            
            # Intégrer dans tkinter
            self.canvas_widget = FigureCanvasTkAgg(self.fig, self.map_canvas)
            self.canvas_widget.draw()
            self.canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Connecter les événements
            self.canvas_widget.mpl_connect('motion_notify_event', self.on_matplotlib_move)
            self.canvas_widget.mpl_connect('button_press_event', self.on_matplotlib_click)
            
            self.update_info("Carte matplotlib/cartopy chargée avec succès")
            
        except ImportError:
            raise Exception("Cartopy non disponible, utilisation d'une carte simple")
    
    def add_matplotlib_markers(self):
        """Ajoute les marqueurs sur la carte matplotlib avec gestion de visibilité"""
        self.matplotlib_markers = []
        visible_count = 0
        
        for name, lat, lon, color, emoji in self.locations:
            # Vérifier si le marqueur est dans la vue
            is_visible = self.is_location_in_view(lat, lon) and self.show_markers
            
            # Ajouter un point sur la carte
            marker = self.ax.plot(lon, lat, 'o', color=color, markersize=10, 
                                transform=ccrs.PlateCarree(), zorder=5,
                                visible=is_visible)[0]
            
            # Ajouter le label avec le nom de la ville
            text = self.ax.text(lon, lat + 2, f"{emoji} {name}", 
                              transform=ccrs.PlateCarree(),
                              fontsize=8, ha='center', va='bottom',
                              bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
                              zorder=6, visible=is_visible)
            
            self.matplotlib_markers.append((marker, text, name, lat, lon))
            
            if is_visible:
                visible_count += 1
        
        self.update_info(f"Marqueurs: {visible_count}/{len(self.locations)} visibles dans la vue actuelle")
    
    def update_matplotlib_markers_visibility(self):
        """Met à jour la visibilité des marqueurs matplotlib"""
        if not hasattr(self, 'matplotlib_markers'):
            return
            
        visible_count = 0
        
        for marker, text, name, lat, lon in self.matplotlib_markers:
            is_visible = self.is_location_in_view(lat, lon) and self.show_markers
            marker.set_visible(is_visible)
            text.set_visible(is_visible)
            
            if is_visible:
                visible_count += 1
        
        self.canvas_widget.draw()
        self.update_info(f"Marqueurs mis à jour: {visible_count}/{len(self.locations)} visibles")
    
    def create_simple_map(self):
        """Crée une carte simple dessinée avec gestion de la visibilité des marqueurs"""
        # Dimensions de la carte
        width = 1200
        height = 600
        
        # Mettre à jour les limites de vue
        self.update_view_bounds()
        
        # Créer une image de base
        self.map_image = Image.new('RGB', (width, height), 'lightblue')
        draw = ImageDraw.Draw(self.map_image)
        
        # Dessiner les continents (approximation simplifiée)
        self.draw_continents(draw, width, height)
        
        # Grille de coordonnées
        self.draw_grid(draw, width, height)
        
        # Ajouter les marqueurs sur la carte simple (seulement ceux visibles)
        if self.show_markers:
            visible_count = self.add_simple_markers(draw, width, height)
            self.update_info(f"Carte simple: {visible_count}/{len(self.locations)} marqueurs visibles")
        
        # Convertir pour tkinter
        self.map_photo = ImageTk.PhotoImage(self.map_image)
        self.map_canvas.create_image(width//2, height//2, image=self.map_photo)
    
    def draw_continents(self, draw, width, height):
        """Dessine les continents sur la carte simple"""
        # Afrique
        africa_points = [(width//2 + 20, height//2 - 100), (width//2 + 80, height//2 + 100)]
        draw.rectangle(africa_points, fill='lightgreen', outline='black')
        
        # Europe
        europe_points = [(width//2 + 10, height//2 - 120), (width//2 + 60, height//2 - 80)]
        draw.rectangle(europe_points, fill='lightgreen', outline='black')
        
        # Asie
        asia_points = [(width//2 + 80, height//2 - 150), (width//2 + 200, height//2 + 50)]
        draw.rectangle(asia_points, fill='lightgreen', outline='black')
        
        # Amérique du Nord
        america_n_points = [(width//2 - 200, height//2 - 120), (width//2 - 50, height//2 - 20)]
        draw.rectangle(america_n_points, fill='lightgreen', outline='black')
        
        # Amérique du Sud
        america_s_points = [(width//2 - 150, height//2 - 20), (width//2 - 80, height//2 + 120)]
        draw.rectangle(america_s_points, fill='lightgreen', outline='black')
    
    def draw_grid(self, draw, width, height):
        """Dessine la grille de coordonnées"""
        for i in range(0, width, width//12):  # Lignes de longitude
            draw.line([(i, 0), (i, height)], fill='gray', width=1)
        
        for i in range(0, height, height//6):  # Lignes de latitude
            draw.line([(0, i), (width, i)], fill='gray', width=1)
    
    def add_simple_markers(self, draw, width, height):
        """Ajoute les marqueurs sur la carte simple (seulement ceux visibles)"""
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        visible_count = 0
        
        for name, lat, lon, color, emoji in self.locations:
            # Vérifier si le marqueur est dans la vue
            if not self.is_location_in_view(lat, lon):
                continue
            
            # Convertir les coordonnées géographiques en pixels
            x = int((lon + 180) * width / 360)
            y = int((90 - lat) * height / 180)
            
            # Vérifier si le marqueur est dans les limites du canvas
            if 0 <= x <= width and 0 <= y <= height:
                # Dessiner le marqueur (cercle)
                marker_size = 8
                draw.ellipse([x-marker_size, y-marker_size, x+marker_size, y+marker_size], 
                            fill=color, outline='black', width=2)
                
                # Ajouter le label
                label = f"{emoji} {name}"
                text_bbox = draw.textbbox((0, 0), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Position du texte (au-dessus du marqueur)
                text_x = x - text_width // 2
                text_y = y - marker_size - text_height - 5
                
                # S'assurer que le texte est visible
                text_x = max(0, min(text_x, width - text_width))
                text_y = max(0, min(text_y, height - text_height))
                
                # Dessiner un fond blanc pour le texte
                draw.rectangle([text_x-2, text_y-2, text_x+text_width+2, text_y+text_height+2], 
                             fill='white', outline='black')
                
                # Dessiner le texte
                draw.text((text_x, text_y), label, fill='black', font=font)
                
                visible_count += 1
        
        return visible_count
    
    def toggle_markers(self):
        """Affiche/masque les marqueurs"""
        self.show_markers = not self.show_markers
        
        if hasattr(self, 'matplotlib_markers'):
            # Matplotlib markers
            self.update_matplotlib_markers_visibility()
        else:
            # Simple map - redessiner la carte
            self.create_simple_map()
        
        status = "affichés" if self.show_markers else "masqués"
        self.update_info(f"Marqueurs {status}")
    
    def zoom_in(self):
        """Zoom avant"""
        self.zoom_level *= 1.2
        self.zoom_label.config(text=f"{self.zoom_level:.1f}x")
        if hasattr(self, 'ax'):
            self.update_matplotlib_view()
        else:
            self.create_simple_map()
        self.update_info(f"Zoom: {self.zoom_level:.1f}x")
    
    def zoom_out(self):
        """Zoom arrière"""
        self.zoom_level /= 1.2
        if self.zoom_level < 0.5:
            self.zoom_level = 0.5
        self.zoom_label.config(text=f"{self.zoom_level:.1f}x")
        if hasattr(self, 'ax'):
            self.update_matplotlib_view()
        else:
            self.create_simple_map()
        self.update_info(f"Zoom: {self.zoom_level:.1f}x")
    
    def update_matplotlib_view(self):
        """Met à jour la vue matplotlib"""
        if hasattr(self, 'ax'):
            # Calculer les limites basées sur le zoom et la position
            extent = 180 / self.zoom_level
            self.ax.set_extent([
                self.current_lon - extent/2,
                self.current_lon + extent/2,
                self.current_lat - extent/4,
                self.current_lat + extent/4
            ], ccrs.PlateCarree())
            
            # Mettre à jour les limites de vue et la visibilité des marqueurs
            self.update_view_bounds()
            self.update_matplotlib_markers_visibility()
    
    def reset_view(self):
        """Remet la vue par défaut"""
        self.zoom_level = 1.0
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.zoom_label.config(text="1.0x")
        if hasattr(self, 'ax'):
            self.ax.set_global()
            self.update_view_bounds()
            self.update_matplotlib_markers_visibility()
        else:
            self.update_view_bounds()
            self.create_simple_map()
        self.update_coordinates()
        self.update_info("Vue remise à zéro")
    
    def center_origin(self):
        """Centre la carte sur 0,0"""
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.update_coordinates()
        if hasattr(self, 'ax'):
            self.update_matplotlib_view()
        else:
            self.create_simple_map()
        self.update_info("Carte centrée sur 0°, 0°")
    
    def go_to_location(self, lat, lon, name):
        """Va à un lieu spécifique"""
        self.current_lat = lat
        self.current_lon = lon
        self.update_coordinates()
        if hasattr(self, 'ax'):
            self.update_matplotlib_view()
        else:
            self.create_simple_map()
        self.update_info(f"Navigation vers {name}: {lat:.3f}°, {lon:.3f}°")
    
    # ... (le reste des méthodes reste identique)
    
    def on_mouse_move(self, event):
        """Gère le mouvement de la souris sur la carte simple"""
        if hasattr(self, 'canvas_widget'):
            return  # Utilise matplotlib
        
        # Calculer les coordonnées géographiques
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            # Conversion pixel -> coordonnées géographiques
            lon = ((event.x / canvas_width) - 0.5) * 360
            lat = (0.5 - (event.y / canvas_height)) * 180
            
            self.current_lat = lat
            self.current_lon = lon
            
            self.update_coordinates()
            
            # Vérifier si la souris est proche d'un marqueur visible
            self.check_marker_hover(event.x, event.y, canvas_width, canvas_height)
    
    def check_marker_hover(self, x, y, canvas_width, canvas_height):
        """Vérifie si la souris survole un marqueur visible"""
        for name, lat, lon, color, emoji in self.locations:
            # Vérifier si le marqueur est visible
            if not self.is_location_in_view(lat, lon) or not self.show_markers:
                continue
                
            # Convertir les coordonnées du marqueur en pixels
            marker_x = (lon + 180) * canvas_width / 360
            marker_y = (90 - lat) * canvas_height / 180
            
            # Vérifier la distance
            distance = ((x - marker_x) ** 2 + (y - marker_y) ** 2) ** 0.5
            
            if distance < 15:  # Zone de survol
                self.update_info(f"Survol: {emoji} {name} ({lat:.3f}°, {lon:.3f}°)")
                break
    
    def on_matplotlib_move(self, event):
        """Gère le mouvement de la souris sur la carte matplotlib"""
        if event.inaxes:
            self.current_lon = event.xdata if event.xdata else 0
            self.current_lat = event.ydata if event.ydata else 0
            self.update_coordinates()
            
            # Vérifier si la souris survole un marqueur visible
            self.check_matplotlib_marker_hover(event.xdata, event.ydata)
    
    def check_matplotlib_marker_hover(self, lon, lat):
        """Vérifie si la souris survole un marqueur matplotlib visible"""
        if lon is None or lat is None:
            return
            
        for name, m_lat, m_lon, color, emoji in self.locations:
            # Vérifier si le marqueur est visible
            if not self.is_location_in_view(m_lat, m_lon) or not self.show_markers:
                continue
                
            # Calculer la distance
            distance = ((lon - m_lon) ** 2 + (lat - m_lat) ** 2) ** 0.5
            
            if distance < 5:  # Zone de survol (en degrés)
                self.update_info(f"Survol: {emoji} {name} ({m_lat:.3f}°, {m_lon:.3f}°)")
                break
    
    def on_click(self, event):
        """Gère le clic sur la carte"""
        # Vérifier si on clique sur un marqueur visible
        clicked_location = self.find_clicked_marker(event.x, event.y)
        if clicked_location:
            name, lat, lon, color, emoji = clicked_location
            self.go_to_location(lat, lon, name)
        else:
            self.update_info(f"Clic à: {self.current_lat:.3f}°, {self.current_lon:.3f}°")
    
    def find_clicked_marker(self, x, y):
        """Trouve le marqueur cliqué (seulement parmi les visibles)"""
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()
        
        for location in self.locations:
            name, lat, lon, color, emoji = location
            
            # Vérifier si le marqueur est visible
            if not self.is_location_in_view(lat, lon) or not self.show_markers:
                continue
                
            marker_x = (lon + 180) * canvas_width / 360
            marker_y = (90 - lat) * canvas_height / 180
            
            distance = ((x - marker_x) ** 2 + (y - marker_y) ** 2) ** 0.5
            if distance < 15:
                return location
        return None
    
    def on_matplotlib_click(self, event):
        """Gère le clic sur la carte matplotlib"""
        if event.inaxes:
            lat, lon = event.ydata, event.xdata
            
            # Vérifier si on clique sur un marqueur visible
            clicked_location = self.find_matplotlib_clicked_marker(lon, lat)
            if clicked_location:
                name, m_lat, m_lon, color, emoji = clicked_location
                self.go_to_location(m_lat, m_lon, name)
            else:
                self.update_info(f"Clic à: {lat:.3f}°, {lon:.3f}°")
    
    def find_matplotlib_clicked_marker(self, lon, lat):
        """Trouve le marqueur cliqué sur matplotlib (seulement parmi les visibles)"""
        if lon is None or lat is None:
            return None
            
        for location in self.locations:
            name, m_lat, m_lon, color, emoji = location
            
            # Vérifier si le marqueur est visible
            if not self.is_location_in_view(m_lat, m_lon) or not self.show_markers:
                continue
                
            distance = ((lon - m_lon) ** 2 + (lat - m_lat) ** 2) ** 0.5
            if distance < 5:
                return location
        return None
    
    def on_mouse_wheel(self, event):
        """Gère le zoom avec la molette"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def update_coordinates(self):
        """Met à jour l'affichage des coordonnées"""
        self.lat_label.config(text=f"{self.current_lat:.3f}°")
        self.lon_label.config(text=f"{self.current_lon:.3f}°")
    
    def update_info(self, message):
        """Met à jour le texte d'information"""
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)