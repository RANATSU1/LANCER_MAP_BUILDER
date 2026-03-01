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

class UtilsMixin:
    def load_global_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                if "ui_bg_color" in data: self.map_state.ui_bg_color = data["ui_bg_color"]
                if "ui_fg_color" in data: self.map_state.ui_fg_color = data["ui_fg_color"]
                if "tokens_directory" in data: self.map_state.tokens_directory = data["tokens_directory"]
                if "markers_directory" in data: self.map_state.markers_directory = data["markers_directory"]
                if "app_mode" in data: self.app_mode.set(data["app_mode"])
            except Exception as e:
                print(f"Error loading global settings: {e}")

    def save_global_settings(self):
        try:
            data = {
                "ui_bg_color": self.map_state.ui_bg_color,
                "ui_fg_color": self.map_state.ui_fg_color,
                "tokens_directory": self.map_state.tokens_directory,
                "markers_directory": self.map_state.markers_directory,
                "app_mode": self.app_mode.get()
            }
            with open(self.settings_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving global settings: {e}")

    def is_combatant(self, item):
        if item.get("type", "") == "token": return True
        p = item.get("path", "").lower()
        if "token" in p or "frame" in p: return True
        if any(k in item for k in ('hp', 'max_hp', 'structure', 'speed', 'evasion', 'repair_cap', 'heat_cap')): return True
        if item.get("faction", "Neutral") != "Neutral": return True
        return False

    def get_token_name(self, idx):
        item = self.map_state.items[idx]
        if item.get("custom_name"):
            return item["custom_name"]
        elif item.get("linked_file"):
            return os.path.basename(item["linked_file"]).split('.')[0][:15]
        else:
            return os.path.basename(item["path"]).split('.')[0][:15]

    def get_selected_name(self):
        if self.selected_item_index is None: return "Unknown"
        return self.get_token_name(self.selected_item_index)

    def get_index_from_cb(self, cb_str):
        import re
        if not cb_str: return None
        m = re.match(r'^\[(\d+)\]', cb_str)
        if m: return int(m.group(1))
        return None

    def get_image(self, path):
        if path not in self.loaded_images:
            try:
                img = Image.open(path)
                self.loaded_images[path] = img
            except Exception as e:
                print(f"Error loading image {path}: {e}")
                return None
        return self.loaded_images[path]

    def get_occupied_hexes(self, item):
        q, r = item["q"], item["r"]
        s = round(item.get("scale", 1.0))
        occupied = set([(q, r)])
        
        if self.is_combatant(item):
            if s == 2:
                # Size 2 is exactly 3 hexes (a small triangle)
                occupied.add((q+1, r))
                occupied.add((q, r+1))
            elif s == 3:
                # Size 3 is exactly 7 hexes (center + 1 ring)
                for dq, dr in [(1,0), (1,-1), (0,-1), (-1,0), (-1,1), (0,1)]:
                    occupied.add((q+dq, r+dr))
            elif s >= 4:
                # Size 4+
                for dq in range(-2, 3):
                    for dr in range(max(-2, -dq-2), min(2, -dq+2) + 1):
                        occupied.add((q+dq, r+dr))
        return occupied

    def parse_size_from_filename(self, path):
        filename = os.path.basename(path).lower()
        
        # Check for fractional size "Size 1/2" or "Size 0.5"
        if "size 1/2" in filename or "size 0.5" in filename:
            return 0.5

        # Look for "Size X"
        import re
        match = re.search(r"size\s*(\d)", filename)
        if match:
            return int(match.group(1))
        
        # Heuristic for Tiles?
        # If it's a tile, default 1.
        return 1

