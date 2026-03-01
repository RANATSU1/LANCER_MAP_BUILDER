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

class UiActionsMixin:
    def toggle_hex_barrier(self, event=None):
        if self.selected_item_index is not None:
            item = self.map_state.items[self.selected_item_index]
            item["hex_barrier"] = not item.get("hex_barrier", False)
            self.draw_wrapper()

    def change_tokens_directory(self, top):
        top.destroy()
        dir_path = filedialog.askdirectory(title="Select Tokens Directory", initialdir=self.map_state.tokens_directory)
        if dir_path:
            self.map_state.tokens_directory = dir_path
            self.assets = scan_assets(dir_path)
            self.populate_tree()
            self.save_global_settings()

    def change_markers_directory(self, top):
        top.destroy()
        dir_path = filedialog.askdirectory(title="Select Markers Directory", initialdir=self.map_state.markers_directory)
        if dir_path:
            self.map_state.markers_directory = dir_path
            self.save_global_settings()

    def open_settings_overlay(self):
        top = tk.Toplevel(self.root)
        top.title("Settings")
        top.geometry("250x230")
        top.configure(bg=self.map_state.ui_bg_color)
        top.transient(self.root)
        top.grab_set()
        
        # Center the dialog
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 125
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        top.geometry(f"+{x}+{y}")
        
        ttk.Label(top, text="Map Builder Settings", anchor="center").pack(fill="x", pady=10)
        
        mode_frame = ttk.Frame(top)
        mode_frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(mode_frame, text="Mode:").pack(side="left")
        cb = ttk.Combobox(mode_frame, textvariable=self.app_mode, values=["GUSTAV_NHP", "WEBER_NHP"], state="readonly", width=12)
        cb.pack(side="right", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: self.save_global_settings())

        ttk.Button(top, text="Tokens Directory", command=lambda: self.change_tokens_directory(top)).pack(fill="x", padx=20, pady=5)
        ttk.Button(top, text="Markers Directory", command=lambda: self.change_markers_directory(top)).pack(fill="x", padx=20, pady=5)
        ttk.Button(top, text="UI Colors", command=lambda: self.open_ui_settings(top)).pack(fill="x", padx=20, pady=5)

    def open_ui_settings(self, top=None):
        if top:
            top.destroy()
        bg = colorchooser.askcolor(title="Background Color", initialcolor=self.map_state.ui_bg_color)
        if bg[1]:
            self.map_state.ui_bg_color = bg[1]
        fg = colorchooser.askcolor(title="Foreground/Accent Color", initialcolor=self.map_state.ui_fg_color)
        if fg[1]:
            self.map_state.ui_fg_color = fg[1]
            
        self.apply_theme()
        self.save_global_settings()

    def _hide_all_left(self):
        self.overlay_assets.place_forget()
        self.overlay_paint.place_forget()
        self.overlay_preview.place_forget()
        self.overlay_grid.place_forget()
        self.assets_visible = False
        self.paint_visible = False
        self.preview_visible = False
        self.grid_visible = False

    def toggle_assets(self):
        v = self.assets_visible
        self._hide_all_left()
        if not v:
            self.overlay_assets.place(x=70, y=50, width=320, relheight=0.9, height=-100)
            self.assets_visible = True

    def toggle_paint(self):
        v = self.paint_visible
        self._hide_all_left()
        if not v:
            self.overlay_paint.place(x=70, y=50, width=320)
            self.paint_visible = True

    def toggle_preview(self):
        v = self.preview_visible
        self._hide_all_left()
        if not v:
            self.overlay_preview.place(x=70, y=50, width=320)
            self.preview_visible = True

    def toggle_grid(self):
        v = self.grid_visible
        self._hide_all_left()
        if not v:
            self.overlay_grid.place(x=70, y=50, width=320)
            self.grid_visible = True

    def toggle_combat(self):
        if self.combat_visible:
            self.combat_panel.place_forget()
            self.combat_visible = False
        else:
            self.combat_panel.place(relx=1.0, x=-10, y=50, width=320, relheight=0.5, height=-60, anchor="ne")
            self.combat_visible = True
            self.turn_panel.place_forget()
            self.turn_visible = False

    def toggle_turn(self):
        if self.turn_visible:
            self.turn_panel.place_forget()
            self.turn_visible = False
        else:
            self.turn_panel.place(relx=1.0, x=-10, y=50, width=320, relheight=0.5, height=-60, anchor="ne")
            self.turn_visible = True
            self.combat_panel.place_forget()
            self.combat_visible = False

    def on_mode_change(self, *args):
        self.populate_tree()
        if hasattr(self, 'btn_load_bg'):
            if self.app_mode.get() == "WEBER_NHP":
                self.btn_load_bg.pack(fill="x", padx=5, pady=5)
            else:
                self.btn_load_bg.pack_forget()
        self.draw_wrapper()

    def load_background_image(self):
        f = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif"), ("All Files", "*.*")]
        )
        if f:
            self.map_state.background_image = f
            
            # Auto-fit the camera and scale to the loaded image
            bg_img = self.get_image(f)
            if bg_img:
                orig_w, orig_h = bg_img.size
                cw = self.canvas.winfo_width()
                ch = self.canvas.winfo_height()
                
                if cw > 0 and orig_w > 0:
                    scale_w = cw / orig_w
                    scale_h = ch / orig_h
                    # Use max to ensure the image covers the entire canvas without gray borders
                    self.scale = max(scale_w, scale_h)
                    
                    # Center the camera on the image
                    self.camera_x = orig_w / 2
                    self.camera_y = orig_h / 2
                    
            self.draw_wrapper()

    def on_asset_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = self.tree.item(selected[0])
        # Check if it's a leaf node (has path in values)
        if item["values"]:
            self.selected_asset_path = item["values"][0]
            self.update_preview(self.selected_asset_path)
            # Choosing an asset implicitly enters "Place Mode" (clears selection)
            self.selected_item_index = None
            self.update_attachment_ui()
            self.draw_wrapper()

    def update_preview(self, path):
        img = self.get_image(path)
        if img:
            # Resize for preview (max 250x250)
            w, h = img.size
            ratio = min(250/w, 250/h)
            new_w, new_h = int(w*ratio), int(h*ratio)
            resized = img.resize((new_w, new_h), Image.Resampling.NEAREST)
            tk_img = ImageTk.PhotoImage(resized)
            
            # Keep ref
            self.preview_image_ref = tk_img 
            self.preview_label.config(image=tk_img, text="")
        else:
            self.preview_label.config(image="", text="Preview Error")

    def deselect_all(self, event=None):
        self.selected_asset_path = None
        self.tree.selection_remove(self.tree.selection())
        self.preview_label.config(image="", text="No Selection")
        self.update_attachment_ui()
        self.draw_wrapper()

    def delete_selected_item(self, event=None):
        # Prevent deletion when typing in an entry or text field
        if event is not None and getattr(event.widget, "winfo_class", lambda: "")() in ("Entry", "TEntry", "Text", "TCombobox"):
            return
            
        if self.selected_item_index is not None:
            if 0 <= self.selected_item_index < len(self.map_state.items):
                del self.map_state.items[self.selected_item_index]
                self.selected_item_index = None
                self.update_attachment_ui()
                self.draw_wrapper()

    def show_marker_menu(self, event=None):
        # Prevent marker trigger when typing
        if event is not None and getattr(event.widget, "winfo_class", lambda: "")() in ("Entry", "TEntry", "Text", "TCombobox"):
            return
            
        if self.selected_item_index is None:
            return
            
        marker_dir = self.map_state.markers_directory
        if not marker_dir or not os.path.exists(marker_dir):
            messagebox.showwarning("Warning", f"Marker folder not found. Please set it in Settings.")
            return
            
        menu = tk.Menu(self.root, tearoff=0)
        
        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        markers = [f for f in os.listdir(marker_dir) if f.lower().endswith(valid_exts)]
        markers.sort()
        
        item = self.map_state.items[self.selected_item_index]
        current_markers = item.get("markers", [])
        
        for m in markers:
            m_path = os.path.join(marker_dir, m)
            label = os.path.splitext(m)[0]
            if m_path in current_markers:
                menu.add_command(label="✓ " + label, command=lambda p=m_path: self.toggle_marker(p))
            else:
                menu.add_command(label="  " + label, command=lambda p=m_path: self.toggle_marker(p))
                
        x, y = self.root.winfo_pointerxy()
        menu.tk_popup(x, y)

    def toggle_marker(self, marker_path):
        if self.selected_item_index is None: return
        item = self.map_state.items[self.selected_item_index]
        if "markers" not in item:
            item["markers"] = []
            
        if marker_path in item["markers"]:
            item["markers"].remove(marker_path)
        else:
            item["markers"].append(marker_path)
            
        self.draw_wrapper()

    def add_marker_by_name(self, tgt_idx, marker_name):
        marker_dir = self.map_state.markers_directory
        if not marker_dir or not os.path.exists(marker_dir):
            return
            
        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        markers = [f for f in os.listdir(marker_dir) if f.lower().endswith(valid_exts)]
        
        found_path = None
        for m in markers:
            if marker_name.lower() in m.lower():
                found_path = os.path.join(marker_dir, m)
                break
                
        if found_path:
            item = self.map_state.items[tgt_idx]
            if "markers" not in item:
                item["markers"] = []
            if found_path not in item["markers"]:
                item["markers"].append(found_path)
            self.draw_wrapper()
    def show_structure_table_info(self):
        top = tk.Toplevel(self.root)
        top.title("Structure Damage Table Reference")
        top.geometry("600x250")
        top.transient(self.root)
        
        info = (
            "STRUCTURE DAMAGE TABLE\n"
            "--------------------------------------------------\n"
            "5-6 Glancing Blow: Emergency systems kick in. IMPAIRED until end of next turn.\n"
            "2-4 System Trauma: Roll 1d6. (1-3) Weapon destroyed, (4-6) System destroyed.\n"
            "1   Direct Hit: Effects depend on remaining structure:\n"
            "      3+ Structure: STUNNED until end of next turn.\n"
            "      2 Structure: Hull Check. Success = STUNNED, Failure = DESTROYED.\n"
            "      1 Structure: DESTROYED.\n\n"
            "Multiple 1s Crushing Hit: DESTROYED.\n"
        )
        tk.Label(top, text=info, justify="left", font=("Consolas", 11)).pack(padx=20, pady=20)
        ttk.Button(top, text="Close", command=top.destroy).pack(pady=5)

    def update_attachment_ui(self):
        self.attachment_preview_lbl.pack_forget()
        self.attachment_text_preview.pack_forget()
        self.attachment_image_ref = None # Clear ref
        self.stats_frame.pack_forget()
        
        if self.selected_item_index is not None:
            self.btn_attach.config(state="normal")
            item = self.map_state.items[self.selected_item_index]
            linked = item.get("linked_file")
            
            if linked:
                fname = os.path.basename(linked)
                self.lbl_attachment_status.config(text=f"Linked: {fname}")
                self.btn_open.config(state="normal")
                
                # Try preview
                ext = os.path.splitext(linked)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif']:
                    # Image Preview
                    try:
                        img = Image.open(linked)
                        # Resize to fit panel width approx 280
                        w, h = img.size
                        ratio = min(280/w, 200/h) # Limit height too
                        new_w, new_h = int(w*ratio), int(h*ratio)
                        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        tk_img = ImageTk.PhotoImage(resized)
                        self.attachment_image_ref = tk_img
                        self.attachment_preview_lbl.config(image=tk_img, text="")
                        self.attachment_preview_lbl.pack(fill="both", padx=5, pady=5)
                    except Exception as e:
                        self.attachment_preview_lbl.config(image="", text=f"Error loading prev: {e}")
                        self.attachment_preview_lbl.pack(fill="x")
                elif ext in ['.txt', '.md', '.json']:
                    # Text Preview
                    try:
                        with open(linked, 'r', encoding='utf-8') as f:
                            content = f.read(500) # Preview first 500 chars
                        self.attachment_text_preview.config(state="normal")
                        self.attachment_text_preview.delete("1.0", "end")
                        self.attachment_text_preview.insert("1.0", content)
                        self.attachment_text_preview.config(state="disabled")
                        self.attachment_text_preview.pack(fill="x", padx=5, pady=5)
                    except Exception as e:
                         self.lbl_attachment_status.config(text=f"Error reading text: {e}")
                else:
                    self.attachment_preview_lbl.config(image="", text="(No Preview Available)")
                    self.attachment_preview_lbl.pack(fill="x")
            else:
                self.lbl_attachment_status.config(text="No file attached")
                self.btn_open.config(state="disabled")
            
            # Show stats if they exist
            if any(k in item for k in ('hp', 'max_hp', 'structure', 'speed', 'evasion', 'custom_name', 'faction', 'repair_cap', 'heat_cap')):
                self.stats_frame.pack(fill="x", padx=5, pady=10)
                
                self.name_var.set(item.get('custom_name', ''))
                self.faction_var.set(item.get('faction', 'Neutral'))
                self.barrier_var.set(item.get('barrier_radius', 1))
                
                hp_str = f"HP: {item.get('hp', '-')} / {item.get('max_hp', '-')}"
                self.lbl_hp.config(text=hp_str)
                struct_str = f"Structure: {item.get('structure', '-')}"
                self.lbl_struct.config(text=struct_str)
                speed_str = f"Speed: {item.get('speed', '-')}"
                self.lbl_speed.config(text=speed_str)
                ev_str = f"Evasion: {item.get('evasion', '-')}"
                self.lbl_evasion.config(text=ev_str)
                edef_str = f"E-Def: {item.get('e_defense', '-')}"
                self.lbl_edefense.config(text=edef_str)
                repair_str = f"Repairs: {item.get('repair_cap', '-')}"
                self.lbl_repair.config(text=repair_str)
                heat_str = f"Heat Cap: {item.get('heat_cap', '-')}"
                self.lbl_heat.config(text=heat_str)
        else:
            self.btn_attach.config(state="disabled")
            self.btn_open.config(state="disabled")
            self.lbl_attachment_status.config(text="Select an item to attach")

    def attach_file(self):
        if self.selected_item_index is None: return
        f = filedialog.askopenfilename(title="Select File to Attach")
        if f:
            item = self.map_state.items[self.selected_item_index]
            item["linked_file"] = f
            
            # Parse stats if text/md
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.txt', '.md']:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        text = file.read()
                    import re
                    hp_match = re.search(r'(?i)(?:hp|hit\s*points?)\s*[:=]?\s*(\d+)', text)
                    struct_match = re.search(r'(?i)(?:structure|struct)\s*[:=]?\s*(\d+)', text)
                    speed_match = re.search(r'(?i)(?:speed|spd)\s*[:=]?\s*(\d+)', text)
                    
                    # Fix Evasion / E-Def regex
                    evade_match = re.search(r'(?i)(?:evasion|evade|eva)\s*[:=-]?\s*(\d+)', text)
                    edef_match = re.search(r'(?i)(?:e-defense|e-def|e\s*def(?:ense)?|edef)\s*[:=-]?\s*(\d+)', text)
                    
                    repair_match = re.search(r'(?i)(?:repair|repairs|repair\s*cap)\s*[:=]?\s*(\d+)', text)
                    heat_match = re.search(r'(?i)(?:heat|heat\s*cap)\s*[:=]?\s*(\d+)', text)
                    
                    if hp_match and 'max_hp' not in item:
                        item['max_hp'] = int(hp_match.group(1))
                        item['hp'] = item['max_hp']
                    if struct_match and 'structure' not in item:
                        item['structure'] = int(struct_match.group(1))
                    if speed_match:
                        item['speed'] = int(speed_match.group(1))
                    if evade_match:
                        item['evasion'] = int(evade_match.group(1))
                    if edef_match:
                        item['e_defense'] = int(edef_match.group(1))
                    if repair_match:
                        item['repair_cap'] = int(repair_match.group(1))
                    if heat_match:
                        item['heat_cap'] = int(heat_match.group(1))
                        
                except Exception as e:
                    print(f"Error parsing stats: {e}")
            
            self.update_attachment_ui()

    def update_custom_name(self, event=None):
        if self.selected_item_index is not None:
            self.map_state.items[self.selected_item_index]["custom_name"] = self.name_var.get()
            self.update_combat_comboboxes()

    def log_to_terminal(self, msg):
        self.term_text.config(state="normal")
        self.term_text.insert("end", msg + "\n")
        self.term_text.see("end")
        self.term_text.config(state="disabled")

    def open_linked_file(self):
        if self.selected_item_index is None: return
        item = self.map_state.items[self.selected_item_index]
        linked = item.get("linked_file")
        if linked and os.path.exists(linked):
            try:
                os.startfile(linked)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
        else:
            messagebox.showwarning("Warning", "Linked file not found or invalid.")


    def choose_grid_color(self):
        color_code = colorchooser.askcolor(title="Choose grid color", initialcolor=self.map_state.grid_color)
        if color_code[1]:
            self.map_state.grid_color = color_code[1]
            self.draw_wrapper()

    def update_grid_config(self, event=None):
        try:
            self.map_state.grid_size = self.grid_size_var.get()
            self.map_state.grid_offset_x = self.offset_x_var.get()
            self.map_state.grid_offset_y = self.offset_y_var.get()
            
            self.grid.size = self.map_state.grid_size
            self.draw_wrapper()
        except ValueError:
            pass

    def update_faction(self, event=None):
        if self.selected_item_index is not None:
            self.map_state.items[self.selected_item_index]["faction"] = self.faction_var.get()
            self.update_combat_comboboxes()
            self.draw_wrapper()

    def update_barrier_size(self, event=None):
        if self.selected_item_index is not None:
            try:
                self.map_state.items[self.selected_item_index]["barrier_radius"] = self.barrier_var.get()
                self.draw_wrapper()
            except ValueError:
                pass

