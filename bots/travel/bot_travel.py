"""
🗺️ Dofus Retro Travel Bot v3.3
Bot de déplacement automatique
- Entrée manuelle facile
- Zaaps automatiques
- Pathfinding A*
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import time
import threading
import heapq

try:
    import pyautogui
    import keyboard
    from PIL import ImageGrab, Image, ImageTk
    HAS_DEPS = True
except ImportError as e:
    print(f"Import error: {e}")
    HAS_DEPS = False


# ============================================================
#                    CONFIGURATION
# ============================================================

class Config:
    def __init__(self):
        try:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.script_dir = os.getcwd()
        
        self.config_file = os.path.join(self.script_dir, "travel_config.json")
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return self.default_config()
    
    def default_config(self):
        return {
            "click_positions": {
                "right": {"x": 1250, "y": 400},
                "left": {"x": 240, "y": 400},
                "up": {"x": 750, "y": 50},
                "down": {"x": 750, "y": 620}
            },
            "zaap_click": {"x": 600, "y": 400},
            "move_delay": 1.5,
            "zaap_delay": 2.5,
            "known_zaaps": ["Astrub", "Amakna Village"],
            "use_zaaps": True,
            "last_position": {"x": 4, "y": -19}
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False


# ============================================================
#                    WORLD MAP
# ============================================================

class WorldMap:
    ZAAPS = {
        "Astrub (4, -19)": (4, -19),
        "Astrub Centre (5, -18)": (5, -18),
        "Amakna Village (0, 0)": (0, 0),
        "Amakna Château (3, -5)": (3, -5),
        "Port Madrestam (7, -4)": (7, -4),
        "Coin des Bouftous (5, 7)": (5, 7),
        "Bord de Forêt (-1, 13)": (-1, 13),
        "Bonta (-26, -36)": (-26, -36),
        "Brakmar (-26, 35)": (-26, 35),
        "Sufokia (13, 26)": (13, 26),
    }
    
    # Lieux utiles (non-zaap)
    PLACES = {
        "Astrub - Banque": (4, -18),
        "Astrub - Zaap": (4, -19),
        "Amakna - Zaap": (0, 0),
        "Amakna - Banque": (4, -3),
        "Champs de Blé": (0, -1),
        "Mine Astrub": (1, -20),
    }
    
    BLOCKED_MAPS = set()
    
    @classmethod
    def get_neighbors(cls, x, y):
        neighbors = []
        directions = [("right", x+1, y), ("left", x-1, y), ("up", x, y-1), ("down", x, y+1)]
        for d, nx, ny in directions:
            if (nx, ny) not in cls.BLOCKED_MAPS:
                neighbors.append((d, nx, ny, 1))
        return neighbors
    
    @classmethod
    def get_zaap_list(cls):
        return list(cls.ZAAPS.keys())
    
    @classmethod
    def get_zaap_pos(cls, name):
        return cls.ZAAPS.get(name)
    
    @classmethod
    def get_places_list(cls):
        return list(cls.PLACES.keys())
    
    @classmethod
    def get_place_pos(cls, name):
        return cls.PLACES.get(name)
    
    @classmethod
    def find_nearest_zaap(cls, x, y, known):
        nearest, min_dist = None, float('inf')
        for name in known:
            for zaap_name, pos in cls.ZAAPS.items():
                if name in zaap_name:
                    dist = abs(x-pos[0]) + abs(y-pos[1])
                    if dist < min_dist:
                        min_dist, nearest = dist, (zaap_name, pos[0], pos[1])
        return nearest, min_dist
    
    @classmethod
    def is_on_zaap(cls, x, y, known):
        for name in known:
            for zaap_name, pos in cls.ZAAPS.items():
                if name in zaap_name and pos == (x, y):
                    return zaap_name
        return None


# ============================================================
#                    PATHFINDING
# ============================================================

class Pathfinder:
    def __init__(self, use_zaaps=True, known_zaaps=None):
        self.use_zaaps = use_zaaps
        self.known_zaaps = known_zaaps or []
    
    def find_path(self, start, goal, max_iter=50000):
        if start == goal:
            return []
        
        counter = 0
        open_set = [(0, counter, start, [])]
        closed, g_scores = set(), {start: 0}
        
        while open_set and counter < max_iter:
            _, _, current, path = heapq.heappop(open_set)
            
            if current == goal:
                return path
            if current in closed:
                continue
            closed.add(current)
            
            for d, nx, ny, cost in WorldMap.get_neighbors(current[0], current[1]):
                neighbor = (nx, ny)
                if neighbor in closed:
                    continue
                g = g_scores.get(current, float('inf')) + cost
                if g < g_scores.get(neighbor, float('inf')):
                    g_scores[neighbor] = g
                    f = g + abs(goal[0]-nx) + abs(goal[1]-ny)
                    counter += 1
                    heapq.heappush(open_set, (f, counter, neighbor, path + [(d, neighbor)]))
            
            # Zaaps
            if self.use_zaaps and self.known_zaaps:
                zaap = WorldMap.is_on_zaap(current[0], current[1], self.known_zaaps)
                if zaap:
                    for dest_name, dest_pos in WorldMap.ZAAPS.items():
                        if any(k in dest_name for k in self.known_zaaps) and dest_name != zaap:
                            if dest_pos in closed:
                                continue
                            g = g_scores.get(current, float('inf')) + 2
                            if g < g_scores.get(dest_pos, float('inf')):
                                g_scores[dest_pos] = g
                                f = g + abs(goal[0]-dest_pos[0]) + abs(goal[1]-dest_pos[1])
                                counter += 1
                                heapq.heappush(open_set, (f, counter, dest_pos, path + [(f"zaap:{dest_name}", dest_pos)]))
        
        return None
    
    def find_best_path(self, start, goal):
        direct = self.find_path(start, goal)
        best = direct
        
        if self.use_zaaps and self.known_zaaps:
            dest_zaap, d_dist = WorldMap.find_nearest_zaap(goal[0], goal[1], self.known_zaaps)
            if dest_zaap:
                start_zaap, s_dist = WorldMap.find_nearest_zaap(start[0], start[1], self.known_zaaps)
                if start_zaap and start_zaap[0] != dest_zaap[0]:
                    if s_dist + 2 + d_dist < (len(direct) if direct else float('inf')):
                        p1 = self.find_path(start, (start_zaap[1], start_zaap[2]))
                        p2 = self.find_path((dest_zaap[1], dest_zaap[2]), goal)
                        if p1 is not None and p2 is not None:
                            best = p1 + [(f"zaap:{dest_zaap[0]}", (dest_zaap[1], dest_zaap[2]))] + p2
        
        return best


# ============================================================
#                    BOT
# ============================================================

class TravelBot:
    def __init__(self, config, log_callback=None, pos_callback=None):
        self.config = config
        self.log = log_callback or print
        self.on_position_change = pos_callback
        
        self.running = False
        self.paused = False
        self.stop_requested = False
        
        self.current_pos = None
        self.target_pos = None
        self.current_path = []
        self.path_index = 0
        
        self.pathfinder = Pathfinder(
            use_zaaps=config.data.get("use_zaaps", True),
            known_zaaps=config.data.get("known_zaaps", [])
        )
        
        # Charger dernière position
        last = config.data.get("last_position", {})
        if last:
            self.current_pos = (last.get("x", 0), last.get("y", 0))
    
    def set_position(self, x, y):
        self.current_pos = (x, y)
        self.config.data["last_position"] = {"x": x, "y": y}
        self.config.save()
        self.log(f"📍 Position: [{x}, {y}]")
        if self.on_position_change:
            self.on_position_change(x, y)
    
    def calculate_path(self, tx, ty):
        if not self.current_pos:
            self.log("❌ Entre ta position d'abord!")
            return None
        
        self.target_pos = (tx, ty)
        self.log(f"🗺️ Calcul [{self.current_pos[0]},{self.current_pos[1]}] → [{tx},{ty}]")
        
        self.pathfinder.known_zaaps = self.config.data.get("known_zaaps", [])
        self.pathfinder.use_zaaps = self.config.data.get("use_zaaps", True)
        
        path = self.pathfinder.find_best_path(self.current_pos, self.target_pos)
        if path:
            self.current_path = path
            self.path_index = 0
            self.log(f"✅ {len(path)} étapes")
            return path
        elif self.current_pos == self.target_pos:
            self.log("✅ Tu es déjà à destination!")
            return []
        self.log("❌ Pas de chemin trouvé!")
        return None
    
    def click_direction(self, d):
        pos = self.config.data.get("click_positions", {}).get(d)
        if pos:
            pyautogui.click(pos["x"], pos["y"])
            return True
        return False
    
    def use_zaap(self, dest):
        self.log(f"🌀 Zaap → {dest.split('(')[0].strip()}")
        zaap = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        pyautogui.click(zaap["x"], zaap["y"])
        time.sleep(1)
        
        # Menu zaap - positions approximatives
        menu = {
            "Astrub": (500, 280),
            "Amakna Village": (500, 300),
            "Amakna Château": (500, 320),
            "Bonta": (500, 340),
            "Brakmar": (500, 360),
        }
        
        for name, pos in menu.items():
            if name in dest:
                pyautogui.doubleClick(*pos)
                break
        
        time.sleep(self.config.data.get("zaap_delay", 2.5))
        return True
    
    def execute_move(self, move, target):
        if str(move).startswith("zaap:"):
            self.use_zaap(move.split(":", 1)[1])
            self.set_position(target[0], target[1])
            return True
        else:
            icons = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            self.log(f"🚶 {icons.get(move, '?')} [{target[0]},{target[1]}]")
            if self.click_direction(move):
                time.sleep(self.config.data.get("move_delay", 1.5))
                self.set_position(target[0], target[1])
                return True
            return False
    
    def start_travel(self):
        if not self.current_path or self.running:
            return
        
        self.running = True
        self.paused = False
        self.stop_requested = False
        self.path_index = 0
        threading.Thread(target=self._loop, daemon=True).start()
    
    def _loop(self):
        total = len(self.current_path)
        self.log(f"🚀 Départ! {total} étapes")
        
        while self.running and self.path_index < total:
            if self.stop_requested:
                break
            while self.paused and not self.stop_requested:
                time.sleep(0.1)
            if self.stop_requested:
                break
            
            move, target = self.current_path[self.path_index]
            self.log(f"[{self.path_index+1}/{total}]")
            
            if self.execute_move(move, target):
                self.path_index += 1
            else:
                time.sleep(1)
        
        if self.path_index >= total and not self.stop_requested:
            self.log(f"🎉 Arrivé à destination!")
        self.running = False
    
    def pause(self):
        self.paused = not self.paused
        self.log("⏸️ Pause" if self.paused else "▶️ Reprise")
    
    def stop(self):
        self.stop_requested = True
        self.running = False
        self.log("⏹️ Arrêté")


# ============================================================
#                    GUI
# ============================================================

THEME = {
    'bg': '#1a1a2e', 'bg2': '#16213e', 'bg3': '#0f3460',
    'card': '#1f4068', 'accent': '#e94560', 'accent2': '#4cc9f0',
    'success': '#00d26a', 'warning': '#ff9f1c',
    'text': '#ffffff', 'text2': '#8b8b9e'
}


class TravelBotGUI:
    def __init__(self):
        self.config = Config()
        self.bot = TravelBot(self.config, self.log, self.update_position_display)
        
        self.setup_window()
        self.create_widgets()
        self.setup_hotkeys()
        
        # Afficher dernière position
        if self.bot.current_pos:
            self.current_x.delete(0, 'end')
            self.current_x.insert(0, str(self.bot.current_pos[0]))
            self.current_y.delete(0, 'end')
            self.current_y.insert(0, str(self.bot.current_pos[1]))
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🗺️ Dofus Travel Bot v3.3")
        self.root.geometry("700x850")
        self.root.configure(bg=THEME['bg'])
        self.root.resizable(True, True)
    
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('F5', self.start_travel)
            keyboard.add_hotkey('F6', self.pause_travel)
            keyboard.add_hotkey('F7', self.stop_travel)
        except:
            pass
    
    def update_position_display(self, x, y):
        """Met à jour l'affichage de la position"""
        self.root.after(0, lambda: self._update_pos(x, y))
    
    def _update_pos(self, x, y):
        self.current_x.delete(0, 'end')
        self.current_x.insert(0, str(x))
        self.current_y.delete(0, 'end')
        self.current_y.insert(0, str(y))
        self.pos_label.config(text=f"Position actuelle: [{x}, {y}]")
    
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=THEME['accent'], height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🗺️ DOFUS TRAVEL BOT", font=('Segoe UI', 20, 'bold'),
                bg=THEME['accent'], fg='white').pack(pady=10)
        
        self.pos_label = tk.Label(header, text="Position actuelle: [?, ?]", 
                                  font=('Segoe UI', 11),
                                  bg=THEME['accent'], fg='white')
        self.pos_label.pack()
        
        # Tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.create_navigation_tab(notebook)
        self.create_calibration_tab(notebook)
        self.create_zaaps_tab(notebook)
        
        # Status bar
        status = tk.Frame(self.root, bg=THEME['bg2'], height=30)
        status.pack(fill='x', side='bottom')
        tk.Label(status, text="F5 = Démarrer • F6 = Pause • F7 = Stop",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(pady=5)
    
    def create_navigation_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🗺️ Navigation")
        
        # ═══════════════════════════════════════════════
        # POSITION ACTUELLE
        # ═══════════════════════════════════════════════
        frame = tk.LabelFrame(tab, text="📍 TA POSITION (regarde en haut à gauche dans Dofus)", 
                              font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        # Aide
        tk.Label(frame, text="💡 Dans Dofus, ta position est affichée: \"Coordonnées : X, Y\"",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(anchor='w')
        
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x', pady=10)
        
        tk.Label(row, text="X:", font=('Segoe UI', 12, 'bold'), 
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.current_x = tk.Entry(row, width=8, font=('Segoe UI', 14), 
                                  bg=THEME['bg3'], fg=THEME['text'],
                                  justify='center')
        self.current_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", font=('Segoe UI', 12, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(20, 0))
        self.current_y = tk.Entry(row, width=8, font=('Segoe UI', 14),
                                  bg=THEME['bg3'], fg=THEME['text'],
                                  justify='center')
        self.current_y.pack(side='left', padx=5)
        
        tk.Button(row, text="✅ VALIDER", font=('Segoe UI', 10, 'bold'),
                 bg=THEME['success'], fg='white', padx=15,
                 command=self.set_position).pack(side='left', padx=20)
        
        # ═══════════════════════════════════════════════
        # DESTINATION
        # ═══════════════════════════════════════════════
        frame = tk.LabelFrame(tab, text="🎯 DESTINATION", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        # Coordonnées manuelles
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x', pady=5)
        
        tk.Label(row, text="X:", font=('Segoe UI', 12, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.dest_x = tk.Entry(row, width=8, font=('Segoe UI', 14),
                               bg=THEME['bg3'], fg=THEME['text'],
                               justify='center')
        self.dest_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", font=('Segoe UI', 12, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(20, 0))
        self.dest_y = tk.Entry(row, width=8, font=('Segoe UI', 14),
                               bg=THEME['bg3'], fg=THEME['text'],
                               justify='center')
        self.dest_y.pack(side='left', padx=5)
        
        # Zaaps dropdown
        tk.Label(frame, text="─── OU choisir un Zaap ───",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(pady=5)
        
        self.zaap_var = tk.StringVar()
        zaap_combo = ttk.Combobox(frame, textvariable=self.zaap_var, width=35,
                                  values=WorldMap.get_zaap_list(), state='readonly',
                                  font=('Segoe UI', 10))
        zaap_combo.pack()
        zaap_combo.bind('<<ComboboxSelected>>', self.on_zaap_selected)
        
        # ═══════════════════════════════════════════════
        # OPTIONS
        # ═══════════════════════════════════════════════
        frame = tk.LabelFrame(tab, text="⚙️ Options", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        self.use_zaaps_var = tk.BooleanVar(value=self.config.data.get("use_zaaps", True))
        tk.Checkbutton(row, text="🌀 Utiliser les Zaaps", variable=self.use_zaaps_var,
                      font=('Segoe UI', 10), bg=THEME['bg2'], fg=THEME['text'],
                      selectcolor=THEME['bg3']).pack(side='left')
        
        tk.Label(row, text="Délai:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(30, 5))
        self.delay_var = tk.StringVar(value=str(self.config.data.get("move_delay", 1.5)))
        tk.Spinbox(row, from_=0.5, to=5.0, increment=0.1, width=5,
                  textvariable=self.delay_var, font=('Segoe UI', 10)).pack(side='left')
        tk.Label(row, text="sec", bg=THEME['bg2'], fg=THEME['text2']).pack(side='left', padx=5)
        
        # ═══════════════════════════════════════════════
        # BOUTONS
        # ═══════════════════════════════════════════════
        frame = tk.Frame(tab, bg=THEME['bg'])
        frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(frame, text="🔍 CALCULER LE CHEMIN", font=('Segoe UI', 12, 'bold'),
                 bg=THEME['accent2'], fg='white', width=25, height=2,
                 command=self.calculate_path).pack(pady=5)
        
        row = tk.Frame(frame, bg=THEME['bg'])
        row.pack(pady=5)
        
        tk.Button(row, text="▶️ GO! (F5)", font=('Segoe UI', 12, 'bold'),
                 bg=THEME['success'], fg='white', width=14, height=2,
                 command=self.start_travel).pack(side='left', padx=5)
        tk.Button(row, text="⏸️ Pause (F6)", font=('Segoe UI', 10),
                 bg=THEME['warning'], fg='white', width=12, height=2,
                 command=self.pause_travel).pack(side='left', padx=5)
        tk.Button(row, text="⏹️ Stop (F7)", font=('Segoe UI', 10),
                 bg=THEME['accent'], fg='white', width=12, height=2,
                 command=self.stop_travel).pack(side='left', padx=5)
        
        # ═══════════════════════════════════════════════
        # CHEMIN + LOG
        # ═══════════════════════════════════════════════
        frame = tk.LabelFrame(tab, text="📋 Chemin calculé", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        frame.pack(fill='x', padx=10, pady=5)
        self.path_text = tk.Text(frame, height=4, font=('Consolas', 9),
                                 bg=THEME['bg3'], fg=THEME['text'])
        self.path_text.pack(fill='x')
        
        frame = tk.LabelFrame(tab, text="📜 Log", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.log_text = tk.Text(frame, height=8, font=('Consolas', 9),
                                bg=THEME['bg3'], fg=THEME['text'])
        self.log_text.pack(fill='both', expand=True)
        
        self.log("🗺️ Travel Bot v3.3")
        self.log("─" * 35)
        self.log("1. Entre ta position (depuis Dofus)")
        self.log("2. Entre ta destination ou choisis un Zaap")
        self.log("3. Clique CALCULER puis GO!")
    
    def create_calibration_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🎯 Calibration")
        
        tk.Label(tab, text="🎯 Calibration des clics", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=15)
        
        tk.Label(tab, text="Configure où le bot doit cliquer pour changer de map",
                font=('Segoe UI', 10), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        # Clics
        frame = tk.LabelFrame(tab, text="🖱️ Positions de clic",
                              font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=20, pady=15)
        
        self.click_entries = {}
        for d, label in [("up", "↑ Haut"), ("down", "↓ Bas"), ("left", "← Gauche"), ("right", "→ Droite")]:
            row = tk.Frame(frame, bg=THEME['bg2'])
            row.pack(fill='x', pady=3)
            
            tk.Label(row, text=f"{label}:", width=12, anchor='w', font=('Segoe UI', 10),
                    bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            
            pos = self.config.data.get("click_positions", {}).get(d, {"x": 0, "y": 0})
            
            tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            x_e = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'], font=('Segoe UI', 10))
            x_e.insert(0, str(pos["x"]))
            x_e.pack(side='left', padx=3)
            
            tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            y_e = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'], font=('Segoe UI', 10))
            y_e.insert(0, str(pos["y"]))
            y_e.pack(side='left', padx=3)
            
            self.click_entries[d] = (x_e, y_e)
            
            tk.Button(row, text="🎯 Calibrer", bg=THEME['accent2'], fg='white',
                     command=lambda d=d: self.calibrate_click(d)).pack(side='left', padx=10)
        
        # Zaap
        frame = tk.LabelFrame(tab, text="🌀 Position du Zaap sur la map",
                              font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=20, pady=10)
        
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        zaap = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.zaap_x = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'], font=('Segoe UI', 10))
        self.zaap_x.insert(0, str(zaap["x"]))
        self.zaap_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.zaap_y = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'], font=('Segoe UI', 10))
        self.zaap_y.insert(0, str(zaap["y"]))
        self.zaap_y.pack(side='left', padx=5)
        
        tk.Button(row, text="🎯 Calibrer", bg=THEME['accent2'], fg='white',
                 command=self.calibrate_zaap).pack(side='left', padx=10)
        
        # Save
        tk.Button(tab, text="💾 SAUVEGARDER", font=('Segoe UI', 12, 'bold'),
                 bg=THEME['success'], fg='white', width=20,
                 command=self.save_calibration).pack(pady=20)
    
    def create_zaaps_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🌀 Zaaps")
        
        tk.Label(tab, text="🌀 Zaaps connus par ton personnage", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        tk.Label(tab, text="Coche les zaaps que tu as débloqués dans le jeu",
                font=('Segoe UI', 10), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        # Liste scrollable
        container = tk.Frame(tab, bg=THEME['bg2'])
        container.pack(fill='both', expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(container, bg=THEME['bg2'], highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=THEME['bg2'])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        known = self.config.data.get("known_zaaps", [])
        self.zaap_vars = {}
        
        for name, pos in WorldMap.ZAAPS.items():
            short_name = name.split(" (")[0]
            var = tk.BooleanVar(value=(short_name in known or name in known))
            self.zaap_vars[short_name] = var
            
            f = tk.Frame(scroll_frame, bg=THEME['bg2'])
            f.pack(fill='x', padx=10, pady=3)
            
            tk.Checkbutton(f, text=name, variable=var, font=('Segoe UI', 10),
                          bg=THEME['bg2'], fg=THEME['text'],
                          selectcolor=THEME['bg3']).pack(side='left')
        
        # Boutons
        row = tk.Frame(tab, bg=THEME['bg'])
        row.pack(pady=10)
        tk.Button(row, text="✅ Tout cocher", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(True) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(row, text="❌ Tout décocher", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(False) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(row, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 font=('Segoe UI', 10, 'bold'),
                 command=self.save_zaaps).pack(side='left', padx=15)
    
    # ═══════════════════════════════════════════════
    # MÉTHODES
    # ═══════════════════════════════════════════════
    
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self._log(f"[{ts}] {msg}"))
    
    def _log(self, msg):
        self.log_text.insert('end', msg + "\n")
        self.log_text.see('end')
    
    def set_position(self):
        try:
            x = int(self.current_x.get())
            y = int(self.current_y.get())
            self.bot.set_position(x, y)
        except ValueError:
            messagebox.showerror("Erreur", "Entre des coordonnées valides!\n\nExemple: X=4, Y=-19")
    
    def on_zaap_selected(self, event):
        pos = WorldMap.get_zaap_pos(self.zaap_var.get())
        if pos:
            self.dest_x.delete(0, 'end')
            self.dest_x.insert(0, str(pos[0]))
            self.dest_y.delete(0, 'end')
            self.dest_y.insert(0, str(pos[1]))
            self.log(f"🎯 Destination: {self.zaap_var.get()}")
    
    def calculate_path(self):
        # Valider position actuelle
        try:
            cx = int(self.current_x.get())
            cy = int(self.current_y.get())
        except ValueError:
            messagebox.showerror("Erreur", "Entre ta position actuelle!\n\n"
                               "Regarde en haut à gauche dans Dofus:\n"
                               "\"Coordonnées : X, Y\"")
            return
        
        # Valider destination
        try:
            dx = int(self.dest_x.get())
            dy = int(self.dest_y.get())
        except ValueError:
            messagebox.showerror("Erreur", "Entre une destination!\n\n"
                               "Soit des coordonnées X/Y, soit choisis un Zaap")
            return
        
        # Sauvegarder options
        self.config.data["use_zaaps"] = self.use_zaaps_var.get()
        try:
            self.config.data["move_delay"] = float(self.delay_var.get())
        except:
            pass
        self.config.save()
        
        # Calculer
        self.bot.set_position(cx, cy)
        path = self.bot.calculate_path(dx, dy)
        
        # Afficher
        self.path_text.delete('1.0', 'end')
        if path:
            arrows = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            self.path_text.insert('end', f"[{cx},{cy}] → [{dx},{dy}] = {len(path)} étapes\n")
            for i, (m, p) in enumerate(path[:10]):  # Max 10 lignes
                if str(m).startswith("zaap:"):
                    name = m.split(":")[1].split("(")[0].strip()
                    self.path_text.insert('end', f"{i+1}. 🌀 {name}\n")
                else:
                    self.path_text.insert('end', f"{i+1}. {arrows.get(m,'?')} [{p[0]},{p[1]}]\n")
            if len(path) > 10:
                self.path_text.insert('end', f"... +{len(path)-10} étapes\n")
        elif path == []:
            self.path_text.insert('end', "✅ Tu es déjà à destination!")
        else:
            self.path_text.insert('end', "❌ Pas de chemin trouvé!")
    
    def start_travel(self):
        if not self.bot.current_path:
            self.calculate_path()
        if self.bot.current_path:
            self.bot.start_travel()
    
    def pause_travel(self):
        self.bot.pause()
    
    def stop_travel(self):
        self.bot.stop()
    
    def calibrate_click(self, d):
        labels = {"up": "HAUT", "down": "BAS", "left": "GAUCHE", "right": "DROITE"}
        messagebox.showinfo("Calibration", 
                           f"Clique OK, puis dans 3 secondes,\n"
                           f"clique sur le bord {labels[d]} de l'écran Dofus\n"
                           f"(là où tu cliques pour changer de map)")
        
        def do():
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            self.click_entries[d][0].delete(0, 'end')
            self.click_entries[d][0].insert(0, str(x))
            self.click_entries[d][1].delete(0, 'end')
            self.click_entries[d][1].insert(0, str(y))
            self.log(f"✅ {d}: X={x}, Y={y}")
        
        threading.Thread(target=do, daemon=True).start()
    
    def calibrate_zaap(self):
        messagebox.showinfo("Calibration",
                           "Clique OK, puis dans 3 secondes,\n"
                           "clique sur le ZAAP dans le jeu")
        
        def do():
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            self.zaap_x.delete(0, 'end')
            self.zaap_x.insert(0, str(x))
            self.zaap_y.delete(0, 'end')
            self.zaap_y.insert(0, str(y))
            self.log(f"✅ Zaap: X={x}, Y={y}")
        
        threading.Thread(target=do, daemon=True).start()
    
    def save_calibration(self):
        try:
            for d, (x_e, y_e) in self.click_entries.items():
                self.config.data["click_positions"][d] = {
                    "x": int(x_e.get()), "y": int(y_e.get())
                }
            
            self.config.data["zaap_click"] = {
                "x": int(self.zaap_x.get()),
                "y": int(self.zaap_y.get())
            }
            
            self.config.save()
            messagebox.showinfo("OK", "✅ Calibration sauvegardée!")
            self.log("💾 Calibration sauvegardée")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    def save_zaaps(self):
        known = [n for n, v in self.zaap_vars.items() if v.get()]
        self.config.data["known_zaaps"] = known
        self.config.save()
        self.bot.pathfinder.known_zaaps = known
        messagebox.showinfo("OK", f"✅ {len(known)} zaaps sauvegardés!")
        self.log(f"💾 {len(known)} zaaps sauvegardés")


# ============================================================
#                    MAIN
# ============================================================

if __name__ == "__main__":
    if not HAS_DEPS:
        print("❌ Dépendances manquantes!")
        print("Lance Installer.bat")
        input("Entrée pour fermer...")
    else:
        app = TravelBotGUI()
        app.run()
