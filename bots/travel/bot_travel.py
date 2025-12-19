"""
🗺️ Dofus Retro Travel Bot v3.0
Bot de déplacement 100% AUTOMATIQUE
- Lecture des coordonnées à l'écran (OCR)
- Utilisation automatique des Zaaps
- Pathfinding A* intelligent
- Déplacement automatique
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import time
import threading
import heapq
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

# OCR
try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


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
            # Zone des coordonnées à l'écran (à calibrer)
            "coords_region": {
                "x": 230,
                "y": 40,
                "width": 250,
                "height": 60
            },
            # Positions de clic pour changer de map
            "click_positions": {
                "right": {"x": 1250, "y": 400},
                "left": {"x": 240, "y": 400},
                "up": {"x": 750, "y": 50},
                "down": {"x": 750, "y": 620}
            },
            # Position du zaap sur la map (à calibrer)
            "zaap_click": {"x": 600, "y": 400},
            # Bouton pour utiliser le zaap
            "zaap_use_button": {"x": 750, "y": 550},
            # Délais
            "move_delay": 1.5,
            "zaap_delay": 2.5,
            "ocr_delay": 0.5,
            # Zaaps connus
            "known_zaaps": ["Astrub", "Amakna Village"],
            # Options
            "use_zaaps": True,
            "auto_detect_position": True
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
    """Base de données des maps et zaaps de Dofus Retro"""
    
    # Zaaps avec leurs coordonnées
    ZAAPS = {
        "Astrub": (4, -19),
        "Astrub Centre": (5, -18),
        "Amakna Village": (0, 0),
        "Amakna Château": (3, -5),
        "Port Madrestam": (7, -4),
        "Coin des Bouftous": (5, 7),
        "Bord de Forêt": (-1, 13),
        "Bonta": (-26, -36),
        "Brakmar": (-26, 35),
        "Sufokia": (13, 26),
    }
    
    # Maps bloquées (eau, murs, etc.)
    BLOCKED_MAPS = set()
    
    @classmethod
    def is_blocked(cls, x, y):
        return (x, y) in cls.BLOCKED_MAPS
    
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
            if not cls.is_blocked(nx, ny):
                neighbors.append((direction, nx, ny, 1))
        return neighbors
    
    @classmethod
    def get_zaap_list(cls):
        return list(cls.ZAAPS.keys())
    
    @classmethod
    def get_zaap_pos(cls, name):
        return cls.ZAAPS.get(name)
    
    @classmethod
    def find_nearest_zaap(cls, x, y, known_zaaps):
        """Trouve le zaap connu le plus proche"""
        nearest = None
        min_dist = float('inf')
        
        for name in known_zaaps:
            if name in cls.ZAAPS:
                zx, zy = cls.ZAAPS[name]
                dist = abs(x - zx) + abs(y - zy)
                if dist < min_dist:
                    min_dist = dist
                    nearest = (name, zx, zy)
        
        return nearest, min_dist
    
    @classmethod
    def is_on_zaap(cls, x, y, known_zaaps):
        """Vérifie si on est sur un zaap connu"""
        for name in known_zaaps:
            if name in cls.ZAAPS:
                zx, zy = cls.ZAAPS[name]
                if (x, y) == (zx, zy):
                    return name
        return None


# ============================================================
#                    DÉTECTION DE POSITION (OCR)
# ============================================================

class PositionDetector:
    """Détecte la position actuelle en lisant l'écran"""
    
    def __init__(self, config):
        self.config = config
        self.last_position = None
    
    def capture_coords_region(self):
        """Capture la zone des coordonnées"""
        region = self.config.data.get("coords_region", {})
        x = region.get("x", 230)
        y = region.get("y", 40)
        w = region.get("width", 250)
        h = region.get("height", 60)
        
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        return screenshot
    
    def detect_position(self):
        """Détecte les coordonnées avec OCR"""
        if not HAS_OCR:
            return None
        
        try:
            # Capture
            img = self.capture_coords_region()
            img_np = np.array(img)
            
            # Prétraitement pour améliorer l'OCR
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            
            # OCR
            text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789-,: ')
            
            # Parser les coordonnées "4, -19"
            match = re.search(r'(-?\d+)\s*[,;]\s*(-?\d+)', text)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                self.last_position = (x, y)
                return (x, y)
            
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None


