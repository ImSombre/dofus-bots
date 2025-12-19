"""
🗺️ Dofus Retro Travel Bot v2.0
Bot de déplacement automatique intelligent
- Pathfinding A* avec évitement d'obstacles
- Utilisation des Zaaps
- Calibration des clics
- Déplacement automatique
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import time
import threading
import heapq
import math
import re

try:
    import pyautogui
    import keyboard
    from PIL import ImageGrab, Image
    import numpy as np
    import cv2
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
            # Positions de clic pour changer de map (en pixels)
            # À calibrer selon ta résolution
            "click_positions": {
                "right": {"x": 1890, "y": 540},
                "left": {"x": 30, "y": 540},
                "up": {"x": 960, "y": 30},
                "down": {"x": 960, "y": 1050}
            },
            # Délais
            "move_delay": 1.0,
            "zaap_delay": 2.0,
            "retry_delay": 0.5,
            # Options
            "max_retries": 3,
            "use_zaaps": True,
            "resolution": "1920x1080",
            # Zaaps connus par le personnage
            "known_zaaps": [
                "Astrub", "Astrub Centre", "Amakna Village"
            ],
            # Favoris
            "favorites": []
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False


# ============================================================
#                    BASE DE DONNÉES DU MONDE
# ============================================================

class WorldMap:
    """
    Base de données du monde de Dofus Retro
    Le monde est une grille - on peut aller dans 4 directions
    Certaines zones sont bloquées (eau, murs, etc.)
    """
    
    # ===== ZAAPS =====
    ZAAPS = {
        # Astrub
        "Astrub": (4, -19),
        "Astrub Centre": (5, -18),
        "Taverne Astrub": (5, -16),
        
        # Amakna
        "Amakna Village": (0, 0),
        "Amakna Château": (3, -5),
        "Port Madrestam": (7, -4),
        "Coin des Bouftous": (5, 7),
        "Bord de Forêt": (-1, 13),
        "Plaine des Scarafeuilles": (-1, 24),
        
        # Cités
        "Bonta": (-26, -36),
        "Brakmar": (-26, 35),
        
        # Autres
        "Sufokia": (13, 26),
        "Pandala": (26, -36),
        "Frigost Village": (-78, -41),
        "Village des Dopeuls": (-34, -8),
        "Tainéla": (1, -32),
        "Moon": (-56, 18),
    }
    
    # ===== ZONES BLOQUÉES (rectangles) =====
    BLOCKED_ZONES = [
        # Lac d'Amakna
        {"x_min": -5, "x_max": -2, "y_min": 3, "y_max": 8},
        # Zone d'eau au sud
        {"x_min": -20, "x_max": 30, "y_min": 28, "y_max": 35},
    ]
    
    # ===== MAPS INDIVIDUELLES BLOQUÉES =====
    BLOCKED_MAPS = set([
        # Ajoute ici les maps spécifiques bloquées
        # (-1, 5), (-2, 5), etc.
    ])
    
    # ===== DIRECTIONS BLOQUÉES PAR MAP =====
    # Format: (x, y): ["direction1", "direction2"]
    BLOCKED_DIRECTIONS = {
        # Exemple: certaines maps n'ont pas de sortie
        # (5, -18): ["up"],
    }
    
    @classmethod
    def is_blocked(cls, x, y):
        """Vérifie si une map est bloquée"""
        # Map individuelle
        if (x, y) in cls.BLOCKED_MAPS:
            return True
        
        # Zones rectangulaires
        for zone in cls.BLOCKED_ZONES:
            if (zone["x_min"] <= x <= zone["x_max"] and 
                zone["y_min"] <= y <= zone["y_max"]):
                return True
        
        return False
    
    @classmethod
    def can_move(cls, from_x, from_y, direction):
        """Vérifie si on peut aller dans une direction"""
        # Direction bloquée depuis cette map ?
        blocked = cls.BLOCKED_DIRECTIONS.get((from_x, from_y), [])
        if direction in blocked:
            return False
        
        # Calculer la destination
        dest = {
            "right": (from_x + 1, from_y),
            "left": (from_x - 1, from_y),
            "up": (from_x, from_y - 1),
            "down": (from_x, from_y + 1),
        }.get(direction)
        
        if not dest:
            return False
        
        # Destination bloquée ?
        return not cls.is_blocked(dest[0], dest[1])
    
    @classmethod
    def get_neighbors(cls, x, y):
        """Retourne les voisins accessibles"""
        neighbors = []
        
        directions = [
            ("right", x + 1, y),
            ("left", x - 1, y),
            ("up", x, y - 1),
            ("down", x, y + 1),
        ]
        
        for direction, nx, ny in directions:
            if cls.can_move(x, y, direction):
                neighbors.append((direction, nx, ny, 1))
        
        return neighbors
    
    @classmethod
    def get_zaap_list(cls):
        return list(cls.ZAAPS.keys())
    
    @classmethod
    def get_zaap_pos(cls, name):
        return cls.ZAAPS.get(name)


# ============================================================
#                    PATHFINDING A*
# ============================================================

class Pathfinder:
    """Algorithme A* pour trouver le chemin optimal"""
    
    def __init__(self, use_zaaps=True, known_zaaps=None):
        self.use_zaaps = use_zaaps
        self.known_zaaps = known_zaaps or []
    
    def heuristic(self, a, b):
        """Distance Manhattan"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def find_path(self, start, goal, max_iterations=50000):
        """Trouve le chemin optimal avec A*"""
        
        if start == goal:
            return []
        
        counter = 0
        open_set = [(0, counter, start, [])]
        heapq.heapify(open_set)
        
        closed_set = set()
        g_scores = {start: 0}
        
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            f, _, current, path = heapq.heappop(open_set)
            
            if current == goal:
                return path
            
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # Voisins normaux (marche)
            for direction, nx, ny, cost in WorldMap.get_neighbors(current[0], current[1]):
                neighbor = (nx, ny)
                
                if neighbor in closed_set:
                    continue
                
                tentative_g = g_scores.get(current, float('inf')) + cost
                
                if tentative_g < g_scores.get(neighbor, float('inf')):
                    g_scores[neighbor] = tentative_g
                    f_score = tentative_g + self.heuristic(neighbor, goal)
                    
                    new_path = path + [(direction, neighbor)]
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor, new_path))
            
            # Connexions zaap
            if self.use_zaaps and self.known_zaaps:
                for zaap_name, zaap_pos in WorldMap.ZAAPS.items():
                    if current == zaap_pos and zaap_name in self.known_zaaps:
                        for dest_name, dest_pos in WorldMap.ZAAPS.items():
                            if dest_name != zaap_name and dest_name in self.known_zaaps:
                                if dest_pos in closed_set:
                                    continue
                                
                                # Coût zaap = 2
                                tentative_g = g_scores.get(current, float('inf')) + 2
                                
                                if tentative_g < g_scores.get(dest_pos, float('inf')):
                                    g_scores[dest_pos] = tentative_g
                                    f_score = tentative_g + self.heuristic(dest_pos, goal)
                                    
                                    new_path = path + [(f"zaap:{dest_name}", dest_pos)]
                                    counter += 1
                                    heapq.heappush(open_set, (f_score, counter, dest_pos, new_path))
        
        return None
    
    def find_optimal_path(self, start, goal):
        """Compare chemin direct vs avec zaaps"""
        
        # Direct
        old_zaaps = self.use_zaaps
        self.use_zaaps = False
        direct_path = self.find_path(start, goal)
        direct_cost = len(direct_path) if direct_path else float('inf')
        
        # Avec zaaps
        self.use_zaaps = True
        zaap_path = self.find_path(start, goal)
        zaap_cost = len(zaap_path) if zaap_path else float('inf')
        
        self.use_zaaps = old_zaaps
        
        if zaap_cost < direct_cost:
            return zaap_path, zaap_cost, True
        else:
            return direct_path, direct_cost, False


