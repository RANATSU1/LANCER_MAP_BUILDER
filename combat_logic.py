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

class CombatLogicMixin:
    def handle_structure_damage(self, tgt_idx, tgt_name):
        import random
        tgt_item = self.map_state.items[tgt_idx]
        
        top = tk.Toplevel(self.root)
        top.title("Structure Damage")
        top.geometry("600x420")
        top.transient(self.root)
        top.grab_set()
        
        info = (
            "STRUCTURE DAMAGE TABLE\n"
            "--------------------------------------------------\n"
            "5-6 Glancing Blow: Emergency systems kick in. IMPAIRED until end of next turn.\n"
            "2-4 System Trauma: Roll 1d6. (1-3) Weapon destroyed, (4-6) System destroyed.\n"
            "1   Direct Hit: Effects depend on remaining structure:\n"
            "      3+ Structure: STUNNED until end of next turn.\n"
            "      2 Structure: Hull Check. Success = STUNNED, Failure = DESTROYED.\n"
            "      1 Structure: DESTROYED.\n"
        )
        tk.Label(top, text=info, justify="left", font=("Consolas", 10)).pack(padx=10, pady=10)
        
        tk.Label(top, text=f"Applying Structure Damage to {tgt_name}!\nDoes the mech have a 'Custom Paint Job'?", font=("Arial", 11, "bold")).pack(pady=10)
        
        result_var = tk.StringVar(value="")
        
        def on_custom_paint():
            result_var.set("custom")
            top.destroy()
            
        def on_normal():
            result_var.set("normal")
            top.destroy()
            
        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Yes (Custom Paint Job)", command=on_custom_paint, bg="#4444ff", fg="white").pack(side="left", padx=10)
        tk.Button(btn_frame, text="No (Normal Roll)", command=on_normal).pack(side="left", padx=10)
        
        self.root.wait_window(top)
        
        res = result_var.get()
        if not res: return # window closed
        
        if res == "custom":
            cp_roll = random.randint(1, 6)
            self.log_to_terminal(f"> Custom Paint Job Roll = {cp_roll}")
            if cp_roll == 6:
                self.log_to_terminal(f"> {tgt_name}'s Custom Paint Job saved them! No continued structure damage effects.")
                return
            else:
                self.log_to_terminal(f"> Custom Paint Job failed. Taking structure damage.")
                
        # Normal Structure Roll
        struct_roll = random.randint(1, 6)
        struct_left = tgt_item.get("structure", 0)
        
        if struct_roll >= 5: # 5-6 Glancing Blow
            self.log_to_terminal(f"> Structure Roll: {struct_roll} (GLANCING BLOW)")
            self.log_to_terminal(f"> {tgt_name} is IMPAIRED.")
            self.add_marker_by_name(tgt_idx, "impaired")
            
        elif struct_roll >= 2: # 2-4 System Trauma
            sys_roll = random.randint(1, 6)
            self.log_to_terminal(f"> Structure Roll: {struct_roll} (SYSTEM TRAUMA)")
            if sys_roll <= 3:
                self.log_to_terminal(f"> System Trauma Roll: {sys_roll}. A WEAPON is destroyed!")
            else:
                self.log_to_terminal(f"> System Trauma Roll: {sys_roll}. A SYSTEM is destroyed!")
                
        else: # 1 Direct Hit
            self.log_to_terminal(f"> Structure Roll: {struct_roll} (DIRECT HIT!)")
            if struct_left >= 3:
                self.log_to_terminal(f"> DIRECT HIT! {struct_left} structure left! You're stunned!")
                self.add_marker_by_name(tgt_idx, "stunned")
            elif struct_left == 2:
                self.log_to_terminal(f"> DIRECT HIT! 2 structure left! Roll a HULL check!\nSuccess: Stunned. Failure: Destroyed.")
            else:
                self.log_to_terminal(f"> DIRECT HIT! 1 or less structure left! DESTROYED!")

    def decide_first_faction(self):
        import random
        if not hasattr(self, "acted_this_round"):
            self.acted_this_round = set()
            
        factions = set()
        for idx, item in enumerate(self.map_state.items):
            if self.is_combatant(item):
                if idx not in self.acted_this_round:
                    factions.add(item.get("faction", "Neutral"))
        
        if not factions:
            self.log_to_terminal("> No combatants found.")
            return
            
        chosen = random.choice(list(factions))
        self.log_to_terminal(f"=== {chosen.upper()} GOES FIRST ===")

    def start_turn(self):
        idx = self.get_index_from_cb(self.cb_turn.get())
        if idx is None:
            self.log_to_terminal("> Select a combatant for the next turn.")
            return
            
        if getattr(self, "active_turn_idx", None) is not None:
            self.end_turn(auto_advance=False)
            
        self.active_turn_idx = idx
        name = self.get_token_name(idx)
        self.lbl_active_turn.config(text=f"Active: {name}")
        self.log_to_terminal(f"=== {name}'s Turn Begins ===")
        
        # Add Turn marker dynamically
        item = self.map_state.items[idx]
        if "markers" not in item:
            item["markers"] = []
            
        # Try to find Turn.png
        turn_marker_path = None
        if self.map_state.markers_directory:
            possible_path = os.path.join(self.map_state.markers_directory, "Turn.png")
            if os.path.exists(possible_path):
                turn_marker_path = possible_path
                
        if turn_marker_path and turn_marker_path not in item["markers"]:
            item["markers"].append(turn_marker_path)
            
        # Reset Action Tracker points
        try:
            speed = int(item.get("speed", 0))
        except:
            speed = 0
            
        if hasattr(self, 'val_movement'):
            self.val_movement.set(speed)
            self.val_actions.set(2)
            self.val_free_actions.set(0)
            self.overcharge_used = False
            self.btn_overcharge.config(state="normal")
            
        self.update_turn_combobox()
        self.draw_wrapper()

    def end_turn(self, auto_advance=True):
        idx = getattr(self, "active_turn_idx", None)
        if idx is None:
            return
            
        name = self.get_token_name(idx)
        self.log_to_terminal(f"=== {name}'s Turn Ends ===")
        
        item = self.map_state.items[idx]
        if "markers" in item:
            to_remove = []
            for m in item["markers"]:
                if os.path.basename(m).lower() == "turn.png":
                    to_remove.append(m)
            for m in to_remove:
                item["markers"].remove(m)
                
        if not hasattr(self, "acted_this_round"):
            self.acted_this_round = set()
        self.acted_this_round.add(idx)
        
        self.active_turn_idx = None
        self.lbl_active_turn.config(text="Active: None")
        
        self.update_turn_combobox()
        self.draw_wrapper()
        
        if auto_advance and not self.cb_turn['values']:
            has_tokens = any(1 for item in self.map_state.items if "token" in item["path"].lower() or "frame" in item["path"].lower())
            if has_tokens:
                self.root.after(100, self.next_round)

    def dec_movement(self):
        v = self.val_movement.get()
        if v > 0:
            self.val_movement.set(v - 1)
            self.log_to_terminal(f"> Used 1 movement. ({v-1} left)")

    def inc_movement(self):
        v = self.val_movement.get()
        self.val_movement.set(v + 1)
        self.log_to_terminal(f"> Gained 1 movement. ({v+1} left)")

    def use_quick_action(self):
        v = self.val_actions.get()
        if v >= 1:
            self.val_actions.set(v - 1)
            self.log_to_terminal(f"> Used a Quick Action. ({v-1} acts left)")
        else:
            self.log_to_terminal(f"> Not enough actions for a Quick Action!")

    def use_full_action(self):
        v = self.val_actions.get()
        if v >= 2:
            self.val_actions.set(v - 2)
            self.log_to_terminal(f"> Used a Full Action. ({v-2} acts left)")
        else:
            self.log_to_terminal(f"> Not enough actions for a Full Action!")

    def use_free_action(self):
        v = self.val_free_actions.get()
        self.val_free_actions.set(v + 1)
        self.log_to_terminal(f"> A free action was used. ({v+1} total taken)")

    def use_overcharge(self):
        if not self.overcharge_used:
            self.overcharge_used = True
            self.val_actions.set(self.val_actions.get() + 1)
            self.btn_overcharge.config(state="disabled")
            self.log_to_terminal(f"> OVERCHARGE! Gained 1 Quick Action.")

    def next_round(self):
        self.round += 1
        self.lbl_round.config(text=f"Round: {self.round}")
        self.log_to_terminal(f"=== ROUND {self.round} BEGINS ===")
        
        self.update_turn_combobox()
        self.draw_wrapper()
        if hasattr(self, "acted_this_round"):
            self.acted_this_round.clear()
            
        # Ensure any lingering turn markers are removed
        for item in self.map_state.items:
            if "markers" in item:
                item["markers"] = [m for m in item["markers"] if os.path.basename(m).lower() != "turn.png"]
                
        self.update_turn_combobox()
        self.draw_wrapper()
    def parse_dice(self, dice_str):
        import re, random
        dice_str = str(dice_str).lower().replace(" ", "")
        match = re.match(r'^(\d*)d(\d+)(?:([+-])(\d+(?:\.\d+)?))?$', dice_str)
        if not match: return None
        
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_sides = int(match.group(2))
        
        modifier = 0.0
        if match.group(3) and match.group(4):
            mod_val = float(match.group(4))
            modifier = mod_val if match.group(3) == '+' else -mod_val
            
        return num_dice, die_sides, modifier
        
    def roll_dice_string(self, dice_str):
        import random
        try:
            val = float(dice_str)
            return [], val
        except ValueError:
            pass
            
        parsed = self.parse_dice(dice_str)
        if not parsed: return None
        num_dice, die_sides, mod = parsed
        
        rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
        total = sum(rolls) + mod
        return rolls, total

    def roll_custom_dice(self):
        import random
        dice_str = self.dice_var.get()
        parsed = self.parse_dice(dice_str)
        
        is_fixed_float = False
        fixed_val = 0.0
        if not parsed:
            try:
                fixed_val = float(dice_str)
                is_fixed_float = True
            except ValueError:
                self.log_to_terminal(f"> Invalid dice format: {dice_str}")
                return

        overlay = tk.Frame(self.root, bg=self.map_state.ui_bg_color, highlightbackground=self.map_state.ui_fg_color, highlightthickness=3)
        overlay.place(relx=0.5, rely=0.5, anchor="center", width=250, height=200)
        
        lbl_icon = tk.Label(overlay, text="🎲", font=("Segoe UI Emoji", 48), bg=self.map_state.ui_bg_color, fg=self.map_state.ui_fg_color)
        lbl_icon.pack(expand=True, pady=(20, 0))
        
        lbl_val = tk.Label(overlay, text="?", font=("Consolas", 32, "bold"), bg=self.map_state.ui_bg_color, fg=self.map_state.ui_fg_color)
        lbl_val.pack(expand=True, pady=(0, 20))
        
        rolls_made = 0
        max_rolls = 10
        if not is_fixed_float:
            num_dice, die_sides, mod = parsed
        else:
            num_dice, die_sides, mod = 0, 0, 0
        
        def animate_roll():
            nonlocal rolls_made
            if rolls_made < max_rolls:
                if is_fixed_float:
                    fake_val = fixed_val
                else:
                    fake_val = sum(random.randint(1, die_sides) for _ in range(num_dice)) + mod
                lbl_val.config(text=str(fake_val))
                rolls_made += 1
                self.root.after(100, animate_roll)
            else:
                res = self.roll_dice_string(dice_str)
                if res is not None:
                    rolls_res, total = res
                    lbl_val.config(text=str(total))
                    
                    if is_fixed_float:
                        self.log_to_terminal(f"> Fixed Value {dice_str}: = {total}")
                    else:
                        mod_str = ""
                        if mod > 0: mod_str = f"+{mod}"
                        elif mod < 0: mod_str = f"{mod}"
                        self.log_to_terminal(f"> Rolled {dice_str}: {rolls_res}{mod_str} = {total}")
                
                self.root.after(1500, overlay.destroy)

        animate_roll()


    def perform_attack(self):
        import random
        if getattr(self, "active_turn_idx", None) is None:
            self.log_to_terminal("> Attack Error: A Turn must be active to perform an attack.")
            messagebox.showwarning("Attack Error", "You must start someone's turn before attacking!")
            return

        atk_idx = self.get_index_from_cb(self.cb_attacker.get())
        tgt_idx = self.get_index_from_cb(self.cb_target.get())
        
        if atk_idx is None or tgt_idx is None:
            self.log_to_terminal("> Attack Error: Select Attacker and Target")
            return
            
        atk_name = self.get_token_name(atk_idx)
        tgt_name = self.get_token_name(tgt_idx)
        
        tgt_item = self.map_state.items[tgt_idx]
        
        is_edefense = messagebox.askyesno("Attack Defense", f"Does this attack target E-Defense?\n(Yes = E-Defense / No = Evasion)")
        defense_val = tgt_item.get("e_defense", 8) if is_edefense else tgt_item.get("evasion", 8)
        defense_name = "E-Defense" if is_edefense else "Evasion"
        
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
            self.log_to_terminal(f"> Attack: [CRIT 20] + {bonus} = {atk_total} vs {defense_name} {defense_val}")
            self.apply_damage(tgt_idx, self.atk_dmg_var.get(), is_crit=True, resist=self.res_var.get())
            self.prompt_marker_after_attack(tgt_idx)
            
        elif atk_total >= defense_val: # HIT
            self.log_to_terminal(f"### {atk_name} attacks {tgt_name} ###")
            self.log_to_terminal(f"> Attack: {d20} + {bonus} = {atk_total} vs {defense_name} {defense_val} (HIT)")
            self.apply_damage(tgt_idx, self.atk_dmg_var.get(), is_crit=False, resist=self.res_var.get())
            self.prompt_marker_after_attack(tgt_idx)
            
        else: # MISS
            self.log_to_terminal(f"### {atk_name} attacks {tgt_name} ###")
            self.log_to_terminal(f"> Attack: {d20} + {bonus} = {atk_total} vs {defense_name} {defense_val} (MISS)")

    def prompt_marker_after_attack(self, tgt_idx):
        tgt_name = self.get_token_name(tgt_idx)
        if messagebox.askyesno("Apply Marker", f"Does the attack apply any condition/marker to {tgt_name}?"):
            self.selected_item_index = tgt_idx
            self.show_marker_menu()

    def apply_damage(self, target_idx, dmg_str, is_crit=False, resist=False):
        import math
        tgt_name = self.get_token_name(target_idx)
        res = self.roll_dice_string(dmg_str)
        if res is None:
            self.log_to_terminal(f"> Error: Invalid damage format {dmg_str}")
            return
            
        rolls, total_dmg = res
        
        if is_crit:
            res2 = self.roll_dice_string(dmg_str)
            rolls2, total2 = res2
            self.log_to_terminal(f"> Crit Damage Roll 1: {rolls} = {total_dmg}")
            self.log_to_terminal(f"> Crit Damage Roll 2: {rolls2} = {total2}")
            total_dmg = max(total_dmg, total2)
            self.log_to_terminal(f"> Choice (Highest Total): {total_dmg}")
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
            
            while tgt_item['hp'] <= 0:
                self.log_to_terminal(f"> {tgt_name} HP DEPLETED!")
                if tgt_item.get('structure', 0) > 0:
                    excess = -tgt_item['hp']
                    tgt_item['structure'] -= 1
                    
                    new_max = tgt_item.get('max_hp', 0)
                    tgt_item['hp'] = new_max - excess
                    
                    self.log_to_terminal(f"> {tgt_name} loses 1 Structure. Struct: {tgt_item['structure']}. HP Reset with OVERFLOW -{excess} dmg. New HP: {tgt_item['hp']}")
                    self.handle_structure_damage(target_idx, tgt_name)
                    
                    if tgt_item.get('structure', 0) <= 0 and tgt_item['hp'] <= 0:
                        self.log_to_terminal(f"> {tgt_name} HAS BEEN DESTROYED!")
                        tgt_item['hp'] = 0
                        break
                else:
                    self.log_to_terminal(f"> {tgt_name} HAS BEEN DESTROYED!")
                    tgt_item['hp'] = 0
                    break
        else:
            self.log_to_terminal(f"> {tgt_name} has no HP stats to reduce.")
            
        if self.selected_item_index == target_idx:
            self.update_attachment_ui()

