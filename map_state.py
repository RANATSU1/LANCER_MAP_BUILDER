import json

class MapState:
    def __init__(self):
        self.items = []  # List of dicts: { "type": "token"|"tile", "path": str, "q": int, "r": int, "s": float, "rot": int }
        self.drawings = [] # List of dicts for paint tools
        self.background_color = "#000000"
        self.grid_size = 50
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        self.background_image = None
        self.grid_color = "#39ff14"
        self.ui_bg_color = "#000000"
        self.ui_fg_color = "#39ff14"
        self.tokens_directory = None
        self.markers_directory = None

    def add_item(self, path, q, r, item_type="token", scale=1.0, rotation=0):
        self.items.append({
            "path": path,
            "q": q,
            "r": r,
            "type": item_type,
            "scale": scale,
            "rotation": rotation
        })

    def remove_item_at(self, q, r):
        # Remove top-most item at coordinates
        for i in range(len(self.items) - 1, -1, -1):
            if self.items[i]["q"] == q and self.items[i]["r"] == r:
                del self.items[i]
                return True
        return False

    def clear(self):
        self.items = []
        self.drawings = []
        self.background_image = None

    def to_dict(self):
        return {
            "background_image": self.background_image,
            "background_color": self.background_color,
            "grid_size": self.grid_size,
            "grid_color": self.grid_color,
            "ui_bg_color": self.ui_bg_color,
            "ui_fg_color": self.ui_fg_color,
            "tokens_directory": self.tokens_directory,
            "markers_directory": self.markers_directory,
            "grid_offset_x": self.grid_offset_x,
            "grid_offset_y": self.grid_offset_y,
            "items": self.items,
            "drawings": self.drawings
        }

    def save_to_file(self, filepath):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def load_from_file(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.background_color = data.get("background_color", "#000000")
        self.background_image = data.get("background_image", None)
        self.grid_size = data.get("grid_size", 50)
        self.grid_color = data.get("grid_color", "#39ff14")
        self.ui_bg_color = data.get("ui_bg_color", "#000000")
        self.ui_fg_color = data.get("ui_fg_color", "#39ff14")
        self.tokens_directory = data.get("tokens_directory", None)
        self.markers_directory = data.get("markers_directory", None)
        self.grid_offset_x = data.get("grid_offset_x", 0)
        self.grid_offset_y = data.get("grid_offset_y", 0)
        self.items = data.get("items", [])
        self.drawings = data.get("drawings", [])