# ============================================================
#                    PATHFINDING A*
# ============================================================

class Pathfinder:
    """Algorithme A* pour trouver le chemin optimal"""
    
    def __init__(self, use_zaaps=True, known_zaaps=None):
        self.use_zaaps = use_zaaps
        self.known_zaaps = known_zaaps or []
    
    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def find_path(self, start, goal, max_iterations=50000):
        """Trouve le chemin avec A*"""
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
            
            # Voisins normaux
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
            
            # Zaaps
            if self.use_zaaps and self.known_zaaps:
                current_zaap = WorldMap.is_on_zaap(current[0], current[1], self.known_zaaps)
                if current_zaap:
                    for dest_name in self.known_zaaps:
                        if dest_name != current_zaap and dest_name in WorldMap.ZAAPS:
                            dest_pos = WorldMap.ZAAPS[dest_name]
                            
                            if dest_pos in closed_set:
                                continue
                            
                            tentative_g = g_scores.get(current, float('inf')) + 2
                            
                            if tentative_g < g_scores.get(dest_pos, float('inf')):
                                g_scores[dest_pos] = tentative_g
                                f_score = tentative_g + self.heuristic(dest_pos, goal)
                                
                                new_path = path + [(f"zaap:{dest_name}", dest_pos)]
                                counter += 1
                                heapq.heappush(open_set, (f_score, counter, dest_pos, new_path))
        
        return None
    
    def find_best_path(self, start, goal):
        """Trouve le meilleur chemin"""
        
        # Chemin direct
        direct_path = self.find_path(start, goal)
        direct_cost = len(direct_path) if direct_path else float('inf')
        
        best_path = direct_path
        best_cost = direct_cost
        
        # Via zaaps
        if self.use_zaaps and self.known_zaaps:
            # Zaap le plus proche de la destination
            dest_zaap, dest_zaap_dist = WorldMap.find_nearest_zaap(goal[0], goal[1], self.known_zaaps)
            
            if dest_zaap:
                # Zaap le plus proche de nous
                start_zaap, start_zaap_dist = WorldMap.find_nearest_zaap(start[0], start[1], self.known_zaaps)
                
                if start_zaap and start_zaap[0] != dest_zaap[0]:
                    total_cost = start_zaap_dist + 2 + dest_zaap_dist
                    
                    if total_cost < best_cost:
                        path_to_zaap = self.find_path(start, (start_zaap[1], start_zaap[2]))
                        if path_to_zaap is not None:
                            path_from_zaap = self.find_path((dest_zaap[1], dest_zaap[2]), goal)
                            if path_from_zaap is not None:
                                best_path = path_to_zaap + [(f"zaap:{dest_zaap[0]}", (dest_zaap[1], dest_zaap[2]))] + path_from_zaap
                                best_cost = len(best_path)
        
        return best_path


# ============================================================
#                    BOT AUTOMATIQUE
# ============================================================

