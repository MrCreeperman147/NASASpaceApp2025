"""
Interface graphique pour carte Folium interactive - NASASpaceApp2025
"""

import tkinter as tk
from tkinter import ttk, messagebox
import folium
from folium import plugins
import webbrowser
import tempfile
import os
from pathlib import Path
import json


class FoliumMapGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NASA Space App 2025 - Carte Folium Interactive")
        self.root.geometry("1400x900")
        
        # Variables
        self.current_lat = 0.0
        self.current_lon = 0.0
        self.zoom_level = 2
        
        # Lieux prédéfinis avec marqueurs
        self.locations = [
            {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "color": "red", "emoji": "🗼", 
             "info": "Capitale de la France, Tour Eiffel"},
            {"name": "New York", "lat": 40.7128, "lon": -74.0060, "color": "blue", "emoji": "🏙️",
             "info": "Ville emblématique des États-Unis"},
            {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "color": "green", "emoji": "🏯",
             "info": "Capitale du Japon, technologie avancée"},
            {"name": "Sydney", "lat": -33.8688, "lon": 151.2093, "color": "orange", "emoji": "🏖️",
             "info": "Opéra de Sydney, Australie"},
            {"name": "Le Caire", "lat": 30.0444, "lon": 31.2357, "color": "purple", "emoji": "🏛️",
             "info": "Pyramides d'Égypte"},
            {"name": "Brasília", "lat": -15.7939, "lon": -47.8828, "color": "brown", "emoji": "🌴",
             "info": "Capitale du Brésil"}
        ]
        
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
        control_frame = ttk.LabelFrame(main_frame, text="Contrôles Folium", padding="5")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Coordonnées et contrôles
        coord_frame = ttk.Frame(control_frame)
        coord_frame.grid(row=0, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(coord_frame, text="Centre:").grid(row=0, column=0, padx=(0, 5))
        ttk.Label(coord_frame, text="Lat:").grid(row=0, column=1, padx=(0, 2))
        self.lat_var = tk.StringVar(value="0.0")
        self.lat_entry = ttk.Entry(coord_frame, textvariable=self.lat_var, width=8)
        self.lat_entry.grid(row=0, column=2, padx=(0, 10))
        
        ttk.Label(coord_frame, text="Lon:").grid(row=0, column=3, padx=(0, 2))
        self.lon_var = tk.StringVar(value="0.0")
        self.lon_entry = ttk.Entry(coord_frame, textvariable=self.lon_var, width=8)
        self.lon_entry.grid(row=0, column=4, padx=(0, 10))
        
        ttk.Label(coord_frame, text="Zoom:").grid(row=0, column=5, padx=(0, 2))
        self.zoom_var = tk.StringVar(value="2")
        self.zoom_spinbox = ttk.Spinbox(coord_frame, textvariable=self.zoom_var, 
                                       from_=1, to=18, width=5)
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
        
        ttk.Button(btn_frame, text="🔄 Reset", 
                  command=self.reset_map).grid(row=0, column=3, padx=2)
        
        ttk.Button(btn_frame, text="📍 Ajouter Point", 
                  command=self.add_custom_marker).grid(row=0, column=4, padx=2)
        
        # Style de carte
        style_frame = ttk.LabelFrame(control_frame, text="Style de Carte", padding="5")
        style_frame.grid(row=2, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.map_style = tk.StringVar(value="CartoDB positron")
        styles = ["CartoDB positron",]
        
        for i, style in enumerate(styles):
            ttk.Radiobutton(style_frame, text=style, variable=self.map_style, 
                           value=style, command=self.change_map_style).grid(row=0, column=i, padx=5)
        
        # Lieux prédéfinis
        location_frame = ttk.LabelFrame(control_frame, text="Lieux Prédéfinis", padding="5")
        location_frame.grid(row=3, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(10, 0))
        
        for i, location in enumerate(self.locations):
            btn_text = f"{location['emoji']} {location['name']}"
            ttk.Button(location_frame, text=btn_text,
                      command=lambda loc=location: self.go_to_location(loc)).grid(
                      row=i//3, column=i%3, padx=2, pady=2)
        
        # Frame pour l'aperçu de la carte
        preview_frame = ttk.LabelFrame(main_frame, text="Aperçu de la Carte", padding="5")
        preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Zone de texte pour afficher le HTML ou des informations
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
        self.update_info("🎯 Utilisez les contrôles pour naviguer sur la carte")
        self.update_info("🌐 Cliquez sur 'Ouvrir dans Navigateur' pour voir la carte interactive")
    
    def create_folium_map(self):
        """Crée une carte Folium avec les marqueurs"""
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
            
        except ValueError as e:
            messagebox.showerror("Erreur", f"Coordonnées invalides: {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création de la carte: {e}")
    
    def add_map_tiles(self):
        """Ajoute les tuiles de carte selon le style sélectionné"""
        style = self.map_style.get()
        
        if style == "CartoDB positron":
            folium.TileLayer('CartoDB positron').add_to(self.map_object)
    
    def add_location_markers(self):
        """Ajoute les marqueurs des lieux prédéfinis"""
        for location in self.locations:
            # Créer un popup avec les informations
            popup_html = f"""
            <div style='width: 200px;'>
                <h4>{location['emoji']} {location['name']}</h4>
                <p><b>Coordonnées:</b><br>
                Lat: {location['lat']:.4f}<br>
                Lon: {location['lon']:.4f}</p>
                <p><b>Info:</b><br>{location['info']}</p>
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
        plugins.MeasureControl().add_to(self.map_object)
        
        # Plugin de mini-carte
        minimap = plugins.MiniMap()
        self.map_object.add_child(minimap)
        
        # Plugin de géolocalisation
        plugins.LocateControl().add_to(self.map_object)
        
        # Plugin de plein écran
        plugins.Fullscreen().add_to(self.map_object)
        
        # Widget d'affichage des coordonnées du curseur
        plugins.MousePosition(
            position='topright',
            separator=' | ',
            empty_string='NaN',
            lng_first=False,
            num_digits=20,
            prefix='Coordonnées: ',
            lat_formatter="function(num) {return L.Util.formatNum(num, 4) + ' °N';}",
            lng_formatter="function(num) {return L.Util.formatNum(num, 4) + ' °E';}"
        ).add_to(self.map_object)
        
        # Ajouter un contrôle de couches
        folium.LayerControl().add_to(self.map_object)
    
    def show_map_preview(self):
        """Affiche un aperçu des informations de la carte"""
        if self.map_object:
            # Informations sur la carte
            info = f"""
    📍 CARTE FOLIUM GÉNÉRÉE

    🎯 Centre: {self.lat_var.get()}, {self.lon_var.get()}
    🔍 Zoom: {self.zoom_var.get()}
    🎨 Style: {self.map_style.get()}
    📍 Marqueurs: {len(self.locations)} lieux

    🏷️ LIEUX INCLUS:
    """
            for location in self.locations:
                info += f"  {location['emoji']} {location['name']} ({location['lat']}, {location['lon']})\n"
            
            info += f"""
    🔧 PLUGINS INCLUS:
    • Mesure de distance
    • Mini-carte
    • Géolocalisation
    • Mode plein écran
    • Affichage coordonnées curseur
    • Contrôle des couches

    💡 Cliquez sur 'Ouvrir dans Navigateur' pour voir la carte interactive!
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
                os.unlink(self.temp_map_file)
            
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
        """Remet la carte à zéro"""
        self.lat_var.set("0.0")
        self.lon_var.set("0.0")
        self.zoom_var.set("2")
        self.map_style.set("OpenStreetMap")
        self.create_folium_map()
        self.update_info("🔄 Carte remise à zéro")
    
    def change_map_style(self):
        """Change le style de la carte"""
        self.create_folium_map()
        self.update_info(f"🎨 Style changé: {self.map_style.get()}")
    
    def go_to_location(self, location):
        """Va à un lieu spécifique"""
        self.lat_var.set(str(location['lat']))
        self.lon_var.set(str(location['lon']))
        self.zoom_var.set("10")
        self.create_folium_map()
        self.update_info(f"🎯 Navigation vers {location['emoji']} {location['name']}")
    
    def add_custom_marker(self):
        """Ajoute un marqueur personnalisé"""
        # Fenêtre de dialogue pour ajouter un marqueur
        dialog = tk.Toplevel(self.root)
        dialog.title("Ajouter un marqueur")
        dialog.geometry("300x250")
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
        ttk.Entry(dialog, textvariable=name_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Latitude:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=lat_var, width=20).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Longitude:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=lon_var, width=20).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Couleur:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        color_combo = ttk.Combobox(dialog, textvariable=color_var, 
                                  values=["red", "blue", "green", "purple", "orange", "darkred", "lightred"])
        color_combo.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Description:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(dialog, textvariable=info_var, width=20).grid(row=4, column=1, padx=5, pady=5)
        
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