# ============================================================
#                    BOT DE DÉPLACEMENT
# ============================================================

class TravelBot:
    """Bot de déplacement automatique"""
    
    def __init__(self, config, log_callback=None):
        self.config = config
        self.log = log_callback or print
        
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
        
        # Stats
        self.moves_done = 0
        self.zaaps_used = 0
    
    def set_current_position(self, x, y):
        """Définit la position actuelle"""
        self.current_pos = (x, y)
        self.log(f"📍 Position: [{x}, {y}]")
    
    def calculate_path(self, target_x, target_y):
        """Calcule le chemin optimal"""
        if not self.current_pos:
            self.log("❌ Position actuelle non définie!")
            return None
        
        self.target_pos = (target_x, target_y)
        
        self.log(f"🗺️ Calcul: [{self.current_pos[0]}, {self.current_pos[1]}] → [{target_x}, {target_y}]")
        
        # Mettre à jour les zaaps connus
        self.pathfinder.known_zaaps = self.config.data.get("known_zaaps", [])
        self.pathfinder.use_zaaps = self.config.data.get("use_zaaps", True)
        
        # Calculer
        path, cost, used_zaaps = self.pathfinder.find_optimal_path(self.current_pos, self.target_pos)
        
        if path:
            self.current_path = path
            self.path_index = 0
            
            zaap_count = sum(1 for move, _ in path if str(move).startswith("zaap:"))
            walk_count = len(path) - zaap_count
            
            self.log(f"✅ Chemin trouvé: {len(path)} étapes")
            self.log(f"   🚶 {walk_count} déplacements, 🌀 {zaap_count} zaap(s)")
            
            return path
        else:
            self.log("❌ Aucun chemin trouvé!")
            return None
    
    def click_direction(self, direction):
        """Clique pour changer de map"""
        positions = self.config.data.get("click_positions", {})
        
        if direction not in positions:
            self.log(f"⚠️ Direction '{direction}' non calibrée!")
            return False
        
        pos = positions[direction]
        x, y = pos["x"], pos["y"]
        
        pyautogui.click(x, y)
        return True
    
    def execute_move(self, move_type, target_pos):
        """Exécute un mouvement"""
        
        if str(move_type).startswith("zaap:"):
            # === ZAAP ===
            zaap_name = move_type.split(":")[1]
            self.log(f"🌀 ZAAP → {zaap_name}")
            self.log(f"   ⚠️ Utilise le zaap manuellement!")
            self.log(f"   ⏳ Attente {self.config.data.get('zaap_delay', 2.0)}s...")
            
            # Pause pour laisser le temps d'utiliser le zaap
            time.sleep(self.config.data.get("zaap_delay", 2.0))
            
            self.current_pos = target_pos
            self.zaaps_used += 1
            return True
            
        else:
            # === MARCHE ===
            icons = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            icon = icons.get(move_type, "?")
            
            self.log(f"🚶 {icon} [{target_pos[0]}, {target_pos[1]}]")
            
            # Clic
            success = self.click_direction(move_type)
            
            if success:
                time.sleep(self.config.data.get("move_delay", 1.0))
                self.current_pos = target_pos
                self.moves_done += 1
                return True
            else:
                return False
    
    def start_travel(self):
        """Démarre le voyage"""
        if not self.current_path:
            self.log("❌ Aucun chemin!")
            return
        
        if self.running:
            self.log("⚠️ Déjà en cours...")
            return
        
        self.running = True
        self.paused = False
        self.stop_requested = False
        self.path_index = 0
        self.moves_done = 0
        self.zaaps_used = 0
        
        threading.Thread(target=self._travel_loop, daemon=True).start()
    
    def _travel_loop(self):
        """Boucle principale"""
        total = len(self.current_path)
        self.log(f"🚀 C'est parti! {total} étapes")
        self.log(f"   F6=Pause, F7=Stop")
        
        while self.running and self.path_index < len(self.current_path):
            if self.stop_requested:
                break
            
            while self.paused and self.running and not self.stop_requested:
                time.sleep(0.1)
            
            if self.stop_requested:
                break
            
            move_type, target_pos = self.current_path[self.path_index]
            
            self.log(f"[{self.path_index + 1}/{total}]")
            
            success = self.execute_move(move_type, target_pos)
            
            if success:
                self.path_index += 1
            else:
                self.log("⚠️ Échec, réessai...")
                time.sleep(0.5)
        
        if self.path_index >= len(self.current_path) and not self.stop_requested:
            self.log(f"🎉 ARRIVÉ! [{self.target_pos[0]}, {self.target_pos[1]}]")
            self.log(f"   📊 {self.moves_done} maps, {self.zaaps_used} zaaps")
        
        self.running = False
    
    def pause(self):
        self.paused = not self.paused
        self.log("⏸️ Pause" if self.paused else "▶️ Reprise")
    
    def stop(self):
        self.stop_requested = True
        self.running = False
        self.log("⏹️ Arrêt")


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================

