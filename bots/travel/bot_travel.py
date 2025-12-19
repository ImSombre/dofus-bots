"""
🗺️ Dofus Retro Travel Bot v1.0
Bot de déplacement intelligent avec pathfinding A* et Zaaps
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
    from PIL import ImageGrab
    import numpy as np
    import cv2
    HAS_DEPS = True
except ImportError:
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
        
        return {
            "click_positions": {
                "right": {"x": 95, "y": 50},   # % de l'écran
                "left": {"x": 5, "y": 50},
                "up": {"x": 50, "y": 5},
                "down": {"x": 50, "y": 95}
            },
            "move_delay": 1.5,
            "zaap_delay": 2.0,
            "pos_region": {"x1": 0, "y1": 0, "x2": 200, "y2": 50},
            "known_zaaps": [],
            "favorites": [],
            "resolution": "1920x1080"
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False


# ============================================================
#                    BASE DE DONNÉES DES MAPS
# ============================================================

class MapDatabase:
    """Base de données des maps et zaaps de Dofus Retro"""
    
    # Zaaps principaux de Dofus Retro avec leurs coordonnées
    ZAAPS = {
        "Astrub": (4, -19),
        "Astrub Centre": (5, -18),
        "Bonta": (-26, -36),
        "Brakmar": (-26, 35),
        "Amakna Village": (0, 0),
        "Amakna Château": (3, -5),
        "Sufokia": (13, 26),
        "Pandala": (26, -36),
        "Frigost Village": (-78, -41),
        "Incarnam": (0, 0),  # Zone de départ
        "Port Madrestam": (7, -4),
        "Taverne Astrub": (5, -16),
        "Bord de Forêt": (-1, 13),
        "Plaine des Scarafeuilles": (-1, 24),
        "Village des Dopeuls": (-34, -8),
        "Coin des Bouftous": (5, 7),
        "Tainéla": (1, -32),
        "Moon": (-56, 18),
    }
    
    # Zones importantes avec leurs coordonnées centrales
    ZONES = {
        "Astrub": {"center": (5, -18), "radius": 15},
        "Amakna": {"center": (0, 5), "radius": 20},
        "Bonta": {"center": (-28, -55), "radius": 15},
        "Brakmar": {"center": (-25, 40), "radius": 15},
        "Incarnam": {"center": (5, 2), "radius": 10},
        "Forêt Malefique": {"center": (-5, 10), "radius": 8},
        "Plaines Rocheuses": {"center": (10, 15), "radius": 10},
        "Sufokia": {"center": (15, 28), "radius": 12},
        "Frigost": {"center": (-78, -40), "radius": 20},
    }
    
    # Connexions spéciales (bateaux, passages secrets, etc.)
    SPECIAL_CONNECTIONS = {
        # (from_x, from_y): (to_x, to_y, type, cost)
        (7, -4): (13, 26, "bateau", 5),  # Port Madrestam -> Sufokia
        (13, 26): (7, -4, "bateau", 5),  # Sufokia -> Port Madrestam
    }
    
    @staticmethod
    def get_zaap_list():
        """Retourne la liste des zaaps"""
        return list(MapDatabase.ZAAPS.keys())
    
    @staticmethod
    def get_zaap_pos(name):
        """Retourne la position d'un zaap"""
        return MapDatabase.ZAAPS.get(name)
    
    @staticmethod
    def get_nearest_zaap(x, y):
        """Trouve le zaap le plus proche d'une position"""
        nearest = None
        min_dist = float('inf')
        
        for name, (zx, zy) in MapDatabase.ZAAPS.items():
            dist = abs(x - zx) + abs(y - zy)  # Distance Manhattan
            if dist < min_dist:
                min_dist = dist
                nearest = (name, zx, zy)
        
        return nearest


# ============================================================
#                    ALGORITHME A* PATHFINDING
# ============================================================

