"""
Interface graphique pour le traitement d'images - NASASpaceApp2025
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

# Import de la classe ImageProcessor
from src.image_processing import ImageProcessor


class ImageProcessingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NASA Space App 2025 - Traitement d'Images")
        self.root.geometry("1200x800")
        
        # Variables
        self.current_image = None
        self.original_image = None
        self.processor = ImageProcessor()
        
        self.setup_gui()
    
    def setup_gui(self):
        """Configure l'interface graphique"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration des poids pour redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Frame des contrôles
        control_frame = ttk.LabelFrame(main_frame, text="Contrôles", padding="5")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Boutons principaux
        ttk.Button(control_frame, text="Importer Image", 
                  command=self.import_image).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(control_frame, text="Sauvegarder", 
                  command=self.save_image).grid(row=0, column=1, padx=5)
        
        ttk.Button(control_frame, text="Reset", 
                  command=self.reset_image).grid(row=0, column=2, padx=5)
        
        # Frame des filtres
        filter_frame = ttk.LabelFrame(control_frame, text="Filtres", padding="5")
        filter_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(filter_frame, text="Gaussien", 
                  command=lambda: self.apply_filter('gaussian')).grid(row=0, column=0, padx=2)
        
        ttk.Button(filter_frame, text="Médian", 
                  command=lambda: self.apply_filter('median')).grid(row=0, column=1, padx=2)
        
        ttk.Button(filter_frame, text="Sobel", 
                  command=lambda: self.apply_filter('sobel')).grid(row=0, column=2, padx=2)
        
        ttk.Button(filter_frame, text="Détection Contours", 
                  command=self.detect_edges).grid(row=0, column=3, padx=2)
        
        ttk.Button(filter_frame, text="Améliorer Contraste", 
                  command=self.enhance_contrast).grid(row=0, column=4, padx=2)
        
        # Frame de redimensionnement
        resize_frame = ttk.LabelFrame(filter_frame, text="Redimensionner", padding="5")
        resize_frame.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(resize_frame, text="Taille:").grid(row=0, column=0)
        self.size_var = tk.StringVar(value="512x512")
        size_combo = ttk.Combobox(resize_frame, textvariable=self.size_var, 
                                 values=["128x128", "256x256", "512x512", "1024x1024"])
        size_combo.grid(row=0, column=1, padx=5)
        
        ttk.Button(resize_frame, text="Redimensionner", 
                  command=self.resize_image).grid(row=0, column=2, padx=5)
        
        # Frame pour l'image originale
        original_frame = ttk.LabelFrame(main_frame, text="Image Originale", padding="5")
        original_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        original_frame.columnconfigure(0, weight=1)
        original_frame.rowconfigure(0, weight=1)
        
        self.original_canvas = tk.Canvas(original_frame, bg='white', width=400, height=400)
        self.original_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame pour l'image traitée
        processed_frame = ttk.LabelFrame(main_frame, text="Image Traitée", padding="5")
        processed_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        processed_frame.columnconfigure(0, weight=1)
        processed_frame.rowconfigure(0, weight=1)
        
        self.processed_canvas = tk.Canvas(processed_frame, bg='white', width=400, height=400)
        self.processed_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame d'informations
        info_frame = ttk.LabelFrame(main_frame, text="Informations", padding="5")
        info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.info_text = tk.Text(info_frame, height=5, width=80)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Scrollbar pour le texte d'info
        scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=scrollbar.set)
    
    def import_image(self):
        """Importe une image"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner une image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.tiff *.bmp"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Charger l'image avec le processeur
                self.original_image = self.processor.load_image(file_path)
                self.current_image = self.original_image.copy()
                
                # Afficher l'image
                self.display_image(self.original_image, self.original_canvas)
                self.display_image(self.current_image, self.processed_canvas)
                
                # Afficher les informations
                self.update_info(f"Image chargée: {file_path}")
                self.update_info(f"Dimensions: {self.original_image.shape}")
                self.update_info(f"Type: {self.original_image.dtype}")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de charger l'image:\n{str(e)}")
    
    def display_image(self, image, canvas):
        """Affiche une image dans un canvas"""
        if image is None:
            return
        
        # Redimensionner l'image pour l'affichage
        h, w = image.shape[:2]
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width, canvas_height = 400, 400
        
        # Calculer le ratio pour maintenir les proportions
        ratio = min(canvas_width/w, canvas_height/h)
        new_w, new_h = int(w*ratio), int(h*ratio)
        
        # Préparer l'image pour l'affichage
        if len(image.shape) == 3:
            # Image couleur - PIL charge en RGB, pas besoin de conversion BGR->RGB
            display_img = image
        else:
            # Image en niveaux de gris - convertir en RGB pour l'affichage
            display_img = np.stack([image, image, image], axis=-1)
        
        # S'assurer que les valeurs sont dans la bonne plage
        if display_img.dtype == np.float64 or display_img.dtype == np.float32:
            if display_img.max() <= 1.0:
                display_img = (display_img * 255)
        
        # Convertir en uint8
        display_img = display_img.astype('uint8')
        
        # Redimensionner pour l'affichage
        display_img = cv2.resize(display_img, (new_w, new_h))
        
        # Convertir pour Tkinter
        pil_image = Image.fromarray(display_img)
        
        # Stocker la référence pour éviter la garbage collection
        if canvas == self.original_canvas:
            self.original_photo = ImageTk.PhotoImage(pil_image)
            photo_ref = self.original_photo
        else:
            self.processed_photo = ImageTk.PhotoImage(pil_image)
            photo_ref = self.processed_photo
        
        # Afficher dans le canvas
        canvas.delete("all")
        canvas.create_image(canvas_width//2, canvas_height//2, 
                          image=photo_ref, anchor=tk.CENTER)
    
    def apply_filter(self, filter_name):
        """Applique un filtre à l'image"""
        if self.current_image is None:
            messagebox.showwarning("Attention", "Veuillez d'abord importer une image")
            return
        
        try:
            # Convertir en niveaux de gris si nécessaire
            if len(self.current_image.shape) == 3:
                gray_image = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = self.current_image
            
            # Appliquer le filtre avec la classe ImageProcessor
            filtered_image = self.processor.apply_filter(gray_image, filter_name)
            
            # Normaliser si nécessaire
            if filtered_image.max() <= 1.0:
                filtered_image = (filtered_image * 255).astype(np.uint8)
            
            self.current_image = filtered_image
            self.display_image(self.current_image, self.processed_canvas)
            self.update_info(f"Filtre appliqué: {filter_name}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'application du filtre:\n{str(e)}")
    
    def detect_edges(self):
        """Détecte les contours"""
        if self.current_image is None:
            messagebox.showwarning("Attention", "Veuillez d'abord importer une image")
            return
        
        try:
            edges = self.processor.detect_edges(self.current_image)
            self.current_image = edges
            self.display_image(self.current_image, self.processed_canvas)
            self.update_info("Détection de contours appliquée")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la détection de contours:\n{str(e)}")
    
    def enhance_contrast(self):
        """Améliore le contraste"""
        if self.current_image is None:
            messagebox.showwarning("Attention", "Veuillez d'abord importer une image")
            return
        
        try:
            # Convertir en niveaux de gris si nécessaire
            if len(self.current_image.shape) == 3:
                gray_image = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2GRAY)
            else:
                gray_image = self.current_image
            
            enhanced = self.processor.enhance_contrast(gray_image)
            enhanced = (enhanced * 255).astype(np.uint8)
            
            self.current_image = enhanced
            self.display_image(self.current_image, self.processed_canvas)
            self.update_info("Contraste amélioré")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'amélioration du contraste:\n{str(e)}")
    
    def resize_image(self):
        """Redimensionne l'image"""
        if self.current_image is None:
            messagebox.showwarning("Attention", "Veuillez d'abord importer une image")
            return
        
        try:
            size_str = self.size_var.get()
            width, height = map(int, size_str.split('x'))
            
            resized_image = self.processor.resize(self.current_image, (width, height))
            self.current_image = resized_image
            
            self.display_image(self.current_image, self.processed_canvas)
            self.update_info(f"Image redimensionnée à: {width}x{height}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du redimensionnement:\n{str(e)}")
    
    def save_image(self):
        """Sauvegarde l'image traitée"""
        if self.current_image is None:
            messagebox.showwarning("Attention", "Aucune image à sauvegarder")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Sauvegarder l'image",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("TIFF", "*.tiff"),
                ("BMP", "*.bmp"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.processor.save_image(self.current_image, file_path)
                self.update_info(f"Image sauvegardée: {file_path}")
                messagebox.showinfo("Succès", "Image sauvegardée avec succès!")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde:\n{str(e)}")
    
    def reset_image(self):
        """Remet l'image à son état original"""
        if self.original_image is None:
            messagebox.showwarning("Attention", "Aucune image originale disponible")
            return
        
        self.current_image = self.original_image.copy()
        self.display_image(self.current_image, self.processed_canvas)
        self.update_info("Image remise à l'état original")
    
    def update_info(self, message):
        """Met à jour le texte d'information"""
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)