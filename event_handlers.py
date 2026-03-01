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

class EventHandlersMixin:
    def on_canvas_motion(self, event):
        if self.paint_mode.get() or getattr(self, "drag_item_index", None) is not None:
            if self.hovered_item_index is not None:
                self.hovered_item_index = None
                self.canvas.delete("tooltip")
            return

        cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        world_x = (event.x - cx) / self.scale + self.camera_x
        world_y = (event.y - cy) / self.scale + self.camera_y
        
        gx = self.map_state.grid_offset_x
        gy = self.map_state.grid_offset_y
        q, r = self.grid.pixel_to_hex(world_x - gx, world_y - gy)
        
        found = -1
        for i in range(len(self.map_state.items) - 1, -1, -1):
            item = self.map_state.items[i]
            if item["q"] == q and item["r"] == r and self.is_combatant(item):
                found = i
                break

        if self.hovered_item_index != found:
            self.hovered_item_index = found if found != -1 else None
            self.update_hover_tooltip(event.x, event.y)
        elif self.hovered_item_index is not None:
            self.move_hover_tooltip(event.x, event.y)

    def on_canvas_click(self, event):
        cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        
        # Screen to World
        world_x = (event.x - cx) / self.scale + self.camera_x
        world_y = (event.y - cy) / self.scale + self.camera_y
        
        if self.paint_mode.get():
            if self.paint_color.get() == "eraser":
                self.erase_at(world_x, world_y)
                return
            self.current_drawing = {"color": self.paint_color.get(), "points": [{"x": world_x, "y": world_y}]}
            self.map_state.drawings.append(self.current_drawing)
            return
        
        # Adjust for grid offset before converting to Hex
        gx = self.map_state.grid_offset_x
        gy = self.map_state.grid_offset_y
        
        q, r = self.grid.pixel_to_hex(world_x - gx, world_y - gy)
        
        if self.selected_asset_path:
            # PLACE MODE
            # Parse Size
            size = self.parse_size_from_filename(self.selected_asset_path)
            
            if self.app_mode.get() == "WEBER_NHP":
                user_sz = simpledialog.askfloat("Token Size", f"Enter token size (1 = 1 hex) for:\n{os.path.basename(self.selected_asset_path)}", initialvalue=size, minvalue=0.1)
                if user_sz is None:
                    return # User cancelled
                size = user_sz
            
            # Lancer Scaling
            scale_map = {0.5: 0.8, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}
            scale = scale_map.get(size, float(size))
            
            self.map_state.add_item(self.selected_asset_path, q, r, scale=scale)
            self.draw_wrapper()
        else:
            # SELECT MODE
            # Find item at q, r
            # Iterate backwards to select top-most
            found = -1
            for i in range(len(self.map_state.items) - 1, -1, -1):
                item = self.map_state.items[i]
                # Simple hit test: Exact hex match
                # For larger items, this might be tricky (they occupy multiple hexes).
                # For now, select by anchor hex.
                if item["q"] == q and item["r"] == r:
                    found = i
                    break
            
            self.selected_item_index = found if found != -1 else None
            self.drag_item_index = self.selected_item_index # Prepare for drag
            
            if self.drag_item_index is not None and self.drag_item_index == getattr(self, "active_turn_idx", None):
                self.drag_start_hex = (self.map_state.items[self.drag_item_index]["q"], self.map_state.items[self.drag_item_index]["r"])
            else:
                self.drag_start_hex = None
                
            self.update_attachment_ui()
            self.draw_wrapper()

    def on_canvas_right_click(self, event):
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._cam_start_x = self.camera_x
        self._cam_start_y = self.camera_y

    def on_canvas_pan(self, event):
        # Delta screen px
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        
        self.camera_x = self._cam_start_x - dx / self.scale
        self.camera_y = self._cam_start_y - dy / self.scale
        
        self.draw_wrapper()

    def on_zoom(self, event):
        # Windows: event.delta. Linux: Button-4/5
        scale_mult = 1.1
        if event.num == 5 or event.delta < 0:
            self.scale /= scale_mult
        else:
            self.scale *= scale_mult
        
        self.draw_wrapper()

    def on_canvas_drag(self, event):
        cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        world_x = (event.x - cx) / self.scale + self.camera_x
        world_y = (event.y - cy) / self.scale + self.camera_y
        
        if self.paint_mode.get():
            if self.paint_color.get() == "eraser":
                self.erase_at(world_x, world_y)
                return
            if self.current_drawing is not None:
                self.current_drawing["points"].append({"x": world_x, "y": world_y})
                self.draw_wrapper()
            return
            
        # If in select mode and dragging item
        if not self.selected_asset_path and self.drag_item_index is not None:
            gx = self.map_state.grid_offset_x
            gy = self.map_state.grid_offset_y
            q, r = self.grid.pixel_to_hex(world_x - gx, world_y - gy)
            
            # Update item pos
            if 0 <= self.drag_item_index < len(self.map_state.items):
                self.map_state.items[self.drag_item_index]["q"] = q
                self.map_state.items[self.drag_item_index]["r"] = r
                self.draw_wrapper()

    def on_canvas_release(self, event):
        if self.paint_mode.get():
            self.current_drawing = None
            self.draw_wrapper()
            return
            
        if getattr(self, "drag_item_index", None) is not None and getattr(self, "drag_item_index", None) == getattr(self, "active_turn_idx", None):
            item = self.map_state.items[self.drag_item_index]
            if getattr(self, "drag_start_hex", None):
                q1, r1 = self.drag_start_hex
                q2, r2 = item["q"], item["r"]
                dist = int((abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) / 2)
                if dist > 0:
                    current_mov = self.val_movement.get()
                    if dist > current_mov:
                        item["q"], item["r"] = q1, r1
                        self.log_to_terminal(f"> Movement failed: Need {dist} spaces, but only {current_mov} left!")
                        self.draw_wrapper()
                    else:
                        self.val_movement.set(max(0, current_mov - dist))
                        name = self.get_token_name(self.drag_item_index)
                        self.log_to_terminal(f"> {name} moved {dist} spaces. ({self.val_movement.get()} left)")
                        
                        # Update drag start hex so that subsequent dragging calculates again
                        self.drag_start_hex = (q2, r2)
                    
        self.drag_item_index = None

