import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageDraw
import os
import math
import json
import random
import re

from assets import scan_assets, ASSET_ROOT
from grid import HexGrid
from map_state import MapState

class FileOpsMixin:
    def save_map(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Map", "*.json")])
        if f:
            self.map_state.save_to_file(f)
            messagebox.showinfo("Saved", "Map saved successfully!")

    def export_map(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".png", 
            filetypes=[("PNG Files", "*.png"), ("JPEG Files", "*.jpg *.jpeg"), ("WebP Files", "*.webp"), ("BMP Files", "*.bmp"), ("All Files", "*.*")],
            title="Export Map as Image"
        )
        if not f: return
        
        self.canvas.update()
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        from PIL import ImageGrab
        try:
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            img.save(f)
            messagebox.showinfo("Export Map", f"Map exported successfully to:\n{f}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export map: {e}")

    def resolve_missing_asset_paths(self):
        known_images = {}
        known_text = {}
        
        def scan_dir_for_files(dir_path):
            if not dir_path or not os.path.exists(dir_path): return
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    lower_f = file.lower()
                    full_p = os.path.join(root, file)
                    if lower_f.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif')):
                        known_images[file] = full_p
                    elif lower_f.endswith(('.txt', '.md', '.json')):
                        known_text[file] = full_p
                        
        scan_dir_for_files(self.map_state.tokens_directory)
        scan_dir_for_files(self.map_state.markers_directory)
        
        for item in self.map_state.items:
            path = item.get("path")
            if path and not os.path.exists(path):
                fname = os.path.basename(path)
                if fname in known_images:
                    item["path"] = known_images[fname]
                    
            linked = item.get("linked_file")
            if linked and not os.path.exists(linked):
                lname = os.path.basename(linked)
                if lname in known_text:
                    item["linked_file"] = known_text[lname]
                    
        bg_img = self.map_state.background_image
        if bg_img and type(bg_img) == str and not os.path.exists(bg_img):
            bname = os.path.basename(bg_img)
            if bname in known_images:
                self.map_state.background_image = known_images[bname]

    def load_by_file(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Map", "*.json")])
        if f:
            self.map_state.load_from_file(f)
            self.save_global_settings() # Auto-update UI settings from loaded map
            self.assets = scan_assets(self.map_state.tokens_directory)
            self.resolve_missing_asset_paths()
            self.populate_tree()
            self.apply_theme()
            # Update grid controls
            self.grid_size_var.set(self.map_state.grid_size)
            self.offset_x_var.set(self.map_state.grid_offset_x)
            self.offset_y_var.set(self.map_state.grid_offset_y)
            self.grid.size = self.map_state.grid_size
            self.draw_wrapper()

    def clear_map(self):
        if messagebox.askyesno("Clear Map", "Are you sure?"):
            self.map_state.clear()
            self.draw_wrapper()

