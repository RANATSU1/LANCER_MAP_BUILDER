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

class UiSetupMixin:
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

    def setup_ui(self):
        # The main container is now just a Frame or the root.
        # But we need Canvas at the bottom, taking full space.
        self.canvas = tk.Canvas(self.root, bg="#000000", highlightthickness=1, highlightbackground=self.map_state.ui_fg_color, highlightcolor=self.map_state.ui_fg_color)
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

        # --- OVERLAYS ---
        bg = self.map_state.ui_bg_color
        fg = self.map_state.ui_fg_color
        
        # Top Left Buttons
        self.top_left = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.top_left.place(x=10, y=10)
        ttk.Button(self.top_left, text="> SAVE", command=self.save_map).pack(side="left", padx=2, pady=2)
        ttk.Button(self.top_left, text="> LOAD", command=self.load_by_file).pack(side="left", padx=2, pady=2)
        ttk.Button(self.top_left, text="> CLEAR", command=self.clear_map).pack(side="left", padx=2, pady=2)
        ttk.Button(self.top_left, text="> EXPORT", command=self.export_map).pack(side="left", padx=2, pady=2)
        
        # Top Right Buttons
        self.top_right = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.top_right.place(relx=1.0, x=-10, y=10, anchor="ne")
        ttk.Button(self.top_right, text="⚔", width=3, command=self.toggle_combat).pack(side="left", padx=2, pady=2)
        ttk.Button(self.top_right, text="⏱", width=3, command=self.toggle_turn).pack(side="left", padx=2, pady=2)
        ttk.Button(self.top_right, text="⚙", width=3, command=self.open_settings_overlay).pack(side="left", padx=2, pady=2)

        # Left Vertical Tools Bar
        self.tools_bar = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.tools_bar.place(x=10, y=50, width=50)
        
        ttk.Label(self.tools_bar, text="TOOLS").pack(pady=5)
        ttk.Separator(self.tools_bar, orient="horizontal").pack(fill="x", padx=2, pady=2)
        
        self.btn_tools_assets = tk.Button(self.tools_bar, text="🗄", bg=bg, fg=fg, bd=1, relief="solid", command=self.toggle_assets, font=("Consolas", 16), height=1)
        self.btn_tools_assets.pack(fill="x", padx=2, pady=5)
        
        self.btn_tools_paint = tk.Button(self.tools_bar, text="🎨", bg=bg, fg=fg, bd=1, relief="solid", command=self.toggle_paint, font=("Consolas", 16), height=1)
        self.btn_tools_paint.pack(fill="x", padx=2, pady=5)

        self.btn_tools_preview = tk.Button(self.tools_bar, text="👁", bg=bg, fg=fg, bd=1, relief="solid", command=self.toggle_preview, font=("Consolas", 16), height=1)
        self.btn_tools_preview.pack(fill="x", padx=2, pady=5)

        self.btn_tools_grid = tk.Button(self.tools_bar, text="▦", bg=bg, fg=fg, bd=1, relief="solid", command=self.toggle_grid, font=("Consolas", 16), height=1)
        self.btn_tools_grid.pack(fill="x", padx=2, pady=5)

        # 4 Left Overlays
        self.overlay_assets = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.assets_visible = False
        
        self.overlay_paint = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.paint_visible = False
        
        self.overlay_preview = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.preview_visible = False
        
        self.overlay_grid = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.grid_visible = False
        
        # 1. Assets Content
        content_assets = ttk.Frame(self.overlay_assets)
        content_assets.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.load_bg_frame = ttk.Frame(content_assets)
        self.load_bg_frame.pack(fill="x")
        self.btn_load_bg = ttk.Button(self.load_bg_frame, text="Load Map PNG", command=self.load_background_image)
        if self.app_mode.get() == "WEBER_NHP":
            self.btn_load_bg.pack(fill="x", padx=5, pady=5)

        ttk.Label(content_assets, text="Assets").pack(anchor="w", padx=5, pady=5)
        self.tree_frame = ttk.Frame(content_assets)
        self.tree_frame.pack(fill="both", expand=True)
        self.tree_scroll = ttk.Scrollbar(self.tree_frame)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set, height=10)
        self.tree.pack(fill="both", expand=True)
        self.tree_scroll.config(command=self.tree.yview)
        self.populate_tree()
        self.tree.bind("<<TreeviewSelect>>", self.on_asset_select)
        
        ttk.Label(content_assets, text="Preview").pack(anchor="w", padx=5, pady=5)
        self.preview_label = ttk.Label(content_assets, text="No Selection", anchor="center", background="#000000", foreground="#39ff14")
        self.preview_label.pack(fill="x", padx=5, pady=5, ipady=40)

        # 2. Paint Content
        content_paint = ttk.Frame(self.overlay_paint)
        content_paint.pack(fill="both", expand=True, padx=5, pady=5)
        toolbar_f = ttk.LabelFrame(content_paint, text="Map Tools")
        toolbar_f.pack(fill="x", padx=2, pady=5)
        ttk.Button(toolbar_f, text="Select/Move Mode (ESC)", command=self.deselect_all).pack(fill="x", padx=2, pady=2)
        ttk.Checkbutton(toolbar_f, text="Paint Mode", variable=self.paint_mode, style="Toolbutton").pack(fill="x", padx=2, pady=2)
        ttk.Combobox(toolbar_f, textvariable=self.paint_color, values=["white", "red", "blue", "green", "yellow", "black", "eraser"], state="readonly").pack(fill="x", padx=2, pady=2)
        ttk.Button(toolbar_f, text="Eraser", command=lambda: self.paint_color.set("eraser")).pack(fill="x", padx=2, pady=2)

        # 3. Preview Content
        content_preview = ttk.Frame(self.overlay_preview)
        content_preview.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.attachment_frame = ttk.LabelFrame(content_preview, text="Attachment")
        self.attachment_frame.pack(fill="x", padx=5, pady=10)
        self.btn_attach = ttk.Button(self.attachment_frame, text="Attach File", command=self.attach_file, state="disabled")
        self.btn_attach.pack(fill="x", padx=5, pady=2)
        self.btn_open = ttk.Button(self.attachment_frame, text="Open External", command=self.open_linked_file, state="disabled")
        self.btn_open.pack(fill="x", padx=5, pady=2)
        self.lbl_attachment_status = ttk.Label(self.attachment_frame, text="No Selection", wraplength=280)
        self.lbl_attachment_status.pack(fill="x", padx=5, pady=5)
        
        self.attachment_preview_lbl = ttk.Label(self.attachment_frame, background="#000000", anchor="center")
        self.attachment_text_preview = tk.Text(self.attachment_frame, height=6, width=30, bg="#000000", fg="#39ff14", font=("Consolas", 10, "bold"), insertbackground="#39ff14", relief="solid", highlightthickness=1, highlightbackground="#39ff14", state="disabled")

        self.stats_frame = ttk.LabelFrame(content_preview, text="Mech Details")
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
        
        b_frame = ttk.Frame(self.stats_frame)
        b_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(b_frame, text="Barrier Range:").pack(side="left")
        self.barrier_var = tk.IntVar(value=1)
        self.sb_barrier = ttk.Spinbox(b_frame, from_=1, to=20, width=5, textvariable=self.barrier_var, command=self.update_barrier_size)
        self.sb_barrier.pack(side="left", padx=5)
        self.sb_barrier.bind("<Return>", self.update_barrier_size)
        self.sb_barrier.bind("<FocusOut>", self.update_barrier_size)
        
        self.lbl_hp = ttk.Label(self.stats_frame, text="HP: - / -")
        self.lbl_hp.pack(anchor="w", padx=5, pady=2)
        self.lbl_struct = ttk.Label(self.stats_frame, text="Structure: -")
        self.lbl_struct.pack(anchor="w", padx=5, pady=2)
        self.lbl_speed = ttk.Label(self.stats_frame, text="Speed: -")
        self.lbl_speed.pack(anchor="w", padx=5, pady=2)
        self.lbl_evasion = ttk.Label(self.stats_frame, text="Evasion: -")
        self.lbl_evasion.pack(anchor="w", padx=5, pady=2)
        self.lbl_edefense = ttk.Label(self.stats_frame, text="E-Def: -")
        self.lbl_edefense.pack(anchor="w", padx=5, pady=2)
        self.lbl_repair = ttk.Label(self.stats_frame, text="Repairs: -")
        self.lbl_repair.pack(anchor="w", padx=5, pady=2)
        self.lbl_heat = ttk.Label(self.stats_frame, text="Heat Cap: -")
        self.lbl_heat.pack(anchor="w", padx=5, pady=2)

        # 4. Grid Content
        content_grid = ttk.Frame(self.overlay_grid)
        content_grid.pack(fill="both", expand=True, padx=5, pady=5)
        self.grid_controls = ttk.LabelFrame(content_grid, text="Grid Settings")
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

        # Right Sidebars
        self.turn_panel = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.turn_visible = False
        
        self.combat_panel = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.combat_visible = False
        
        self.setup_right_sidebar()
        
        # Status Bar at bottom left
        self.status_bar = tk.Frame(self.root, bg=bg, highlightbackground=fg, highlightthickness=1)
        self.status_bar.place(x=10, rely=1.0, y=-10, anchor="sw")
        self.lbl_status = ttk.Label(self.status_bar, text="STATUS: READY  |  GRID: 50x50")
        self.lbl_status.pack(padx=10, pady=2)

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

    def setup_right_sidebar(self):
        turn_content = ttk.Frame(self.turn_panel)
        turn_content.pack(fill="both", expand=True, padx=5, pady=5)
        
        combat_content = ttk.Frame(self.combat_panel)
        combat_content.pack(fill="both", expand=True, padx=5, pady=5)

        # Round Tracker
        self.round = 1
        round_frame = ttk.Frame(turn_content)
        round_frame.pack(fill="x", padx=5, pady=5)
        self.lbl_round = ttk.Label(round_frame, text="Round: 1", font=("Arial", 14, "bold"))
        self.lbl_round.pack(side="left")
        ttk.Button(round_frame, text="Next Round", command=self.next_round).pack(side="right")
        
        # Turn Tracker panel
        self.active_turn_idx = None
        self.acted_this_round = set()

        turn_frame = ttk.LabelFrame(turn_content, text="Turn Order")
        turn_frame.pack(fill="x", padx=5, pady=5)
        
        tf1 = ttk.Frame(turn_frame)
        tf1.pack(fill="x", pady=2)
        ttk.Button(tf1, text="Decide First Faction", command=self.decide_first_faction).pack(side="left", padx=2)
        
        tf2 = ttk.Frame(turn_frame)
        tf2.pack(fill="x", pady=2)
        ttk.Label(tf2, text="Next:").pack(side="left", padx=2)
        self.cb_turn = ttk.Combobox(tf2, state="readonly", width=15)
        self.cb_turn.pack(side="left", padx=2)
        ttk.Button(tf2, text="Start Turn", command=self.start_turn).pack(side="left", padx=2)
        
        tf3 = ttk.Frame(turn_frame)
        tf3.pack(fill="x", pady=2)
        self.lbl_active_turn = ttk.Label(tf3, text="Active: None")
        self.lbl_active_turn.pack(side="left", padx=2)
        ttk.Button(tf3, text="End Turn", command=self.end_turn).pack(side="right", padx=2)

        # Action Tracking inside turn_frame
        ttk.Separator(turn_frame, orient="horizontal").pack(fill="x", pady=5)
        
        self.val_movement = tk.IntVar(value=0)
        self.val_actions = tk.IntVar(value=2)
        self.val_free_actions = tk.IntVar(value=0)
        self.overcharge_used = False
        
        act_f1 = ttk.Frame(turn_frame)
        act_f1.pack(fill="x", pady=2)
        ttk.Label(act_f1, text="Speed:").pack(side="left", padx=2)
        ttk.Button(act_f1, text="-", width=2, command=self.dec_movement).pack(side="left")
        ttk.Label(act_f1, textvariable=self.val_movement, width=3, anchor="center").pack(side="left")
        ttk.Button(act_f1, text="+", width=2, command=self.inc_movement).pack(side="left")
        
        act_f2 = ttk.Frame(turn_frame)
        act_f2.pack(fill="x", pady=2)
        ttk.Label(act_f2, text="Actions:").pack(side="left", padx=2)
        ttk.Label(act_f2, textvariable=self.val_actions, width=2).pack(side="left", padx=1)
        ttk.Button(act_f2, text="Quick", width=5, command=self.use_quick_action).pack(side="left", padx=1)
        ttk.Button(act_f2, text="Full", width=4, command=self.use_full_action).pack(side="left", padx=1)
        self.btn_overcharge = ttk.Button(act_f2, text="OC", width=3, command=self.use_overcharge)
        self.btn_overcharge.pack(side="left", padx=1)
        
        act_f3 = ttk.Frame(turn_frame)
        act_f3.pack(fill="x", pady=2)
        ttk.Label(act_f3, text="Free Acts:").pack(side="left", padx=2)
        ttk.Label(act_f3, textvariable=self.val_free_actions, width=2).pack(side="left", padx=1)
        ttk.Button(act_f3, text="+", width=3, command=self.use_free_action).pack(side="left", padx=1)

        # Tools Panel (Dice / Attacks)
        tools_frame = ttk.LabelFrame(combat_content, text="Combat Tools")
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
        ttk.Button(tools_frame, text="View Structure Table", command=self.show_structure_table_info).pack(fill="x", padx=2, pady=2)
        
        # Terminal/History (Always Visible, bottom right, 50% height)
        term_frame = ttk.LabelFrame(self.root, text=">> COMBAT_LOG.exe")
        term_frame.place(relx=1.0, rely=1.0, x=-10, y=-10, width=320, relheight=0.5, height=-10, anchor="se")
        
        term_scroll = ttk.Scrollbar(term_frame)
        term_scroll.pack(side="right", fill="y")
        self.term_text = tk.Text(term_frame, height=10, width=30, bg="#000000", fg="#39ff14", font=("Consolas", 10, "bold"), insertbackground="#39ff14", relief="solid", highlightthickness=1, highlightbackground="#39ff14", yscrollcommand=term_scroll.set)
        self.term_text.pack(fill="both", expand=True, padx=2, pady=2)
        term_scroll.config(command=self.term_text.yview)
        
        self.term_text.insert("1.0", "--- Combat Log initialized ---\n")
        self.term_text.config(state="disabled")
        
    def update_combat_comboboxes(self):
        names = []
        for idx, item in enumerate(self.map_state.items):
            if self.is_combatant(item):
                names.append(f"[{idx}] {self.get_token_name(idx)}")
        
        self.cb_attacker['values'] = names
        self.cb_target['values'] = names
        self.update_turn_combobox()

    def update_turn_combobox(self):
        if not hasattr(self, "acted_this_round"):
            self.acted_this_round = set()
            self.active_turn_idx = None
            
        names = []
        for idx, item in enumerate(self.map_state.items):
            if self.is_combatant(item):
                if idx not in self.acted_this_round and idx != self.active_turn_idx:
                    fac = item.get("faction", "Neutral")
                    names.append(f"[{idx}] {fac} - {self.get_token_name(idx)}")
                    
        self.cb_turn['values'] = names
        if names:
            self.cb_turn.current(0)
        else:
            self.cb_turn.set('')

