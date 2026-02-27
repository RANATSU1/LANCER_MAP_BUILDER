import os
import sys

def get_asset_root():
    # Helper to find where we are running from
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Check potential locations for MAPS
    # 1. sibling to exe/script (e.g. if exe is in Lancer root)
    path1 = os.path.join(base_dir, "MAPS")
    if os.path.exists(path1):
        return path1

    # 2. parent of exe/script (e.g. if exe is in MapBuilder folder)
    path2 = os.path.join(os.path.dirname(base_dir), "MAPS")
    if os.path.exists(path2):
        return path2
        
    # 3. Development path (specific to current structure)
    # Lancer/MapBuilder/assets.py -> Lancer/MAPS
    # (Covered by #2 if base_dir is MapBuilder)

    return path1 # Default to sibling, even if missing

ASSET_ROOT = get_asset_root()

def scan_assets():
    """
    Scans the MAPS directory for assets.
    Returns a dictionary of structure:
    {
        "Pack Name": {
            "Tokens": [path1, path2, ...],
            "Tiles": [path1, path2, ...],
            "Other": ...
        },
        ...
    }
    """
    assets = {}

    if not os.path.exists(ASSET_ROOT):
        print(f"Warning: Asset root not found at {ASSET_ROOT}")
        return assets

    print(f"Scanning assets in: {ASSET_ROOT}")

    # Top level directories are usually "Packs"
    for pack_name in os.listdir(ASSET_ROOT):
        pack_path = os.path.join(ASSET_ROOT, pack_name)
        if not os.path.isdir(pack_path):
            continue
        
        assets[pack_name] = {}
        
        # Recursive walk to find images
        for root, dirs, files in os.walk(pack_path):
            lower_root = root.lower()
            
            # Determine Category
            category = "Other"
            if "token" in lower_root:
                category = "Tokens"
            elif "tile" in lower_root:
                category = "Tiles"
            elif "hex" in lower_root:
                category = "Tiles"
            
            # Initialize category if missing
            if category not in assets[pack_name]:
                assets[pack_name][category] = []

            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif')):
                    full_path = os.path.join(root, file)
                    assets[pack_name][category].append(full_path)

    # Post-processing: Filter for 8x preference
    final_assets = {}
    
    for pack, categories in assets.items():
        pack_data = {}
        has_content = False
        
        for cat, paths in categories.items():
            if not paths:
                continue
                
            # Check if this category has any "8x" files
            has_8x = any("8x" in p.lower() for p in paths)
            
            if has_8x:
                # If we have 8x files, only keep those to avoid duplicates/low-res
                filtered = [p for p in paths if "8x" in p.lower()]
                pack_data[cat] = sorted(filtered)
            else:
                pack_data[cat] = sorted(paths)
            
            if pack_data[cat]:
                has_content = True
        
        if has_content:
            final_assets[pack] = pack_data

    return final_assets

if __name__ == "__main__":
    # Test run
    results = scan_assets()
    for pack, cats in results.items():
        print(f"Pack: {pack}")
        for cat, files in cats.items():
            print(f"  {cat}: {len(files)} files")
            if files:
                print(f"    Example: {os.path.basename(files[0])}")
