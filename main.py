import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageDraw
import os
import math

from assets import scan_assets, ASSET_ROOT
from grid import HexGrid
from map_state import MapState

class MapBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lancer Map Builder")
        self.root.geometry("1200x800")

        # Initialize Logic
        # Grid initialized from state
        self.map_state = MapState()
        self.grid = HexGrid(size=50, flat_top=False)
        self.assets = scan_assets()
        
        # State for interactions
        self.selected_asset_path = None
        self.selected_item_index = None # Index of selected item in map_state.items
        self.drag_item_index = None
        self.camera_x = 0
        self.camera_y = 0
        self.scale = 1.0
        self.loaded_images = {} # Cache for PIL images
        self._tk_refs = [] # Keep references to PhotoImages
        
        self.hovered_item_index = None
        self.tooltip_x = 0
        self.tooltip_y = 0

        self.paint_mode = tk.BooleanVar(value=False)
        self.paint_color = tk.StringVar(value="white")
        self.current_drawing = None
        self.app_mode = tk.StringVar(value="GUSTAV_NHP")
        
        # Bind delete keys
        self.root.bind("<Delete>", self.delete_selected_item)
        self.root.bind("<BackSpace>", self.delete_selected_item)
        self.root.bind("<Escape>", self.deselect_all)
        self.root.bind("<m>", self.show_marker_menu)
        self.root.bind("<M>", self.show_marker_menu)

        self.apply_theme()
        self.setup_ui()

    def apply_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = self.map_state.ui_bg_color
        fg_color = self.map_state.ui_fg_color
        
        def darken_color(hex_color, factor=0.5):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"
            return "#004400"
            
        sel_bg = darken_color(fg_color, 0.2)
        btn_active_bg = darken_color(fg_color, 0.1)
        btn_bg = darken_color(bg_color, 0.9) if bg_color != "#000000" else "#0a0a0a"

        font = ("Consolas", 10, "bold")
        
        self.root.configure(bg=bg_color)
        
        style.configure(".", background=bg_color, foreground=fg_color, font=font)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=btn_bg, foreground=fg_color, bordercolor=fg_color, lightcolor=fg_color, darkcolor=fg_color, font=font)
        style.map("TButton", background=[("active", btn_active_bg)], foreground=[("active", fg_color)])
        style.configure("TCombobox", fieldbackground=bg_color, background=btn_bg, foreground=fg_color, arrowcolor=fg_color)
        style.map("TCombobox", fieldbackground=[("readonly", bg_color)], foreground=[("readonly", fg_color)])
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        style.map("TCheckbutton", background=[("active", bg_color)])
        style.configure("Treeview", background=bg_color, fieldbackground=bg_color, foreground=fg_color, font=font, borderwidth=0)
        style.map("Treeview", background=[("selected", sel_bg)], foreground=[("selected", fg_color)])
        style.configure("Treeview.Heading", background=btn_bg, foreground=fg_color, bordercolor=fg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        style.configure("TEntry", fieldbackground=bg_color, foreground=fg_color, insertcolor=fg_color, bordercolor=fg_color)
        style.configure("TSeparator", background=fg_color)
        style.configure("TPanedwindow", background=bg_color)
        style.configure("Vertical.TScrollbar", background=btn_bg, troughcolor=bg_color, arrowcolor=fg_color, bordercolor=fg_color)

        if hasattr(self, 'preview_label'):
            self.preview_label.config(background=bg_color, foreground=fg_color)
        if hasattr(self, 'attachment_preview_lbl'):
            self.attachment_preview_lbl.config(background=bg_color)
        if hasattr(self, 'attachment_text_preview'):
            self.attachment_text_preview.config(bg=bg_color, fg=fg_color, insertbackground=fg_color, highlightbackground=fg_color)
        if hasattr(self, 'canvas'):
            self.canvas.config(bg=bg_color, highlightbackground=fg_color, highlightcolor=fg_color)
        if hasattr(self, 'term_text'):
            self.term_text.config(bg=bg_color, fg=fg_color, insertbackground=fg_color, highlightbackground=fg_color)

    def open_ui_settings(self):
        bg = colorchooser.askcolor(title="Background Color", initialcolor=self.map_state.ui_bg_color)
        if bg[1]:
            self.map_state.ui_bg_color = bg[1]
        fg = colorchooser.askcolor(title="Foreground/Accent Color", initialcolor=self.map_state.ui_fg_color)
        if fg[1]:
            self.map_state.ui_fg_color = fg[1]
            
        self.apply_theme()

    def setup_ui(self):
        # Main Layout: Sidebar (Left) | Canvas (Center) | Toolbar (Top)
        
        # Toolbar
        self.toolbar = ttk.Frame(self.root, height=30)
        self.toolbar.pack(side="top", fill="x")
        
        ttk.Button(self.toolbar, text="Save Map", command=self.save_map).pack(side="left", padx=5, pady=5)
        ttk.Button(self.toolbar, text="Load Map", command=self.load_by_file).pack(side="left", padx=5, pady=5)
        ttk.Button(self.toolbar, text="Clear Map", command=self.clear_map).pack(side="left", padx=5, pady=5)
        ttk.Button(self.toolbar, text="Export Map", command=self.export_map).pack(side="left", padx=5, pady=5)
        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=5, fill="y")
        ttk.Button(self.toolbar, text="Select/Move Mode (ESC)", command=self.deselect_all).pack(side="left", padx=5, pady=5)
        
        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=5, fill="y")
        ttk.Checkbutton(self.toolbar, text="Paint Mode", variable=self.paint_mode, style="Toolbutton").pack(side="left", padx=2, pady=5)
        ttk.Combobox(self.toolbar, textvariable=self.paint_color, values=["white", "red", "blue", "green", "yellow", "black"], state="readonly", width=8).pack(side="left", padx=2, pady=5)
        ttk.Button(self.toolbar, text="Clear Paint", command=self.clear_paint).pack(side="left", padx=2, pady=5)
        
        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=5, fill="y")
        self.mode_cb = ttk.Combobox(self.toolbar, textvariable=self.app_mode, values=["GUSTAV_NHP", "WEBER_NHP"], state="readonly", width=12)
        self.mode_cb.pack(side="left", padx=5, pady=5)
        
        self.btn_load_bg = ttk.Button(self.toolbar, text="Load Map PNG", command=self.load_background_image)
        if self.app_mode.get() == "WEBER_NHP":
            self.btn_load_bg.pack(side="left", padx=5, pady=5)
            
        ttk.Button(self.toolbar, text="UI Colors", command=self.open_ui_settings).pack(side="right", padx=5, pady=5)
        
        # Paned Window
        self.paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True)
        
        # Sidebar
        self.sidebar = ttk.Frame(self.paned, width=300)
        self.paned.add(self.sidebar, weight=1)
        
        # Asset Treeview
        ttk.Label(self.sidebar, text="Assets").pack(anchor="w", padx=5, pady=5)
        
        # Scrollbar for treeview
        self.tree_frame = ttk.Frame(self.sidebar)
        self.tree_frame.pack(fill="both", expand=True)
        
        self.tree_scroll = ttk.Scrollbar(self.tree_frame)
        self.tree_scroll.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set, height=10)
        self.tree.pack(fill="both", expand=True)
        self.tree_scroll.config(command=self.tree.yview)
        
        self.populate_tree()
        self.tree.bind("<<TreeviewSelect>>", self.on_asset_select)

        # Asset Preview
        ttk.Label(self.sidebar, text="Preview").pack(anchor="w", padx=5, pady=5)
        self.preview_label = ttk.Label(self.sidebar, text="No Selection", anchor="center", background="#000000", foreground="#39ff14")
        self.preview_label.pack(fill="x", padx=5, pady=5, ipady=20)

        # Attachment Panel
        self.attachment_frame = ttk.LabelFrame(self.sidebar, text="Attachment")
        self.attachment_frame.pack(fill="x", padx=5, pady=10)
        
        self.btn_attach = ttk.Button(self.attachment_frame, text="Attach File", command=self.attach_file, state="disabled")
        self.btn_attach.pack(fill="x", padx=5, pady=2)
        
        self.btn_open = ttk.Button(self.attachment_frame, text="Open External", command=self.open_linked_file, state="disabled")
        self.btn_open.pack(fill="x", padx=5, pady=2)
        
        self.lbl_attachment_status = ttk.Label(self.attachment_frame, text="No Selection", wraplength=280)
        self.lbl_attachment_status.pack(fill="x", padx=5, pady=5)
        
        # Attachment Preview (Image or Text)
        self.attachment_preview_lbl = ttk.Label(self.attachment_frame, background="#000000", anchor="center")
        # self.attachment_preview_lbl.pack(fill="both", padx=5, pady=5, expand=True) # Packed dynamically
        self.attachment_text_preview = tk.Text(self.attachment_frame, height=6, width=30, bg="#000000", fg="#39ff14", font=("Consolas", 10, "bold"), insertbackground="#39ff14", relief="solid", highlightthickness=1, highlightbackground="#39ff14", state="disabled")
        # Don't pack text initially

        # Stats Panel
        self.stats_frame = ttk.LabelFrame(self.sidebar, text="Mech Details")
        
        name_frame = ttk.Frame(self.stats_frame)
        name_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(name_frame, text="Name:").pack(side="left")
        self.name_var = tk.StringVar()
        self.ent_name = ttk.Entry(name_frame, textvariable=self.name_var)
        self.ent_name.pack(side="left", fill="x", expand=True, padx=2)
        self.ent_name.bind("<KeyRelease>", self.update_custom_name)
        
        fac_frame = ttk.Frame(self.stats_frame)
        fac_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(fac_frame, text="Faction:").pack(side="left")
        self.faction_var = tk.StringVar(value="Neutral")
        self.cb_faction = ttk.Combobox(fac_frame, textvariable=self.faction_var, values=["Neutral", "Player", "NPC"], state="readonly")
        self.cb_faction.pack(side="left", fill="x", expand=True, padx=2)
        self.cb_faction.bind("<<ComboboxSelected>>", self.update_faction)
        
        self.lbl_hp = ttk.Label(self.stats_frame, text="HP: - / -")
        self.lbl_hp.pack(anchor="w", padx=5, pady=2)
        
        self.lbl_struct = ttk.Label(self.stats_frame, text="Structure: -")
        self.lbl_struct.pack(anchor="w", padx=5, pady=2)

        self.lbl_speed = ttk.Label(self.stats_frame, text="Speed: -")
        self.lbl_speed.pack(anchor="w", padx=5, pady=2)

        # Grid Controls
        self.grid_controls = ttk.LabelFrame(self.sidebar, text="Grid Settings")
        self.grid_controls.pack(fill="x", padx=5, pady=10)
        
        ttk.Label(self.grid_controls, text="Size:").grid(row=0, column=0, padx=5, pady=2)
        self.grid_size_var = tk.DoubleVar(value=self.map_state.grid_size)
        self.grid_size_entry = ttk.Entry(self.grid_controls, textvariable=self.grid_size_var, width=5)
        self.grid_size_entry.grid(row=0, column=1, padx=5, pady=2)
        self.grid_size_entry.bind("<Return>", self.update_grid_config)
        self.grid_size_entry.bind("<FocusOut>", self.update_grid_config)

        ttk.Label(self.grid_controls, text="Offset X:").grid(row=1, column=0, padx=5, pady=2)
        self.offset_x_var = tk.DoubleVar(value=self.map_state.grid_offset_x)
        self.offset_x_entry = ttk.Entry(self.grid_controls, textvariable=self.offset_x_var, width=5)
        self.offset_x_entry.grid(row=1, column=1, padx=5, pady=2)
        self.offset_x_entry.bind("<Return>", self.update_grid_config)
        self.offset_x_entry.bind("<FocusOut>", self.update_grid_config)

        ttk.Label(self.grid_controls, text="Offset Y:").grid(row=2, column=0, padx=5, pady=2)
        self.offset_y_var = tk.DoubleVar(value=self.map_state.grid_offset_y)
        self.offset_y_entry = ttk.Entry(self.grid_controls, textvariable=self.offset_y_var, width=5)
        self.offset_y_entry.grid(row=2, column=1, padx=5, pady=2)
        self.offset_y_entry.bind("<Return>", self.update_grid_config)
        self.offset_y_entry.bind("<FocusOut>", self.update_grid_config)
        
        ttk.Button(self.grid_controls, text="Color", command=self.choose_grid_color).grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(self.grid_controls, text="Apply", command=self.update_grid_config).grid(row=3, column=1, padx=5, pady=5)

        # Canvas Area
        self.canvas_frame = ttk.Frame(self.paned)
        self.paned.add(self.canvas_frame, weight=4)

        # Right Sidebar (Combat/Action Tracker)
        self.right_sidebar = ttk.Frame(self.paned, width=300)
        self.paned.add(self.right_sidebar, weight=1)
        
        self.setup_right_sidebar()
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#000000", highlightthickness=1, highlightbackground="#39ff14", highlightcolor="#39ff14")
        self.canvas.pack(fill="both", expand=True)
        
        # Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<ButtonPress-3>", self.on_canvas_right_click) # Panning
        self.canvas.bind("<B3-Motion>", self.on_canvas_pan)
        # Mouse wheel bindings (Windows/Linux/Mac support)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)
        self.canvas.bind("<Motion>", self.on_canvas_motion)

        # Initial Draw
        self.root.after(10, self.draw_wrapper)
        self.app_mode.trace_add("write", self.on_mode_change)

    def populate_tree(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # assets structure: { Pack: { Category: [paths] } }
        for pack, categories in self.assets.items():
            pack_node = self.tree.insert("", "end", text=pack, open=False)
            has_children = False
            for cat, paths in categories.items():
                if self.app_mode.get() == "WEBER_NHP" and cat != "Tokens":
                    continue
                cat_node = self.tree.insert(pack_node, "end", text=cat, open=False)
                for path in paths:
                    filename = os.path.basename(path)
                    # Store full path in values
                    self.tree.insert(cat_node, "end", text=filename, values=(path,))
                    has_children = True
            if not has_children:
                self.tree.delete(pack_node)

    def on_mode_change(self, *args):
        self.populate_tree()
        if hasattr(self, 'btn_load_bg'):
            if self.app_mode.get() == "WEBER_NHP":
                self.btn_load_bg.pack(side="left", padx=5, pady=5)
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
            
        marker_dir = os.path.join(os.path.dirname(ASSET_ROOT), "MARKERS")
        if not os.path.exists(marker_dir):
            messagebox.showwarning("Warning", f"Marker folder not found at {marker_dir}")
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

    # --- Attachment Logic ---
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
            if any(k in item for k in ('hp', 'max_hp', 'structure', 'speed', 'evasion', 'custom_name', 'faction')):
                self.stats_frame.pack(fill="x", padx=5, pady=10)
                
                self.name_var.set(item.get('custom_name', ''))
                self.faction_var.set(item.get('faction', 'Neutral'))
                
                hp_str = f"HP: {item.get('hp', '-')} / {item.get('max_hp', '-')}"
                self.lbl_hp.config(text=hp_str)
                struct_str = f"Structure: {item.get('structure', '-')}"
                self.lbl_struct.config(text=struct_str)
                speed_str = f"Speed: {item.get('speed', '-')}"
                self.lbl_speed.config(text=speed_str)
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
                    evade_match = re.search(r'(?i)(?:evasion|evade)\s*[:=]?\s*(\d+)', text)
                    
                    if hp_match and 'max_hp' not in item:
                        item['max_hp'] = int(hp_match.group(1))
                        item['hp'] = item['max_hp']
                    if struct_match and 'structure' not in item:
                        item['structure'] = int(struct_match.group(1))
                    if speed_match:
                        item['speed'] = int(speed_match.group(1))
                    if evade_match:
                        item['evasion'] = int(evade_match.group(1))
                        
                except Exception as e:
                    print(f"Error parsing stats: {e}")
            
            self.update_attachment_ui()

    def setup_right_sidebar(self):
        # Round Tracker
        self.round = 1
        round_frame = ttk.Frame(self.right_sidebar)
        round_frame.pack(fill="x", padx=5, pady=5)
        self.lbl_round = ttk.Label(round_frame, text="Round: 1", font=("Arial", 14, "bold"))
        self.lbl_round.pack(side="left")
        ttk.Button(round_frame, text="Next Round", command=self.next_round).pack(side="right")
        

        # Tools Panel (Dice / Attacks)
        tools_frame = ttk.LabelFrame(self.right_sidebar, text="Combat Tools")
        tools_frame.pack(fill="x", padx=5, pady=5)
        
        dice_f = ttk.Frame(tools_frame)
        dice_f.pack(fill="x", pady=2)
        ttk.Label(dice_f, text="Roll:").pack(side="left", padx=2)
        self.dice_var = tk.StringVar(value="1d6")
        ttk.Entry(dice_f, textvariable=self.dice_var, width=8).pack(side="left", padx=2)
        ttk.Button(dice_f, text="Roll Dice", command=self.roll_custom_dice).pack(side="left", padx=5)

        ttk.Separator(tools_frame, orient="horizontal").pack(fill="x", pady=5)
        
        atk_f1 = ttk.Frame(tools_frame)
        atk_f1.pack(fill="x", pady=2)
        ttk.Label(atk_f1, text="Atk:").pack(side="left", padx=2)
        self.cb_attacker = ttk.Combobox(atk_f1, state="readonly", width=12)
        self.cb_attacker.pack(side="left", padx=2)
        ttk.Label(atk_f1, text="+Bonus:").pack(side="left", padx=2)
        self.atk_bonus_var = tk.IntVar(value=0)
        ttk.Entry(atk_f1, textvariable=self.atk_bonus_var, width=3).pack(side="left")

        atk_f2 = ttk.Frame(tools_frame)
        atk_f2.pack(fill="x", pady=2)
        ttk.Label(atk_f2, text="Tgt:").pack(side="left", padx=2)
        self.cb_target = ttk.Combobox(atk_f2, state="readonly", width=12)
        self.cb_target.pack(side="left", padx=2)

        atk_f3 = ttk.Frame(tools_frame)
        atk_f3.pack(fill="x", pady=2)
        ttk.Label(atk_f3, text="Dmg:").pack(side="left", padx=2)
        self.atk_dmg_var = tk.StringVar(value="1d6")
        ttk.Entry(atk_f3, textvariable=self.atk_dmg_var, width=5).pack(side="left")
        
        self.res_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(atk_f3, text="Resist", variable=self.res_var).pack(side="left", padx=5)

        ttk.Button(tools_frame, text="Perform Attack", command=self.perform_attack).pack(fill="x", padx=2, pady=5)
        ttk.Button(tools_frame, text="Refresh Combatants", command=self.update_combat_comboboxes).pack(fill="x", padx=2, pady=2)
        
        # Terminal/History
        term_frame = ttk.LabelFrame(self.right_sidebar, text="History")
        term_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        term_scroll = ttk.Scrollbar(term_frame)
        term_scroll.pack(side="right", fill="y")
        self.term_text = tk.Text(term_frame, height=10, width=30, bg="#000000", fg="#39ff14", font=("Consolas", 10, "bold"), insertbackground="#39ff14", relief="solid", highlightthickness=1, highlightbackground="#39ff14", yscrollcommand=term_scroll.set)
        self.term_text.pack(fill="both", expand=True, padx=2, pady=2)
        term_scroll.config(command=self.term_text.yview)
        
        self.term_text.insert("1.0", "--- Combat Log initialized ---\n")
        self.term_text.config(state="disabled")
        
    def update_custom_name(self, event=None):
        if self.selected_item_index is not None:
            self.map_state.items[self.selected_item_index]["custom_name"] = self.name_var.get()
            self.update_combat_comboboxes()

    def get_token_name(self, idx):
        item = self.map_state.items[idx]
        if item.get("custom_name"):
            return item["custom_name"]
        elif item.get("linked_file"):
            return os.path.basename(item["linked_file"]).split('.')[0][:15]
        else:
            return os.path.basename(item["path"]).split('.')[0][:15]

    def update_combat_comboboxes(self):
        names = []
        for idx, item in enumerate(self.map_state.items):
            p = item["path"].lower()
            if "token" in p or "frame" in p:
                names.append(f"[{idx}] {self.get_token_name(idx)}")
        
        self.cb_attacker['values'] = names
        self.cb_target['values'] = names

    def next_round(self):
        self.round += 1
        self.lbl_round.config(text=f"Round: {self.round}")
        self.log_to_terminal(f"=== ROUND {self.round} BEGINS ===")
        
    def log_to_terminal(self, msg):
        self.term_text.config(state="normal")
        self.term_text.insert("end", msg + "\n")
        self.term_text.see("end")
        self.term_text.config(state="disabled")

    def get_selected_name(self):
        if self.selected_item_index is None: return "Unknown"
        return self.get_token_name(self.selected_item_index)

    def parse_dice(self, dice_str):
        import re, random
        dice_str = dice_str.lower().replace(" ", "")
        match = re.match(r'^(\d*)d(\d+)(?:([+-])(\d+))?$', dice_str)
        if not match: return None
        
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_sides = int(match.group(2))
        
        modifier = 0
        if match.group(3) and match.group(4):
            mod_val = int(match.group(4))
            modifier = mod_val if match.group(3) == '+' else -mod_val
            
        return num_dice, die_sides, modifier
        
    def roll_dice_string(self, dice_str):
        import random
        parsed = self.parse_dice(dice_str)
        if not parsed: return None, 0
        num_dice, die_sides, mod = parsed
        
        rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
        total = sum(rolls) + mod
        return rolls, total

    def roll_custom_dice(self):
        import random
        dice_str = self.dice_var.get()
        res = self.roll_dice_string(dice_str)
        if res:
            rolls, total = res
            parsed = self.parse_dice(dice_str)
            mod_str = ""
            if parsed[2] > 0: mod_str = f"+{parsed[2]}"
            elif parsed[2] < 0: mod_str = f"{parsed[2]}"
                
            self.log_to_terminal(f"> Rolled {dice_str}: {rolls}{mod_str} = {total}")
        else:
            self.log_to_terminal(f"> Invalid dice format: {dice_str}")

    def get_index_from_cb(self, cb_str):
        import re
        if not cb_str: return None
        m = re.match(r'^\[(\d+)\]', cb_str)
        if m: return int(m.group(1))
        return None

    def perform_attack(self):
        import random
        atk_idx = self.get_index_from_cb(self.cb_attacker.get())
        tgt_idx = self.get_index_from_cb(self.cb_target.get())
        
        if atk_idx is None or tgt_idx is None:
            self.log_to_terminal("> Attack Error: Select Attacker and Target")
            return
            
        atk_name = self.get_token_name(atk_idx)
        tgt_name = self.get_token_name(tgt_idx)
        
        tgt_item = self.map_state.items[tgt_idx]
        evasion = tgt_item.get("evasion", 10) # default evasion
        
        # Attack Roll
        try:
            bonus = int(self.atk_bonus_var.get())
        except:
            bonus = 0
            
        d20 = random.randint(1, 20)
        atk_total = d20 + bonus
        
        # Log Attack
        if d20 == 20: # CRITICAL HIT
            self.log_to_terminal(f"### {atk_name} violently attacks {tgt_name} ###")
            self.log_to_terminal(f"> Attack: [CRIT 20] + {bonus} = {atk_total} vs Evade {evasion}")
            self.apply_damage(tgt_idx, self.atk_dmg_var.get(), is_crit=True, resist=self.res_var.get())
            
        elif atk_total >= evasion: # HIT
            self.log_to_terminal(f"### {atk_name} attacks {tgt_name} ###")
            self.log_to_terminal(f"> Attack: {d20} + {bonus} = {atk_total} vs Evade {evasion} (HIT)")
            self.apply_damage(tgt_idx, self.atk_dmg_var.get(), is_crit=False, resist=self.res_var.get())
            
        else: # MISS
            self.log_to_terminal(f"### {atk_name} attacks {tgt_name} ###")
            self.log_to_terminal(f"> Attack: {d20} + {bonus} = {atk_total} vs Evade {evasion} (MISS)")

    def apply_damage(self, target_idx, dmg_str, is_crit=False, resist=False):
        import math
        tgt_name = self.get_token_name(target_idx)
        res = self.roll_dice_string(dmg_str)
        if not res:
            self.log_to_terminal(f"> Error: Invalid damage format {dmg_str}")
            return
            
        rolls, total_dmg = res
        
        if is_crit:
            res2 = self.roll_dice_string(dmg_str)
            rolls2, total2 = res2
            self.log_to_terminal(f"> Crit Damage Roll 1: {rolls} = {total_dmg}")
            self.log_to_terminal(f"> Crit Damage Roll 2: {rolls2} = {total2}")
            total_dmg += total2
            self.log_to_terminal(f"> Initial Total Damage: {total_dmg}")
        else:
            self.log_to_terminal(f"> Initial Damage Roll: {rolls} = {total_dmg}")
            
        if resist:
            old_dmg = total_dmg
            total_dmg = math.ceil(total_dmg / 2)
            self.log_to_terminal(f"> Resisted! ({old_dmg} / 2) -> {total_dmg} dmg")
            
        # Apply to target
        tgt_item = self.map_state.items[target_idx]
        if 'hp' in tgt_item:
            tgt_item['hp'] -= total_dmg
            self.log_to_terminal(f"> {tgt_name} takes {total_dmg} dmg. HP: {tgt_item['hp']}")
            if tgt_item['hp'] <= 0:
                self.log_to_terminal(f"> {tgt_name} IS DESTROYED / HP DEPLETED!")
                if 'structure' in tgt_item:
                    tgt_item['structure'] -= 1
                    tgt_item['hp'] = tgt_item.get('max_hp', 0)
                    self.log_to_terminal(f"> {tgt_name} loses 1 Structure. Struct: {tgt_item['structure']}. HP Reset.")
        else:
            self.log_to_terminal(f"> {tgt_name} has no HP stats to reduce.")
            
        if self.selected_item_index == target_idx:
            self.update_attachment_ui()

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


    def get_image(self, path):
        if path not in self.loaded_images:
            try:
                img = Image.open(path)
                self.loaded_images[path] = img
            except Exception as e:
                print(f"Error loading image {path}: {e}")
                return None
        return self.loaded_images[path]

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

    def draw_wrapper(self):
        self.draw()

    def update_faction(self, event=None):
        if self.selected_item_index is not None:
            self.map_state.items[self.selected_item_index]["faction"] = self.faction_var.get()
            self.draw_wrapper()

    def clear_paint(self):
        self.map_state.drawings = []
        self.draw_wrapper()

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
        # Helper to check if item is token
        def is_token(path):
            p = path.lower()
            return "token" in p or "frame" in p

        # Split items
        tiles = []
        tokens = []
        
        # Store index to keep track of selection
        for idx, item in enumerate(self.map_state.items):
            if is_token(item["path"]):
                tokens.append((idx, item))
            else:
                tiles.append((idx, item))
        
        # Draw function to avoid duplication
        def draw_item_obj(idx, item):
            path = item["path"]
            q, r = item["q"], item["r"]
            
            wx, wy = self.grid.hex_to_pixel(q, r)
            wx += gx
            wy += gy
            
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
                    if faction != "Neutral" and is_token(path):
                        color = "#A0C0FF" if faction == "Player" else "#FFA0A0"
                        self.canvas.create_oval(
                            sx - display_w/2 - 2, sy - display_h/2 - 2, 
                            sx + display_w/2 + 2, sy + display_h/2 + 2, 
                            outline=color, width=4
                        )
                    
                    # Selection Highlight
                    if idx == self.selected_item_index:
                        # Draw bounding box
                        self.canvas.create_rectangle(
                            sx - display_w/2, sy - display_h/2, 
                            sx + display_w/2, sy + display_h/2, 
                            outline="cyan", width=3
                        )
                        
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

    # --- Interaction ---

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
            p = item["path"].lower()
            is_token = "token" in p or "frame" in p
            if item["q"] == q and item["r"] == r and is_token:
                found = i
                break

        if self.hovered_item_index != found:
            self.hovered_item_index = found if found != -1 else None
            self.update_hover_tooltip(event.x, event.y)
        elif self.hovered_item_index is not None:
            self.move_hover_tooltip(event.x, event.y)

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
            if "speed" in item:
                stats.append(f"  >SP: {item.get('speed', '-')}")
                
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

    def on_canvas_click(self, event):
        cx, cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        
        # Screen to World
        world_x = (event.x - cx) / self.scale + self.camera_x
        world_y = (event.y - cy) / self.scale + self.camera_y
        
        if self.paint_mode.get():
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
        
        if self.paint_mode.get() and self.current_drawing is not None:
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
            
        self.drag_item_index = None

    # --- File Ops ---
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

    def load_by_file(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Map", "*.json")])
        if f:
            self.map_state.load_from_file(f)
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

if __name__ == "__main__":
    t_root = tk.Tk()
    t_app = MapBuilderApp(t_root)
    t_root.mainloop()
