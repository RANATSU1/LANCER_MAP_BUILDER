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

from assets import scan_assets, ASSET_ROOT
from grid import HexGrid
from map_state import MapState

from ui_setup import UiSetupMixin
from ui_actions import UiActionsMixin
from combat_logic import CombatLogicMixin
from drawing import DrawingMixin
from event_handlers import EventHandlersMixin
from file_ops import FileOpsMixin
from utils import UtilsMixin

class MapBuilderApp(
    UiSetupMixin,
    UiActionsMixin,
    CombatLogicMixin,
    DrawingMixin,
    EventHandlersMixin,
    FileOpsMixin,
    UtilsMixin
):
    def __init__(self, root):
        self.root = root
        self.root.title("Lancer Map Builder")
        self.root.geometry("1200x800")

        self.map_state = MapState()
        self.settings_file = os.path.expanduser("~/.lancer_map_builder_settings.json")
        self.app_mode = tk.StringVar(value="WEBER_NHP")
        self.load_global_settings()

        self.grid = HexGrid(size=50, flat_top=False)
        self.assets = scan_assets(self.map_state.tokens_directory)
        
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
        
        # Bind delete keys
        self.root.bind("<Delete>", self.delete_selected_item)
        self.root.bind("<BackSpace>", self.delete_selected_item)
        self.root.bind("<Escape>", self.deselect_all)
        self.root.bind("<m>", self.show_marker_menu)
        self.root.bind("<M>", self.show_marker_menu)
        self.root.bind("<Key-b>", self.toggle_hex_barrier)
        self.root.bind("<Key-B>", self.toggle_hex_barrier)

        self.apply_theme()
        self.setup_ui()


if __name__ == "__main__":
    t_root = tk.Tk()
    t_app = MapBuilderApp(t_root)
    t_root.mainloop()