THEME = {
    'bg': '#1a1a2e',
    'bg2': '#16213e',
    'bg3': '#0f3460',
    'card': '#1f4068',
    'accent': '#e94560',
    'accent2': '#4cc9f0',
    'success': '#00d26a',
    'warning': '#ff9f1c',
    'text': '#ffffff',
    'text2': '#8b8b9e'
}


class TravelBotGUI:
    def __init__(self):
        self.config = Config()
        self.bot = TravelBot(self.config, self.log)
        
        self.setup_window()
        self.create_widgets()
        self.setup_hotkeys()
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🗺️ Dofus Travel Bot v2.0")
        self.root.geometry("700x800")
        self.root.configure(bg=THEME['bg'])
        
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 700) // 2
        y = (self.root.winfo_screenheight() - 800) // 2
        self.root.geometry(f"700x800+{x}+{y}")
    
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('F5', self.start_travel)
            keyboard.add_hotkey('F6', self.pause_travel)
            keyboard.add_hotkey('F7', self.stop_travel)
        except:
            pass
    
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=THEME['bg2'], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🗺️ DOFUS TRAVEL BOT v2.0", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(pady=12)
        
        # Notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.create_navigation_tab(notebook)
        self.create_calibration_tab(notebook)
        self.create_zaaps_tab(notebook)
        
        # Status
        status = tk.Frame(self.root, bg=THEME['bg2'], height=25)
        status.pack(fill='x', side='bottom')
        self.status_label = tk.Label(status, text="F5=Go • F6=Pause • F7=Stop",
                                     font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2'])
        self.status_label.pack(pady=3)
    
    def create_navigation_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🗺️ Navigation")
        
        # Position actuelle
        pos_frame = tk.LabelFrame(tab, text="📍 Position Actuelle", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=8)
        pos_frame.pack(fill='x', padx=10, pady=5)
        
        pos_row = tk.Frame(pos_frame, bg=THEME['bg2'])
        pos_row.pack(fill='x')
        
        tk.Label(pos_row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.current_x = tk.Entry(pos_row, width=7, font=('Segoe UI', 11), bg=THEME['bg3'], fg=THEME['text'])
        self.current_x.pack(side='left', padx=5)
        self.current_x.insert(0, "5")
        
        tk.Label(pos_row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.current_y = tk.Entry(pos_row, width=7, font=('Segoe UI', 11), bg=THEME['bg3'], fg=THEME['text'])
        self.current_y.pack(side='left', padx=5)
        self.current_y.insert(0, "-18")
        
        tk.Button(pos_row, text="📍 Définir", bg=THEME['accent2'], fg='white',
                 command=self.set_position).pack(side='left', padx=15)
        
        # Destination
        dest_frame = tk.LabelFrame(tab, text="🎯 Destination", font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=8)
        dest_frame.pack(fill='x', padx=10, pady=5)
        
        dest_row = tk.Frame(dest_frame, bg=THEME['bg2'])
        dest_row.pack(fill='x')
        
        tk.Label(dest_row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.dest_x = tk.Entry(dest_row, width=7, font=('Segoe UI', 11), bg=THEME['bg3'], fg=THEME['text'])
        self.dest_x.pack(side='left', padx=5)
        
        tk.Label(dest_row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.dest_y = tk.Entry(dest_row, width=7, font=('Segoe UI', 11), bg=THEME['bg3'], fg=THEME['text'])
        self.dest_y.pack(side='left', padx=5)
        
        tk.Label(dest_frame, text="─── OU choisir un Zaap ───", font=('Segoe UI', 9),
                bg=THEME['bg2'], fg=THEME['text2']).pack(pady=5)
        
        self.zaap_var = tk.StringVar()
        zaap_combo = ttk.Combobox(dest_frame, textvariable=self.zaap_var, width=30,
                                  values=WorldMap.get_zaap_list(), state='readonly')
        zaap_combo.pack()
        zaap_combo.bind('<<ComboboxSelected>>', self.on_zaap_selected)
        
        # Options
        opt_frame = tk.LabelFrame(tab, text="⚙️ Options", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=8)
        opt_frame.pack(fill='x', padx=10, pady=5)
        
        self.use_zaaps_var = tk.BooleanVar(value=self.config.data.get("use_zaaps", True))
        tk.Checkbutton(opt_frame, text="🌀 Utiliser les Zaaps", variable=self.use_zaaps_var,
                      bg=THEME['bg2'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(anchor='w')
        
        delay_row = tk.Frame(opt_frame, bg=THEME['bg2'])
        delay_row.pack(fill='x', pady=5)
        tk.Label(delay_row, text="Délai par map:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.delay_var = tk.StringVar(value=str(self.config.data.get("move_delay", 1.0)))
        tk.Spinbox(delay_row, from_=0.3, to=5.0, increment=0.1, width=5,
                  textvariable=self.delay_var).pack(side='left', padx=10)
        tk.Label(delay_row, text="sec", bg=THEME['bg2'], fg=THEME['text2']).pack(side='left')
        
        # Boutons
        btn_frame = tk.Frame(tab, bg=THEME['bg'])
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(btn_frame, text="🔍 CALCULER LE CHEMIN", font=('Segoe UI', 11, 'bold'),
                 bg=THEME['accent2'], fg='white', width=25,
                 command=self.calculate_path).pack(pady=5)
        
        btn_row = tk.Frame(btn_frame, bg=THEME['bg'])
        btn_row.pack()
        
        tk.Button(btn_row, text="▶️ GO (F5)", font=('Segoe UI', 10, 'bold'),
                 bg=THEME['success'], fg='white', width=12,
                 command=self.start_travel).pack(side='left', padx=3)
        tk.Button(btn_row, text="⏸️ Pause (F6)", font=('Segoe UI', 9),
                 bg=THEME['warning'], fg='white', width=11,
                 command=self.pause_travel).pack(side='left', padx=3)
        tk.Button(btn_row, text="⏹️ Stop (F7)", font=('Segoe UI', 9),
                 bg=THEME['accent'], fg='white', width=11,
                 command=self.stop_travel).pack(side='left', padx=3)
        
        # Chemin
        path_frame = tk.LabelFrame(tab, text="📋 Chemin", font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        path_frame.pack(fill='x', padx=10, pady=5)
        
        self.path_text = tk.Text(path_frame, height=5, font=('Consolas', 9),
                                 bg=THEME['bg3'], fg=THEME['text'])
        self.path_text.pack(fill='x')
        
        # Log
        log_frame = tk.LabelFrame(tab, text="📜 Log", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, font=('Consolas', 9),
                                bg=THEME['bg3'], fg=THEME['text'])
        self.log_text.pack(fill='both', expand=True)
        
        self.log("🗺️ Travel Bot prêt!")
        self.log("💡 1. Entre ta position actuelle")
        self.log("💡 2. Entre ta destination ou choisis un zaap")
        self.log("💡 3. Clique sur CALCULER puis GO!")
    
    def create_calibration_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🎯 Calibration")
        
        tk.Label(tab, text="🎯 Calibration des Clics", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        tk.Label(tab, text="Configure où cliquer pour changer de map.\n"
                          "Clique sur 'Calibrer' puis clique sur le bord de l'écran Dofus.",
                font=('Segoe UI', 10), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        # Directions
        dir_frame = tk.Frame(tab, bg=THEME['bg'])
        dir_frame.pack(pady=20)
        
        self.pos_labels = {}
        
        directions = [("up", "↑ Haut", 1, 0), ("left", "← Gauche", 0, 1),
                      ("right", "→ Droite", 2, 1), ("down", "↓ Bas", 1, 2)]
        
        for direction, label, col, row in directions:
            frame = tk.Frame(dir_frame, bg=THEME['card'], padx=15, pady=10)
            frame.grid(row=row, column=col, padx=5, pady=5)
            
            tk.Label(frame, text=label, font=('Segoe UI', 11, 'bold'),
                    bg=THEME['card'], fg=THEME['text']).pack()
            
            pos = self.config.data.get("click_positions", {}).get(direction, {"x": 0, "y": 0})
            self.pos_labels[direction] = tk.Label(frame, text=f"X:{pos['x']} Y:{pos['y']}",
                                                   font=('Consolas', 9), bg=THEME['card'], fg=THEME['accent2'])
            self.pos_labels[direction].pack(pady=5)
            
            tk.Button(frame, text="🎯 Calibrer", bg=THEME['accent2'], fg='white',
                     command=lambda d=direction: self.calibrate_direction(d)).pack()
        
        tk.Button(tab, text="💾 Sauvegarder", font=('Segoe UI', 10),
                 bg=THEME['success'], fg='white', command=self.save_calibration).pack(pady=20)
    
    def create_zaaps_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🌀 Zaaps")
        
        tk.Label(tab, text="🌀 Zaaps Connus", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        tk.Label(tab, text="Coche les zaaps que ton personnage connaît.",
                font=('Segoe UI', 10), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        # Canvas scrollable
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
        
        for zaap_name, (x, y) in sorted(WorldMap.ZAAPS.items()):
            var = tk.BooleanVar(value=(zaap_name in known))
            self.zaap_vars[zaap_name] = var
            
            frame = tk.Frame(scroll_frame, bg=THEME['bg2'])
            frame.pack(fill='x', padx=10, pady=2)
            
            tk.Checkbutton(frame, text=zaap_name, variable=var, bg=THEME['bg2'],
                          fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left')
            tk.Label(frame, text=f"[{x}, {y}]", font=('Consolas', 9),
                    bg=THEME['bg2'], fg=THEME['text2']).pack(side='right')
        
        btn_frame = tk.Frame(tab, bg=THEME['bg'])
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="✅ Tout", bg=THEME['card'], fg=THEME['text'],
                 command=self.select_all_zaaps).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Rien", bg=THEME['card'], fg=THEME['text'],
                 command=self.deselect_all_zaaps).pack(side='left', padx=5)
        tk.Button(btn_frame, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 command=self.save_zaaps).pack(side='left', padx=10)
    
    # ===== MÉTHODES =====
    
    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self._log(f"[{timestamp}] {msg}"))
    
    def _log(self, msg):
        self.log_text.insert('end', msg + "\n")
        self.log_text.see('end')
    
    def set_position(self):
        try:
            x, y = int(self.current_x.get()), int(self.current_y.get())
            self.bot.set_current_position(x, y)
            self.status_label.config(text=f"Position: [{x}, {y}]")
        except:
            messagebox.showerror("Erreur", "Coordonnées invalides!")
    
    def on_zaap_selected(self, event):
        zaap_name = self.zaap_var.get()
        pos = WorldMap.get_zaap_pos(zaap_name)
        if pos:
            self.dest_x.delete(0, 'end')
            self.dest_x.insert(0, str(pos[0]))
            self.dest_y.delete(0, 'end')
            self.dest_y.insert(0, str(pos[1]))
            self.log(f"🎯 Destination: {zaap_name} [{pos[0]}, {pos[1]}]")
    
    def calculate_path(self):
        try:
            cx, cy = int(self.current_x.get()), int(self.current_y.get())
            dx, dy = int(self.dest_x.get()), int(self.dest_y.get())
        except:
            messagebox.showerror("Erreur", "Coordonnées invalides!")
            return
        
        self.config.data["use_zaaps"] = self.use_zaaps_var.get()
        try:
            self.config.data["move_delay"] = float(self.delay_var.get())
        except:
            pass
        self.config.save()
        
        self.bot.pathfinder.use_zaaps = self.use_zaaps_var.get()
        self.bot.set_current_position(cx, cy)
        path = self.bot.calculate_path(dx, dy)
        
        self.path_text.delete('1.0', 'end')
        
        if path:
            self.path_text.insert('end', f"[{cx},{cy}] → [{dx},{dy}] • {len(path)} étapes\n\n")
            arrows = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            
            for i, (move, pos) in enumerate(path):
                if str(move).startswith("zaap:"):
                    self.path_text.insert('end', f"{i+1}. 🌀 {move.split(':')[1]}\n")
                else:
                    self.path_text.insert('end', f"{i+1}. {arrows.get(move,'?')} [{pos[0]},{pos[1]}]\n")
        else:
            self.path_text.insert('end', "❌ Aucun chemin trouvé!")
    
    def start_travel(self):
        if not self.bot.current_path:
            self.calculate_path()
        if self.bot.current_path:
            self.bot.start_travel()
            self.status_label.config(text="🚀 En route...")
    
    def pause_travel(self):
        self.bot.pause()
        self.status_label.config(text="⏸️ Pause" if self.bot.paused else "🚀 En route...")
    
    def stop_travel(self):
        self.bot.stop()
        self.status_label.config(text="⏹️ Arrêté")
    
    def calibrate_direction(self, direction):
        messagebox.showinfo("Calibration", f"Clique OK puis clique sur le bord '{direction}' dans 3 secondes")
        
        def do_cal():
            self.log(f"🎯 Calibration {direction}...")
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            
            x, y = pyautogui.position()
            self.config.data.setdefault("click_positions", {})[direction] = {"x": x, "y": y}
            self.log(f"✅ {direction}: X={x}, Y={y}")
            self.root.after(0, lambda: self.pos_labels[direction].config(text=f"X:{x} Y:{y}"))
        
        threading.Thread(target=do_cal, daemon=True).start()
    
    def save_calibration(self):
        self.config.save()
        messagebox.showinfo("OK", "Calibration sauvegardée!")
    
    def select_all_zaaps(self):
        for var in self.zaap_vars.values():
            var.set(True)
    
    def deselect_all_zaaps(self):
        for var in self.zaap_vars.values():
            var.set(False)
    
    def save_zaaps(self):
        known = [n for n, v in self.zaap_vars.items() if v.get()]
        self.config.data["known_zaaps"] = known
        self.config.save()
        self.bot.pathfinder.known_zaaps = known
        messagebox.showinfo("OK", f"{len(known)} zaaps sauvegardés!")


# ============================================================
#                    MAIN
# ============================================================

if __name__ == "__main__":
    if not HAS_DEPS:
        print("❌ Dépendances manquantes! Lance Installer.bat")
        input("Entrée pour fermer...")
    else:
        app = TravelBotGUI()
        app.run()