class TravelBot:
    """Bot de déplacement 100% automatique"""
    
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
        
        self.position_detector = PositionDetector(config)
        self.pathfinder = Pathfinder(
            use_zaaps=config.data.get("use_zaaps", True),
            known_zaaps=config.data.get("known_zaaps", [])
        )
    
    def detect_position(self):
        """Détecte la position actuelle"""
        pos = self.position_detector.detect_position()
        if pos:
            self.current_pos = pos
            self.log(f"📍 Position détectée: [{pos[0]}, {pos[1]}]")
            return pos
        else:
            self.log("⚠️ Impossible de lire les coordonnées")
            return None
    
    def set_position(self, x, y):
        """Définit la position manuellement"""
        self.current_pos = (x, y)
        self.log(f"📍 Position: [{x}, {y}]")
    
    def calculate_path(self, target_x, target_y):
        """Calcule le chemin optimal"""
        if not self.current_pos:
            self.log("❌ Position actuelle inconnue!")
            return None
        
        self.target_pos = (target_x, target_y)
        
        self.log(f"🗺️ Calcul: [{self.current_pos[0]}, {self.current_pos[1]}] → [{target_x}, {target_y}]")
        
        self.pathfinder.known_zaaps = self.config.data.get("known_zaaps", [])
        self.pathfinder.use_zaaps = self.config.data.get("use_zaaps", True)
        
        path = self.pathfinder.find_best_path(self.current_pos, self.target_pos)
        
        if path:
            self.current_path = path
            self.path_index = 0
            
            zaap_count = sum(1 for move, _ in path if str(move).startswith("zaap:"))
            walk_count = len(path) - zaap_count
            
            self.log(f"✅ Chemin: {len(path)} étapes ({walk_count} marche, {zaap_count} zaap)")
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
        pyautogui.click(pos["x"], pos["y"])
        return True
    
    def use_zaap(self, destination_name):
        """Utilise un zaap automatiquement"""
        self.log(f"🌀 Zaap vers {destination_name}...")
        
        # 1. Cliquer sur le zaap
        zaap_pos = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        self.log(f"   → Clic sur le zaap...")
        pyautogui.click(zaap_pos["x"], zaap_pos["y"])
        time.sleep(1.0)
        
        # 2. Chercher la destination dans le menu
        self.log(f"   → Recherche de {destination_name}...")
        
        # Positions dans le menu zaap (à calibrer selon le jeu)
        zaap_menu_positions = {
            "Astrub": {"x": 500, "y": 280},
            "Astrub Centre": {"x": 500, "y": 300},
            "Amakna Village": {"x": 500, "y": 320},
            "Amakna Château": {"x": 500, "y": 340},
            "Bonta": {"x": 500, "y": 360},
            "Brakmar": {"x": 500, "y": 380},
            "Port Madrestam": {"x": 500, "y": 400},
            "Coin des Bouftous": {"x": 500, "y": 420},
            "Bord de Forêt": {"x": 500, "y": 440},
            "Sufokia": {"x": 500, "y": 460},
        }
        
        if destination_name in zaap_menu_positions:
            menu_pos = zaap_menu_positions[destination_name]
            pyautogui.click(menu_pos["x"], menu_pos["y"])
            time.sleep(0.5)
            
            # Double-clic pour téléporter
            pyautogui.click(menu_pos["x"], menu_pos["y"])
        
        # 3. Attendre le chargement
        self.log(f"   → Téléportation...")
        time.sleep(self.config.data.get("zaap_delay", 2.5))
        
        return True
    
    def execute_move(self, move_type, target_pos):
        """Exécute un mouvement"""
        
        if str(move_type).startswith("zaap:"):
            zaap_name = move_type.split(":")[1]
            success = self.use_zaap(zaap_name)
            if success:
                self.current_pos = target_pos
            return success
        else:
            icons = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            self.log(f"🚶 {icons.get(move_type, '?')} [{target_pos[0]}, {target_pos[1]}]")
            
            success = self.click_direction(move_type)
            if success:
                time.sleep(self.config.data.get("move_delay", 1.5))
                self.current_pos = target_pos
                return True
            
            return False
    
    def start_travel(self):
        """Démarre le voyage"""
        if not self.current_path:
            self.log("❌ Calcule d'abord le chemin!")
            return
        
        if self.running:
            return
        
        self.running = True
        self.paused = False
        self.stop_requested = False
        self.path_index = 0
        
        threading.Thread(target=self._travel_loop, daemon=True).start()
    
    def _travel_loop(self):
        """Boucle principale"""
        total = len(self.current_path)
        self.log(f"🚀 Départ! {total} étapes")
        
        while self.running and self.path_index < len(self.current_path):
            if self.stop_requested:
                break
            
            while self.paused and not self.stop_requested:
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
                time.sleep(1)
        
        if self.path_index >= len(self.current_path) and not self.stop_requested:
            self.log(f"🎉 ARRIVÉ à [{self.target_pos[0]}, {self.target_pos[1]}]!")
        
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
        self.root.title("🗺️ Dofus Travel Bot v3.0 - AUTO")
        self.root.geometry("750x900")
        self.root.configure(bg=THEME['bg'])
        
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 750) // 2
        y = (self.root.winfo_screenheight() - 900) // 2
        self.root.geometry(f"750x900+{x}+{y}")
    
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('F5', self.start_travel)
            keyboard.add_hotkey('F6', self.pause_travel)
            keyboard.add_hotkey('F7', self.stop_travel)
            keyboard.add_hotkey('F8', self.detect_position)
        except:
            pass
    
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=THEME['bg2'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🗺️ DOFUS TRAVEL BOT v3.0", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(pady=8)
        tk.Label(header, text="🤖 100% AUTOMATIQUE - OCR + Zaaps + Pathfinding",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['success']).pack()
        
        # Notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.create_navigation_tab(notebook)
        self.create_calibration_tab(notebook)
        self.create_zaaps_tab(notebook)
        
        # Status
        status = tk.Frame(self.root, bg=THEME['bg2'], height=25)
        status.pack(fill='x', side='bottom')
        self.status_label = tk.Label(status, text="F5=Go • F6=Pause • F7=Stop • F8=Détecter position",
                                     font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2'])
        self.status_label.pack(pady=3)
    
    def create_navigation_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🗺️ Navigation")
        
        # Position Actuelle
        pos_frame = tk.LabelFrame(tab, text="📍 Position Actuelle", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        pos_frame.pack(fill='x', padx=10, pady=5)
        
        pos_row1 = tk.Frame(pos_frame, bg=THEME['bg2'])
        pos_row1.pack(fill='x')
        
        tk.Label(pos_row1, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.current_x = tk.Entry(pos_row1, width=7, font=('Segoe UI', 11), bg=THEME['bg3'], fg=THEME['text'])
        self.current_x.pack(side='left', padx=5)
        
        tk.Label(pos_row1, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.current_y = tk.Entry(pos_row1, width=7, font=('Segoe UI', 11), bg=THEME['bg3'], fg=THEME['text'])
        self.current_y.pack(side='left', padx=5)
        
        tk.Button(pos_row1, text="📍 Définir", bg=THEME['accent2'], fg='white',
                 command=self.set_position).pack(side='left', padx=10)
        
        tk.Button(pos_row1, text="🔍 DÉTECTER (F8)", bg=THEME['success'], fg='white',
                 font=('Segoe UI', 9, 'bold'),
                 command=self.detect_position).pack(side='left', padx=5)
        
        # Destination
        dest_frame = tk.LabelFrame(tab, text="🎯 Destination", font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
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
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        opt_frame.pack(fill='x', padx=10, pady=5)
        
        self.use_zaaps_var = tk.BooleanVar(value=self.config.data.get("use_zaaps", True))
        tk.Checkbutton(opt_frame, text="🌀 Utiliser les Zaaps automatiquement",
                      variable=self.use_zaaps_var, bg=THEME['bg2'], fg=THEME['text'],
                      selectcolor=THEME['bg3']).pack(anchor='w')
        
        delay_row = tk.Frame(opt_frame, bg=THEME['bg2'])
        delay_row.pack(fill='x', pady=5)
        tk.Label(delay_row, text="Délai par map:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.delay_var = tk.StringVar(value=str(self.config.data.get("move_delay", 1.5)))
        tk.Spinbox(delay_row, from_=0.5, to=5.0, increment=0.1, width=5,
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
        
        tk.Button(btn_row, text="▶️ GO (F5)", font=('Segoe UI', 11, 'bold'),
                 bg=THEME['success'], fg='white', width=12,
                 command=self.start_travel).pack(side='left', padx=3)
        tk.Button(btn_row, text="⏸️ Pause (F6)", font=('Segoe UI', 9),
                 bg=THEME['warning'], fg='white', width=11,
                 command=self.pause_travel).pack(side='left', padx=3)
        tk.Button(btn_row, text="⏹️ Stop (F7)", font=('Segoe UI', 9),
                 bg=THEME['accent'], fg='white', width=11,
                 command=self.stop_travel).pack(side='left', padx=3)
        
        # Chemin
        path_frame = tk.LabelFrame(tab, text="📋 Chemin calculé", font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        path_frame.pack(fill='x', padx=10, pady=5)
        
        self.path_text = tk.Text(path_frame, height=6, font=('Consolas', 9),
                                 bg=THEME['bg3'], fg=THEME['text'])
        self.path_text.pack(fill='x')
        
        # Log
        log_frame = tk.LabelFrame(tab, text="📜 Log", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, font=('Consolas', 9),
                                bg=THEME['bg3'], fg=THEME['text'])
        self.log_text.pack(fill='both', expand=True)
        
        self.log("🗺️ Travel Bot v3.0 - 100% AUTO")
        self.log("─" * 40)
        self.log("1. Clique F8 ou entre ta position")
        self.log("2. Entre ta destination ou choisis zaap")
        self.log("3. CALCULER puis GO!")
        if not HAS_OCR:
            self.log("")
            self.log("⚠️ OCR non disponible!")
            self.log("   pip install pytesseract")
    
    def create_calibration_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🎯 Calibration")
        
        tk.Label(tab, text="🎯 Calibration", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        # Zone OCR
        coords_frame = tk.LabelFrame(tab, text="📍 Zone des coordonnées (OCR)", 
                                     font=('Segoe UI', 10, 'bold'),
                                     bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        coords_frame.pack(fill='x', padx=10, pady=5)
        
        coords_row = tk.Frame(coords_frame, bg=THEME['bg2'])
        coords_row.pack(fill='x', pady=5)
        
        region = self.config.data.get("coords_region", {})
        
        tk.Label(coords_row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_x = tk.Entry(coords_row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_x.insert(0, str(region.get("x", 230)))
        self.ocr_x.pack(side='left', padx=5)
        
        tk.Label(coords_row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_y = tk.Entry(coords_row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_y.insert(0, str(region.get("y", 40)))
        self.ocr_y.pack(side='left', padx=5)
        
        tk.Label(coords_row, text="L:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_w = tk.Entry(coords_row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_w.insert(0, str(region.get("width", 250)))
        self.ocr_w.pack(side='left', padx=5)
        
        tk.Label(coords_row, text="H:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_h = tk.Entry(coords_row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_h.insert(0, str(region.get("height", 60)))
        self.ocr_h.pack(side='left', padx=5)
        
        tk.Button(coords_frame, text="🧪 Tester OCR", bg=THEME['accent2'], fg='white',
                 command=self.test_ocr).pack(pady=5)
        
        # Clics
        click_frame = tk.LabelFrame(tab, text="🖱️ Clics changement de map",
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        click_frame.pack(fill='x', padx=10, pady=5)
        
        self.click_entries = {}
        directions = [("up", "↑ Haut"), ("down", "↓ Bas"), ("left", "← Gauche"), ("right", "→ Droite")]
        
        for direction, label in directions:
            row = tk.Frame(click_frame, bg=THEME['bg2'])
            row.pack(fill='x', pady=2)
            
            tk.Label(row, text=f"{label}:", width=10, anchor='w',
                    bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            
            pos = self.config.data.get("click_positions", {}).get(direction, {"x": 0, "y": 0})
            
            tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            x_entry = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
            x_entry.insert(0, str(pos["x"]))
            x_entry.pack(side='left', padx=2)
            
            tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            y_entry = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
            y_entry.insert(0, str(pos["y"]))
            y_entry.pack(side='left', padx=2)
            
            self.click_entries[direction] = (x_entry, y_entry)
            
            tk.Button(row, text="🎯", bg=THEME['card'], fg=THEME['text'],
                     command=lambda d=direction: self.calibrate_click(d)).pack(side='left', padx=5)
        
        # Zaap
        zaap_frame = tk.LabelFrame(tab, text="🌀 Clic sur Zaap",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        zaap_frame.pack(fill='x', padx=10, pady=5)
        
        zaap_row = tk.Frame(zaap_frame, bg=THEME['bg2'])
        zaap_row.pack(fill='x')
        
        zaap_click = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        
        tk.Label(zaap_row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.zaap_x = tk.Entry(zaap_row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.zaap_x.insert(0, str(zaap_click["x"]))
        self.zaap_x.pack(side='left', padx=5)
        
        tk.Label(zaap_row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.zaap_y = tk.Entry(zaap_row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.zaap_y.insert(0, str(zaap_click["y"]))
        self.zaap_y.pack(side='left', padx=5)
        
        tk.Button(zaap_row, text="🎯", bg=THEME['card'], fg=THEME['text'],
                 command=self.calibrate_zaap).pack(side='left', padx=5)
        
        # Sauvegarder
        tk.Button(tab, text="💾 SAUVEGARDER", font=('Segoe UI', 10, 'bold'),
                 bg=THEME['success'], fg='white', command=self.save_calibration).pack(pady=15)
    
    def create_zaaps_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🌀 Zaaps")
        
        tk.Label(tab, text="🌀 Zaaps Connus", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
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
                 command=lambda: [v.set(True) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Rien", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(False) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(btn_frame, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 command=self.save_zaaps).pack(side='left', padx=10)
    
    # ===== MÉTHODES =====
    
    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self._log(f"[{timestamp}] {msg}"))
    
    def _log(self, msg):
        self.log_text.insert('end', msg + "\n")
        self.log_text.see('end')
    
    def detect_position(self):
        self.log("🔍 Détection...")
        pos = self.bot.detect_position()
        if pos:
            self.current_x.delete(0, 'end')
            self.current_x.insert(0, str(pos[0]))
            self.current_y.delete(0, 'end')
            self.current_y.insert(0, str(pos[1]))
    
    def set_position(self):
        try:
            x, y = int(self.current_x.get()), int(self.current_y.get())
            self.bot.set_position(x, y)
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
            self.log(f"🎯 → {zaap_name} [{pos[0]}, {pos[1]}]")
    
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
        
        self.bot.set_position(cx, cy)
        path = self.bot.calculate_path(dx, dy)
        
        self.path_text.delete('1.0', 'end')
        
        if path:
            self.path_text.insert('end', f"[{cx},{cy}] → [{dx},{dy}] = {len(path)} étapes\n\n")
            
            arrows = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            for i, (move, pos) in enumerate(path):
                if str(move).startswith("zaap:"):
                    self.path_text.insert('end', f"{i+1}. 🌀 {move.split(':')[1]}\n")
                else:
                    self.path_text.insert('end', f"{i+1}. {arrows.get(move,'?')} [{pos[0]},{pos[1]}]\n")
        else:
            self.path_text.insert('end', "❌ Pas de chemin!")
    
    def start_travel(self):
        if not self.bot.current_path:
            self.calculate_path()
        if self.bot.current_path:
            self.bot.start_travel()
    
    def pause_travel(self):
        self.bot.pause()
    
    def stop_travel(self):
        self.bot.stop()
    
    def test_ocr(self):
        try:
            self.config.data["coords_region"] = {
                "x": int(self.ocr_x.get()),
                "y": int(self.ocr_y.get()),
                "width": int(self.ocr_w.get()),
                "height": int(self.ocr_h.get())
            }
        except:
            pass
        self.detect_position()
    
    def calibrate_click(self, direction):
        messagebox.showinfo("Calibration", f"OK puis clique sur bord '{direction}' dans 3s")
        
        def do_cal():
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            self.click_entries[direction][0].delete(0, 'end')
            self.click_entries[direction][0].insert(0, str(x))
            self.click_entries[direction][1].delete(0, 'end')
            self.click_entries[direction][1].insert(0, str(y))
            self.log(f"✅ {direction}: {x}, {y}")
        
        threading.Thread(target=do_cal, daemon=True).start()
    
    def calibrate_zaap(self):
        messagebox.showinfo("Calibration", "OK puis clique sur le zaap dans 3s")
        
        def do_cal():
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            self.zaap_x.delete(0, 'end')
            self.zaap_x.insert(0, str(x))
            self.zaap_y.delete(0, 'end')
            self.zaap_y.insert(0, str(y))
            self.log(f"✅ Zaap: {x}, {y}")
        
        threading.Thread(target=do_cal, daemon=True).start()
    
    def save_calibration(self):
        try:
            self.config.data["coords_region"] = {
                "x": int(self.ocr_x.get()),
                "y": int(self.ocr_y.get()),
                "width": int(self.ocr_w.get()),
                "height": int(self.ocr_h.get())
            }
            
            for direction, (x_e, y_e) in self.click_entries.items():
                self.config.data["click_positions"][direction] = {
                    "x": int(x_e.get()), "y": int(y_e.get())
                }
            
            self.config.data["zaap_click"] = {
                "x": int(self.zaap_x.get()),
                "y": int(self.zaap_y.get())
            }
            
            self.config.save()
            messagebox.showinfo("OK", "Sauvegardé!")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    def save_zaaps(self):
        known = [n for n, v in self.zaap_vars.items() if v.get()]
        self.config.data["known_zaaps"] = known
        self.config.save()
        self.bot.pathfinder.known_zaaps = known
        messagebox.showinfo("OK", f"{len(known)} zaaps!")


# ============================================================
#                    MAIN
# ============================================================

if __name__ == "__main__":
    if not HAS_DEPS:
        print("❌ Dépendances manquantes!")
        input("Entrée...")
    else:
        app = TravelBotGUI()
        app.run()