class Pathfinder:
    """Algorithme A* pour trouver le chemin optimal"""
    
    def __init__(self, use_zaaps=True, known_zaaps=None):
        self.use_zaaps = use_zaaps
        self.known_zaaps = known_zaaps or list(MapDatabase.ZAAPS.keys())
    
    def heuristic(self, a, b):
        """Heuristique: distance Manhattan"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def get_neighbors(self, pos):
        """Retourne les voisins d'une position (4 directions)"""
        x, y = pos
        neighbors = [
            ((x + 1, y), "right", 1),  # Droite
            ((x - 1, y), "left", 1),   # Gauche
            ((x, y - 1), "up", 1),     # Haut
            ((x, y + 1), "down", 1),   # Bas
        ]
        return neighbors
    
    def get_zaap_connections(self, pos):
        """Retourne les connexions zaap disponibles depuis une position"""
        connections = []
        
        if not self.use_zaaps:
            return connections
        
        # Vérifier si on est sur un zaap connu
        for zaap_name, zaap_pos in MapDatabase.ZAAPS.items():
            if pos == zaap_pos and zaap_name in self.known_zaaps:
                # On peut téléporter vers tous les autres zaaps connus
                for dest_name, dest_pos in MapDatabase.ZAAPS.items():
                    if dest_name != zaap_name and dest_name in self.known_zaaps:
                        # Coût du zaap = 1 (très avantageux)
                        connections.append((dest_pos, f"zaap:{dest_name}", 1))
        
        return connections
    
    def find_path(self, start, goal):
        """Trouve le chemin optimal avec A*"""
        
        # File de priorité: (f_score, counter, position, path)
        counter = 0
        open_set = [(0, counter, start, [])]
        heapq.heapify(open_set)
        
        # Positions déjà visitées
        closed_set = set()
        
        # Meilleur g_score pour chaque position
        g_scores = {start: 0}
        
        while open_set:
            f, _, current, path = heapq.heappop(open_set)
            
            # Arrivé à destination ?
            if current == goal:
                return path
            
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # Explorer les voisins (mouvements normaux)
            all_neighbors = self.get_neighbors(current)
            
            # Ajouter les connexions zaap
            all_neighbors.extend(self.get_zaap_connections(current))
            
            for neighbor_pos, move_type, cost in all_neighbors:
                if neighbor_pos in closed_set:
                    continue
                
                # Calculer le nouveau g_score
                tentative_g = g_scores.get(current, float('inf')) + cost
                
                if tentative_g < g_scores.get(neighbor_pos, float('inf')):
                    g_scores[neighbor_pos] = tentative_g
                    f_score = tentative_g + self.heuristic(neighbor_pos, goal)
                    
                    new_path = path + [(move_type, neighbor_pos)]
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor_pos, new_path))
        
        # Pas de chemin trouvé
        return None
    
    def find_path_with_zaap_optimization(self, start, goal):
        """Trouve le chemin optimal en considérant les zaaps"""
        
        # Chemin direct sans zaap
        direct_path = self.find_path(start, goal)
        direct_cost = len(direct_path) if direct_path else float('inf')
        
        best_path = direct_path
        best_cost = direct_cost
        
        if self.use_zaaps and self.known_zaaps:
            # Trouver le zaap le plus proche du départ
            for start_zaap_name in self.known_zaaps:
                start_zaap_pos = MapDatabase.ZAAPS.get(start_zaap_name)
                if not start_zaap_pos:
                    continue
                
                # Distance jusqu'au zaap de départ
                path_to_zaap = self.find_path_simple(start, start_zaap_pos)
                if path_to_zaap is None:
                    continue
                
                # Pour chaque zaap d'arrivée possible
                for end_zaap_name in self.known_zaaps:
                    if end_zaap_name == start_zaap_name:
                        continue
                    
                    end_zaap_pos = MapDatabase.ZAAPS.get(end_zaap_name)
                    if not end_zaap_pos:
                        continue
                    
                    # Distance depuis le zaap d'arrivée jusqu'à la destination
                    path_from_zaap = self.find_path_simple(end_zaap_pos, goal)
                    if path_from_zaap is None:
                        continue
                    
                    # Coût total: aller au zaap + téléportation (1) + aller à destination
                    total_cost = len(path_to_zaap) + 1 + len(path_from_zaap)
                    
                    if total_cost < best_cost:
                        best_cost = total_cost
                        # Construire le chemin complet
                        best_path = path_to_zaap + [(f"zaap:{end_zaap_name}", end_zaap_pos)] + path_from_zaap
        
        return best_path, best_cost
    
    def find_path_simple(self, start, goal):
        """Pathfinding simple sans zaaps (pour les sous-chemins)"""
        old_use_zaaps = self.use_zaaps
        self.use_zaaps = False
        path = self.find_path(start, goal)
        self.use_zaaps = old_use_zaaps
        return path


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
        
        self.current_pos = None
        self.target_pos = None
        self.current_path = []
        self.path_index = 0
        
        # Pathfinder avec les zaaps connus
        known_zaaps = config.data.get("known_zaaps", list(MapDatabase.ZAAPS.keys()))
        self.pathfinder = Pathfinder(use_zaaps=True, known_zaaps=known_zaaps)
        
        # Positions de clic (en pixels)
        self.screen_width = 1920
        self.screen_height = 1080
        
        # Charger la résolution
        res = config.data.get("resolution", "1920x1080")
        if "x" in res:
            parts = res.split("x")
            self.screen_width = int(parts[0])
            self.screen_height = int(parts[1])
    
    def set_current_position(self, x, y):
        """Définit la position actuelle"""
        self.current_pos = (x, y)
        self.log(f"📍 Position actuelle: [{x}, {y}]")
    
    def calculate_path(self, target_x, target_y):
        """Calcule le chemin optimal vers la destination"""
        if not self.current_pos:
            self.log("❌ Position actuelle non définie!")
            return None
        
        self.target_pos = (target_x, target_y)
        
        self.log(f"🗺️ Calcul du chemin: [{self.current_pos[0]}, {self.current_pos[1]}] → [{target_x}, {target_y}]")
        
        # Calculer avec optimisation zaap
        path, cost = self.pathfinder.find_path_with_zaap_optimization(
            self.current_pos, self.target_pos
        )
        
        if path:
            self.current_path = path
            self.path_index = 0
            
            # Compter les zaaps utilisés
            zaap_count = sum(1 for move, _ in path if move.startswith("zaap:"))
            normal_moves = len(path) - zaap_count
            
            self.log(f"✅ Chemin trouvé: {len(path)} étapes")
            self.log(f"   🚶 {normal_moves} déplacements + 🌀 {zaap_count} zaaps")
            
            return path
        else:
            self.log("❌ Aucun chemin trouvé!")
            return None
    
    def get_click_position(self, direction):
        """Retourne la position de clic pour une direction"""
        positions = self.config.data.get("click_positions", {})
        pos = positions.get(direction, {"x": 50, "y": 50})
        
        # Convertir % en pixels
        x = int(self.screen_width * pos["x"] / 100)
        y = int(self.screen_height * pos["y"] / 100)
        
        return x, y
    
    def execute_move(self, move_type, target_pos):
        """Exécute un mouvement"""
        
        if move_type.startswith("zaap:"):
            # Téléportation par zaap
            zaap_name = move_type.split(":")[1]
            self.log(f"🌀 Zaap vers {zaap_name}...")
            
            # TODO: Implémenter l'ouverture du menu zaap et sélection
            # Pour l'instant, on simule avec un délai
            time.sleep(self.config.data.get("zaap_delay", 2.0))
            
            self.current_pos = target_pos
            self.log(f"   ✅ Arrivé à {zaap_name} [{target_pos[0]}, {target_pos[1]}]")
            
        else:
            # Mouvement normal
            x, y = self.get_click_position(move_type)
            
            direction_names = {
                "right": "→ Droite",
                "left": "← Gauche", 
                "up": "↑ Haut",
                "down": "↓ Bas"
            }
            
            self.log(f"🚶 {direction_names.get(move_type, move_type)} → [{target_pos[0]}, {target_pos[1]}]")
            
            # Clic pour se déplacer
            pyautogui.click(x, y)
            
            # Attendre le chargement de la map
            time.sleep(self.config.data.get("move_delay", 1.5))
            
            self.current_pos = target_pos
    
    def start_travel(self):
        """Démarre le voyage"""
        if not self.current_path:
            self.log("❌ Aucun chemin défini!")
            return
        
        self.running = True
        self.paused = False
        self.path_index = 0
        
        threading.Thread(target=self._travel_loop, daemon=True).start()
    
    def _travel_loop(self):
        """Boucle principale de voyage"""
        self.log(f"🚀 Départ! {len(self.current_path)} étapes à parcourir")
        
        while self.running and self.path_index < len(self.current_path):
            if self.paused:
                time.sleep(0.1)
                continue
            
            move_type, target_pos = self.current_path[self.path_index]
            
            self.log(f"[{self.path_index + 1}/{len(self.current_path)}]")
            self.execute_move(move_type, target_pos)
            
            self.path_index += 1
        
        if self.path_index >= len(self.current_path):
            self.log(f"🎉 Arrivé à destination! [{self.target_pos[0]}, {self.target_pos[1]}]")
        
        self.running = False
    
    def stop(self):
        """Arrête le voyage"""
        self.running = False
        self.log("⏹️ Voyage arrêté")
    
    def pause(self):
        """Met en pause"""
        self.paused = not self.paused
        if self.paused:
            self.log("⏸️ Pause")
        else:
            self.log("▶️ Reprise")


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================

