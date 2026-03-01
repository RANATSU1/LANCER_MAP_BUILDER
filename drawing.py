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

class DrawingMixin:
    def draw_wrapper(self):
        self.draw()

    def clear_paint(self):
        self.map_state.drawings = []
        self.draw_wrapper()

    def draw(self):
        self.canvas.delete("all")
        self._tk_refs = [] # Clear references
        
        cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        
        gx = self.map_state.grid_offset_x
        gy = self.map_state.grid_offset_y
        
        bg_w, bg_h = None, None
        # Draw Background Image (Behind Grid)
        if hasattr(self.map_state, 'background_image') and self.map_state.background_image:
            bg_img = self.get_image(self.map_state.background_image)
            if bg_img:
                orig_w, orig_h = bg_img.size
                bg_w, bg_h = orig_w, orig_h
                display_w = int(orig_w * self.scale)
                display_h = int(orig_h * self.scale)
                
                sx = (0 - self.camera_x) * self.scale + cx
                sy = (0 - self.camera_y) * self.scale + cy
                
                try:
                    resized_bg = bg_img.resize((display_w, display_h), Image.Resampling.NEAREST)
                    tk_bg_img = ImageTk.PhotoImage(resized_bg)
                    self._tk_refs.append(tk_bg_img)
                    self.canvas.create_image(sx, sy, image=tk_bg_img, anchor="nw", tags="background")
                except Exception as e:
                    print(f"Error resizing background: {e}")
        
        # Grid Drawing
        q_center, r_center = self.grid.pixel_to_hex(self.camera_x - gx, self.camera_y - gy)
        range_rad = 20 # Draw radius
        
        for q in range(int(q_center - range_rad), int(q_center + range_rad)):
            for r in range(int(r_center - range_rad), int(r_center + range_rad)):
                # Convert hex to pixel (World Space RELATIVE TO GRID ORIGIN)
                wx, wy = self.grid.hex_to_pixel(q, r)
                
                # Apply Grid Offset to get Absolute World Space
                wx += gx
                wy += gy
                
                # Restrict grid to background image in WEBER mode
                if self.app_mode.get() == "WEBER_NHP" and bg_w is not None and bg_h is not None:
                    # check if hex center is outside boundaries (with a little margin)
                    if not (-self.grid.size <= wx <= bg_w + self.grid.size and -self.grid.size <= wy <= bg_h + self.grid.size):
                        continue

                # World to Screen
                sx = (wx - self.camera_x) * self.scale + cx
                sy = (wy - self.camera_y) * self.scale + cy
                
                # Check if visible (roughly)
                if not (-100 < sx < self.canvas.winfo_width() + 100 and -100 < sy < self.canvas.winfo_height() + 100):
                    continue

                # Draw Polygon
                size = self.grid.size * self.scale
                pts = []
                for i in range(6):
                    angle_deg = 60 * i - 30 if self.grid.flat_top else 60 * i
                    angle_rad = math.radians(angle_deg)
                    pts.append(sx + size * math.cos(angle_rad))
                    pts.append(sy + size * math.sin(angle_rad))
                self.canvas.create_polygon(pts, outline=self.map_state.grid_color, fill="", tags="grid", outlinestipple="gray50")

        # Draw Items with Z-Index (Tiles first, then Tokens)

        # Split items
        tiles = []
        tokens = []
        
        # Store index to keep track of selection
        for idx, item in enumerate(self.map_state.items):
            if self.is_combatant(item):
                tokens.append((idx, item))
            else:
                tiles.append((idx, item))
        
        # Draw function to avoid duplication
        def draw_item_obj(idx, item):
            path = item["path"]
            
            occupied = self.get_occupied_hexes(item)
            avg_wx, avg_wy = 0, 0
            for hq, hr in occupied:
                hx, hy = self.grid.hex_to_pixel(hq, hr)
                avg_wx += hx
                avg_wy += hy
                
            wx = avg_wx / len(occupied) + gx
            wy = avg_wy / len(occupied) + gy
            
            sx = (wx - self.camera_x) * self.scale + cx
            sy = (wy - self.camera_y) * self.scale + cy
            
            # Simple visibility check
            if not (-200 < sx < self.canvas.winfo_width() + 200 and -200 < sy < self.canvas.winfo_height() + 200):
                return

            pil_img = self.get_image(path)
            if pil_img:
                # Calculate display size
                base_size = self.grid.width * self.scale
                item_scale = item.get("scale", 1.0)
                display_w = int(base_size * item_scale)
                
                orig_w, orig_h = pil_img.size
                if orig_w == 0: return
                ratio = orig_h / orig_w
                display_h = int(display_w * ratio)
                
                try:
                    resized = pil_img.resize((display_w, display_h), Image.Resampling.NEAREST)
                    tk_img = ImageTk.PhotoImage(resized)
                    self._tk_refs.append(tk_img)
                    
                    self.canvas.create_image(sx, sy, image=tk_img, anchor="center")
                    
                    faction = item.get("faction", "Neutral")
                    # Team border removed as per user request
                    
                    # Selection Highlight
                    if idx == self.selected_item_index:
                        # Draw bounding box
                        self.canvas.create_rectangle(
                            sx - display_w/2, sy - display_h/2, 
                            sx + display_w/2, sy + display_h/2, 
                            outline="cyan", width=3
                        )
                        
                    # Render Hex Barrier
                    if item.get("hex_barrier"):
                        brange = item.get("barrier_radius", 1)
                        current = set(occupied)
                        for _ in range(brange):
                            nxt = set(current)
                            for (hq, hr) in current:
                                for dq, dr in [(1,0), (1,-1), (0,-1), (-1,0), (-1,1), (0,1)]:
                                    nxt.add((hq+dq, hr+dr))
                            current = nxt
                            
                        # Draw individual hexes for barrier
                        h_size = self.grid.size * self.scale
                        barrier_hexes = current - occupied
                        for (bq, br) in barrier_hexes:
                            bx, by = self.grid.hex_to_pixel(bq, br)
                            bx += gx
                            by += gy
                            bsx = (bx - self.camera_x) * self.scale + cx
                            bsy = (by - self.camera_y) * self.scale + cy
                            
                            b_pts = []
                            for i in range(6):
                                angle_deg = 60 * i - 30 if self.grid.flat_top else 60 * i
                                angle_rad = math.radians(angle_deg)
                                b_pts.append(bsx + h_size * math.cos(angle_rad))
                                b_pts.append(bsy + h_size * math.sin(angle_rad))
                            self.canvas.create_polygon(b_pts, outline="#00ffff", width=3, fill="", tags="barrier", dash=(4, 4))
                            self.canvas.create_polygon(b_pts, outline="#00ffff", width=1, fill="", tags="barrier")
                        
                    # Render Markers
                    markers = item.get("markers", [])
                    if markers:
                        marker_size = max(16, int(display_w * 0.35))
                        total_w = (len(markers) - 1) * marker_size * 1.1
                        start_x = sx - total_w / 2
                        m_y = sy + display_h / 2
                        
                        for i, m_path in enumerate(markers):
                            m_img = self.get_image(m_path)
                            if m_img:
                                m_x = start_x + i * marker_size * 1.1
                                try:
                                    m_resized = m_img.resize((marker_size, marker_size), Image.Resampling.LANCZOS)
                                    tk_m_img = ImageTk.PhotoImage(m_resized)
                                    self._tk_refs.append(tk_m_img)
                                    self.canvas.create_image(m_x, m_y, image=tk_m_img, anchor="center")
                                except Exception as e:
                                    print(f"Error drawing marker: {e}")
                                    
                except Exception as e:
                    print(f"Error resizing: {e}")

        # Render Tiles
        for idx, item in tiles:
            draw_item_obj(idx, item)
            
        # Render Paint Drawings
        for line in self.map_state.drawings:
            if len(line["points"]) > 1:
                pts = []
                for p in line["points"]:
                    pts.append((p["x"] - self.camera_x) * self.scale + cx)
                    pts.append((p["y"] - self.camera_y) * self.scale + cy)
                self.canvas.create_line(pts, fill=line.get("color", "white"), width=3, smooth=True)
            
        # Render Tokens
        for idx, item in tokens:
            draw_item_obj(idx, item)

    def update_hover_tooltip(self, x, y):
        self.canvas.delete("tooltip")
        if self.hovered_item_index is not None:
            idx = self.hovered_item_index
            item = self.map_state.items[idx]
            
            lines = [f"NAME: {self.get_token_name(idx)}"]
            
            if item.get("pilot", ""): lines.append(f">PILOT: {item['pilot']}")
            if item.get("ll", ""): lines.append(f">LL: {item['ll']}")
                
            stats = []
            if "hp" in item or "max_hp" in item:
                stats.append(f"  >HP: {item.get('hp', '-')}/{item.get('max_hp', '-')}")
            if "structure" in item:
                stats.append(f"  >ST: {item.get('structure', '-')}")
            if "evasion" in item:
                stats.append(f"  >EV: {item.get('evasion', '-')}")
            if "e_defense" in item:
                stats.append(f"  >E-DEF: {item.get('e_defense', '-')}")
            if "speed" in item:
                stats.append(f"  >SP: {item.get('speed', '-')}")
            if "repair_cap" in item:
                stats.append(f"  >REP: {item.get('repair_cap', '-')}")
            if "heat_cap" in item:
                stats.append(f"  >HEAT: {item.get('heat_cap', '-')}")
                
            if stats:
                lines.append(">STATS:")
                lines.extend(stats)
                
            if item.get("talents"):
                lines.append(">TALENTS:")
                for talent in item["talents"]:
                    lines.append(f"  >{talent}")
                
            text = "\n".join(lines)
            
            # Text first to get bbox
            tx = self.canvas.create_text(x + 15, y + 15, text=text, anchor="nw", font=("Consolas", 10, "bold"), fill=self.map_state.ui_fg_color, tags=("tooltip", "tooltip_text"))
            bbox = self.canvas.bbox(tx)
            
            # Background
            self.canvas.create_rectangle(bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5, fill=self.map_state.ui_bg_color, outline=self.map_state.ui_fg_color, width=2, tags=("tooltip", "tooltip_bg"))
            
            # Pointer arrow to cursor
            self.canvas.create_polygon(x, y, bbox[0]-5, bbox[1]+10, bbox[0]+10, bbox[1]-5, fill=self.map_state.ui_bg_color, outline=self.map_state.ui_fg_color, width=1, tags=("tooltip", "tooltip_arrow"))
            
            self.canvas.tag_raise("tooltip_bg")
            self.canvas.tag_raise("tooltip_arrow")
            self.canvas.tag_raise("tooltip_text")
            
            self.tooltip_x = x
            self.tooltip_y = y

    def move_hover_tooltip(self, x, y):
        dx = x - self.tooltip_x
        dy = y - self.tooltip_y
        self.canvas.move("tooltip", dx, dy)
        self.tooltip_x = x
        self.tooltip_y = y

    def erase_at(self, wx, wy):
        radius = 20 / self.scale # Erase radius
        modified = False
        remaining = []
        for line in self.map_state.drawings:
            removed = False
            for p in line["points"]:
                dist = math.hypot(p["x"] - wx, p["y"] - wy)
                if dist < radius:
                    removed = True
                    break
            if not removed:
                remaining.append(line)
            else:
                modified = True
        if modified:
            self.map_state.drawings = remaining
            self.draw_wrapper()