THEME = {
    'bg': '#1a1a2e',
    'bg2': '#16213e',
    'bg3': '#0f3460',
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
        self.root.title("🗺️ Dofus Travel Bot")
        self.root.geometry("700x750")
        self.root.configure(bg=THEME['bg'])
        self.root.resizable(True, True)
        
        # Centrer
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 700) // 2
        y = (self.root.winfo_screenheight() - 750) // 2
        self.root.geometry(f"700x750+{x}+{y}")
    
    def setup_hotkeys(self):
        """Configure les raccourcis clavier"""
        try:
            keyboard.add_hotkey('F5', self.start_travel)
            keyboard.add_hotkey('F6', self.pause_travel)
            keyboard.add_hotkey('F7', self.stop_travel)
        except:
            pass
    
    def create_widgets(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=THEME['bg2'], height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🗺️ DOFUS TRAVEL BOT", font=('Segoe UI', 20, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(pady=15)
        
        tk.Label(header, text="Déplacement intelligent avec Pathfinding A* + Zaaps",
                font=('Segoe UI', 10), bg=THEME['bg2'], fg=THEME['text2']).pack()
        
        # ===== MAIN CONTENT =====
        main = tk.Frame(self.root, bg=THEME['bg'])
        main.pack(fill='both', expand=True, padx=20, pady=15)
        
        # ----- Position Actuelle -----
        pos_frame = tk.LabelFrame(main, text="📍 Position Actuelle", font=('Segoe UI', 11, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        pos_frame.pack(fill='x', pady=5)
        
        pos_row = tk.Frame(pos_frame, bg=THEME['bg2'])
        pos_row.pack(fill='x')
        
        tk.Label(pos_row, text="X:", font=('Segoe UI', 11),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.current_x = tk.Entry(pos_row, width=8, font=('Segoe UI', 12),
                                  bg=THEME['bg3'], fg=THEME['text'],
                                  insertbackground=THEME['text'])
        self.current_x.pack(side='left', padx=5)
        self.current_x.insert(0, "5")
        
        tk.Label(pos_row, text="Y:", font=('Segoe UI', 11),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(20, 0))
        self.current_y = tk.Entry(pos_row, width=8, font=('Segoe UI', 12),
                                  bg=THEME['bg3'], fg=THEME['text'],
                                  insertbackground=THEME['text'])
        self.current_y.pack(side='left', padx=5)
        self.current_y.insert(0, "-18")
        
        tk.Button(pos_row, text="📍 Définir", font=('Segoe UI', 10),
                 bg=THEME['accent2'], fg='white',
                 command=self.set_current_position).pack(side='left', padx=20)
        
        # ----- Destination -----
        dest_frame = tk.LabelFrame(main, text="🎯 Destination", font=('Segoe UI', 11, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        dest_frame.pack(fill='x', pady=5)
        
        # Coordonnées manuelles
        dest_row = tk.Frame(dest_frame, bg=THEME['bg2'])
        dest_row.pack(fill='x')
        
        tk.Label(dest_row, text="X:", font=('Segoe UI', 11),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.dest_x = tk.Entry(dest_row, width=8, font=('Segoe UI', 12),
                               bg=THEME['bg3'], fg=THEME['text'],
                               insertbackground=THEME['text'])
        self.dest_x.pack(side='left', padx=5)
        
        tk.Label(dest_row, text="Y:", font=('Segoe UI', 11),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(20, 0))
        self.dest_y = tk.Entry(dest_row, width=8, font=('Segoe UI', 12),
                               bg=THEME['bg3'], fg=THEME['text'],
                               insertbackground=THEME['text'])
        self.dest_y.pack(side='left', padx=5)
        
        # Ou sélectionner un zaap
        tk.Label(dest_frame, text="─── OU ───", font=('Segoe UI', 9),
                bg=THEME['bg2'], fg=THEME['text2']).pack(pady=8)
        
        zaap_row = tk.Frame(dest_frame, bg=THEME['bg2'])
        zaap_row.pack(fill='x')
        
        tk.Label(zaap_row, text="🌀 Zaap:", font=('Segoe UI', 11),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        
        self.zaap_var = tk.StringVar()
        zaap_combo = ttk.Combobox(zaap_row, textvariable=self.zaap_var, width=25,
                                  values=MapDatabase.get_zaap_list(), state='readonly')
        zaap_combo.pack(side='left', padx=10)
        zaap_combo.bind('<<ComboboxSelected>>', self.on_zaap_selected)
        
        # ----- Options -----
        options_frame = tk.LabelFrame(main, text="⚙️ Options", font=('Segoe UI', 11, 'bold'),
                                      bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        options_frame.pack(fill='x', pady=5)
        
        self.use_zaaps_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="🌀 Utiliser les Zaaps (chemin plus rapide)",
                      variable=self.use_zaaps_var, font=('Segoe UI', 10),
                      bg=THEME['bg2'], fg=THEME['text'], selectcolor=THEME['bg3'],
                      activebackground=THEME['bg2']).pack(anchor='w')
        
        # Délai de déplacement
        delay_row = tk.Frame(options_frame, bg=THEME['bg2'])
        delay_row.pack(fill='x', pady=5)
        
        tk.Label(delay_row, text="Délai entre déplacements:", font=('Segoe UI', 10),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        
        self.delay_var = tk.StringVar(value=str(self.config.data.get("move_delay", 1.5)))
        delay_spin = tk.Spinbox(delay_row, from_=0.5, to=5.0, increment=0.5, width=5,
                               textvariable=self.delay_var, font=('Segoe UI', 10))
        delay_spin.pack(side='left', padx=10)
        tk.Label(delay_row, text="sec", font=('Segoe UI', 10),
                bg=THEME['bg2'], fg=THEME['text2']).pack(side='left')
        
        # ----- Boutons d'action -----
        action_frame = tk.Frame(main, bg=THEME['bg'])
        action_frame.pack(fill='x', pady=15)
        
        tk.Button(action_frame, text="🔍 CALCULER LE CHEMIN", font=('Segoe UI', 12, 'bold'),
                 bg=THEME['accent2'], fg='white', width=25,
                 command=self.calculate_path).pack(pady=5)
        
        btn_row = tk.Frame(action_frame, bg=THEME['bg'])
        btn_row.pack(pady=5)
        
        self.start_btn = tk.Button(btn_row, text="▶️ PARTIR (F5)", font=('Segoe UI', 11, 'bold'),
                                   bg=THEME['success'], fg='white', width=15,
                                   command=self.start_travel)
        self.start_btn.pack(side='left', padx=5)
        
        tk.Button(btn_row, text="⏸️ Pause (F6)", font=('Segoe UI', 10),
                 bg=THEME['warning'], fg='white', width=12,
                 command=self.pause_travel).pack(side='left', padx=5)
        
        tk.Button(btn_row, text="⏹️ Stop (F7)", font=('Segoe UI', 10),
                 bg=THEME['accent'], fg='white', width=12,
                 command=self.stop_travel).pack(side='left', padx=5)
        
        # ----- Aperçu du chemin -----
        path_frame = tk.LabelFrame(main, text="📋 Chemin calculé", font=('Segoe UI', 11, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=10)
        path_frame.pack(fill='both', expand=True, pady=5)
        
        self.path_text = tk.Text(path_frame, height=6, font=('Consolas', 9),
                                 bg=THEME['bg3'], fg=THEME['text'],
                                 insertbackground=THEME['text'])
        self.path_text.pack(fill='both', expand=True)
        
        # ----- Log -----
        log_frame = tk.LabelFrame(main, text="📜 Log", font=('Segoe UI', 11, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=10)
        log_frame.pack(fill='both', expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, font=('Consolas', 9),
                                bg=THEME['bg3'], fg=THEME['text'],
                                insertbackground=THEME['text'])
        self.log_text.pack(fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
        # ----- Status Bar -----
        status = tk.Frame(self.root, bg=THEME['bg2'], height=30)
        status.pack(fill='x', side='bottom')
        
        self.status_label = tk.Label(status, text="Prêt", font=('Segoe UI', 9),
                                     bg=THEME['bg2'], fg=THEME['text2'])
        self.status_label.pack(side='left', padx=10, pady=5)
        
        # Log initial
        self.log("🗺️ Travel Bot prêt!")
        self.log("💡 Entre ta position actuelle et ta destination")
    
    def log(self, message):
        """Ajoute un message au log"""
        timestamp = time.strftime("%H:%M:%S")
        
        def update():
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
        
        self.root.after(0, update)
    
    def set_current_position(self):
        """Définit la position actuelle"""
        try:
            x = int(self.current_x.get())
            y = int(self.current_y.get())
            self.bot.set_current_position(x, y)
            self.status_label.config(text=f"Position: [{x}, {y}]")
        except ValueError:
            messagebox.showerror("Erreur", "Coordonnées invalides!")
    
    def on_zaap_selected(self, event):
        """Quand un zaap est sélectionné"""
        zaap_name = self.zaap_var.get()
        pos = MapDatabase.get_zaap_pos(zaap_name)
        if pos:
            self.dest_x.delete(0, 'end')
            self.dest_x.insert(0, str(pos[0]))
            self.dest_y.delete(0, 'end')
            self.dest_y.insert(0, str(pos[1]))
            self.log(f"🌀 Destination: {zaap_name} [{pos[0]}, {pos[1]}]")
    
    def calculate_path(self):
        """Calcule le chemin"""
        # Vérifier position actuelle
        try:
            cx = int(self.current_x.get())
            cy = int(self.current_y.get())
        except:
            messagebox.showerror("Erreur", "Position actuelle invalide!")
            return
        
        # Vérifier destination
        try:
            dx = int(self.dest_x.get())
            dy = int(self.dest_y.get())
        except:
            messagebox.showerror("Erreur", "Destination invalide!")
            return
        
        # Configurer le pathfinder
        self.bot.pathfinder.use_zaaps = self.use_zaaps_var.get()
        
        # Mettre à jour le délai
        try:
            self.config.data["move_delay"] = float(self.delay_var.get())
            self.config.save()
        except:
            pass
        
        # Définir position et calculer
        self.bot.set_current_position(cx, cy)
        path = self.bot.calculate_path(dx, dy)
        
        # Afficher le chemin
        self.path_text.delete('1.0', 'end')
        
        if path:
            self.path_text.insert('end', f"🚀 Départ: [{cx}, {cy}]\n")
            self.path_text.insert('end', f"🎯 Arrivée: [{dx}, {dy}]\n")
            self.path_text.insert('end', f"📏 {len(path)} étapes\n\n")
            
            for i, (move, pos) in enumerate(path):
                if move.startswith("zaap:"):
                    zaap_name = move.split(":")[1]
                    self.path_text.insert('end', f"{i+1}. 🌀 ZAAP → {zaap_name} [{pos[0]}, {pos[1]}]\n")
                else:
                    arrows = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
                    self.path_text.insert('end', f"{i+1}. {arrows.get(move, '?')} [{pos[0]}, {pos[1]}]\n")
            
            self.status_label.config(text=f"Chemin: {len(path)} étapes")
        else:
            self.path_text.insert('end', "❌ Aucun chemin trouvé!")
    
    def start_travel(self):
        """Démarre le voyage"""
        if not self.bot.current_path:
            self.calculate_path()
        
        if self.bot.current_path:
            self.bot.start_travel()
            self.status_label.config(text="🚀 En route...")
    
    def pause_travel(self):
        """Pause"""
        self.bot.pause()
        if self.bot.paused:
            self.status_label.config(text="⏸️ Pause")
        else:
            self.status_label.config(text="🚀 En route...")
    
    def stop_travel(self):
        """Stop"""
        self.bot.stop()
        self.status_label.config(text="⏹️ Arrêté")


# ============================================================
#                    MAIN
# ============================================================

if __name__ == "__main__":
    if not HAS_DEPS:
        print("❌ Dépendances manquantes!")
        print("Lance Installer.bat pour les installer.")
        input("Appuie sur Entrée pour fermer...")
    else:
        app = TravelBotGUI()
        app.run()
