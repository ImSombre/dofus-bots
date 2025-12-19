"""
🗺️ Dofus Retro Travel Bot v3.1
Bot de déplacement 100% AUTOMATIQUE
- Calibration visuelle améliorée
- OCR optimisé pour Dofus
- Zaaps automatiques
- Pathfinding A*
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import time
import threading
import heapq
import re

try:
    import pyautogui
    import keyboard
    from PIL import ImageGrab, Image, ImageTk, ImageDraw
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
            "coords_region": {"x": 232, "y": 78, "width": 160, "height": 25},
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
            "use_zaaps": True
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
    
    BLOCKED_MAPS = set()
    
    @classmethod
    def is_blocked(cls, x, y):
        return (x, y) in cls.BLOCKED_MAPS
    
    @classmethod
    def get_neighbors(cls, x, y):
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
        for name in known_zaaps:
            if name in cls.ZAAPS:
                zx, zy = cls.ZAAPS[name]
                if (x, y) == (zx, zy):
                    return name
        return None


# ============================================================
#                    SÉLECTEUR DE ZONE (pour calibration)
# ============================================================

class RegionSelector:
    """Permet de sélectionner une zone à la souris"""
    
    def __init__(self, callback):
        self.callback = callback
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        
    def start(self):
        """Lance la sélection"""
        # Prendre un screenshot
        self.screenshot = ImageGrab.grab()
        
        # Créer une fenêtre fullscreen
        self.root = tk.Toplevel()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(cursor="cross")
        
        # Afficher le screenshot
        self.tk_image = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)
        
        # Overlay semi-transparent
        self.canvas.create_rectangle(0, 0, self.root.winfo_screenwidth(), 
                                     self.root.winfo_screenheight(),
                                     fill='black', stipple='gray50', tags='overlay')
        
        # Instructions
        self.canvas.create_text(self.root.winfo_screenwidth()//2, 30,
                               text="🎯 Dessine un rectangle autour des COORDONNÉES (ex: 4, -19)",
                               font=('Segoe UI', 16, 'bold'), fill='white')
        self.canvas.create_text(self.root.winfo_screenwidth()//2, 60,
                               text="Clic gauche = dessiner | Échap = annuler",
                               font=('Segoe UI', 12), fill='yellow')
        
        # Rectangle de sélection
        self.rect = None
        
        # Bindings
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.root.bind('<Escape>', lambda e: self.root.destroy())
    
    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='#00ff00', width=3
        )
    
    def on_drag(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, 
                          self.end_x, self.end_y)
    
    def on_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        
        # Calculer la région
        x = min(self.start_x, self.end_x)
        y = min(self.start_y, self.end_y)
        w = abs(self.end_x - self.start_x)
        h = abs(self.end_y - self.start_y)
        
        if w > 10 and h > 10:
            self.root.destroy()
            self.callback(x, y, w, h)
        else:
            # Trop petit, réessayer
            if self.rect:
                self.canvas.delete(self.rect)


# ============================================================
#                    DÉTECTION DE POSITION (OCR amélioré)
# ============================================================

class PositionDetector:
    def __init__(self, config):
        self.config = config
        self.last_position = None
        self.last_capture = None
    
    def capture_region(self):
        """Capture la zone configurée"""
        region = self.config.data.get("coords_region", {})
        x = region.get("x", 232)
        y = region.get("y", 78)
        w = region.get("width", 160)
        h = region.get("height", 25)
        
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        self.last_capture = screenshot
        return screenshot
    
    def preprocess_image(self, img):
        """Prétraitement optimisé pour le texte Dofus (blanc sur fond sombre)"""
        img_np = np.array(img)
        
        # Convertir en niveaux de gris
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        
        # Agrandir l'image (aide l'OCR)
        scale = 3
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Augmenter le contraste
        gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
        
        # Seuillage pour isoler le texte blanc
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Inverser si nécessaire (texte noir sur fond blanc pour OCR)
        # Compter les pixels blancs
        white_pixels = np.sum(thresh == 255)
        total_pixels = thresh.size
        
        if white_pixels > total_pixels / 2:
            # Trop de blanc, inverser
            thresh = cv2.bitwise_not(thresh)
        
        return thresh
    
    def detect_position(self):
        """Détecte les coordonnées avec OCR"""
        if not HAS_OCR:
            return None
        
        try:
            img = self.capture_region()
            processed = self.preprocess_image(img)
            
            # OCR avec config optimisée
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789-,.'
            text = pytesseract.image_to_string(processed, config=custom_config)
            
            # Nettoyer le texte
            text = text.strip().replace(' ', '').replace('.', ',')
            
            # Parser: chercher le pattern X, Y (avec X et Y pouvant être négatifs)
            match = re.search(r'(-?\d+)[,;:\s]+(-?\d+)', text)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                self.last_position = (x, y)
                return (x, y)
            
            # Essai alternatif: juste deux nombres
            numbers = re.findall(r'-?\d+', text)
            if len(numbers) >= 2:
                x = int(numbers[0])
                y = int(numbers[1])
                self.last_position = (x, y)
                return (x, y)
                
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None
    
    def get_last_capture_tk(self, max_size=300):
        """Retourne la dernière capture en format Tk pour affichage"""
        if self.last_capture is None:
            return None
        
        img = self.last_capture.copy()
        
        # Redimensionner pour l'affichage
        w, h = img.size
        scale = min(max_size / w, max_size / h, 3)  # Agrandir jusqu'à 3x
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.NEAREST)
        
        return ImageTk.PhotoImage(img)


# ============================================================
#                    PATHFINDING A*
# ============================================================

class Pathfinder:
    def __init__(self, use_zaaps=True, known_zaaps=None):
        self.use_zaaps = use_zaaps
        self.known_zaaps = known_zaaps or []
    
    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def find_path(self, start, goal, max_iterations=50000):
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
        direct_path = self.find_path(start, goal)
        direct_cost = len(direct_path) if direct_path else float('inf')
        best_path = direct_path
        best_cost = direct_cost
        
        if self.use_zaaps and self.known_zaaps:
            dest_zaap, dest_zaap_dist = WorldMap.find_nearest_zaap(goal[0], goal[1], self.known_zaaps)
            if dest_zaap:
                start_zaap, start_zaap_dist = WorldMap.find_nearest_zaap(start[0], start[1], self.known_zaaps)
                if start_zaap and start_zaap[0] != dest_zaap[0]:
                    total_cost = start_zaap_dist + 2 + dest_zaap_dist
                    if total_cost < best_cost:
                        path_to_zaap = self.find_path(start, (start_zaap[1], start_zaap[2]))
                        if path_to_zaap is not None:
                            path_from_zaap = self.find_path((dest_zaap[1], dest_zaap[2]), goal)
                            if path_from_zaap is not None:
                                best_path = path_to_zaap + [(f"zaap:{dest_zaap[0]}", (dest_zaap[1], dest_zaap[2]))] + path_from_zaap
        
        return best_path


# ============================================================
#                    BOT
# ============================================================

class TravelBot:
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
        pos = self.position_detector.detect_position()
        if pos:
            self.current_pos = pos
            self.log(f"📍 Position: [{pos[0]}, {pos[1]}]")
            return pos
        else:
            self.log("⚠️ OCR échoué - entre la position manuellement")
            return None
    
    def set_position(self, x, y):
        self.current_pos = (x, y)
        self.log(f"📍 Position: [{x}, {y}]")
    
    def calculate_path(self, target_x, target_y):
        if not self.current_pos:
            self.log("❌ Position inconnue!")
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
            self.log(f"✅ {len(path)} étapes ({len(path)-zaap_count} marche, {zaap_count} zaap)")
            return path
        else:
            self.log("❌ Pas de chemin!")
            return None
    
    def click_direction(self, direction):
        positions = self.config.data.get("click_positions", {})
        if direction not in positions:
            return False
        pos = positions[direction]
        pyautogui.click(pos["x"], pos["y"])
        return True
    
    def use_zaap(self, destination_name):
        self.log(f"🌀 Zaap → {destination_name}")
        
        # Clic sur zaap
        zaap_pos = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        pyautogui.click(zaap_pos["x"], zaap_pos["y"])
        time.sleep(1.0)
        
        # Menu zaap - positions approximatives
        zaap_menu = {
            "Astrub": {"x": 500, "y": 280},
            "Amakna Village": {"x": 500, "y": 300},
            "Bonta": {"x": 500, "y": 320},
        }
        
        if destination_name in zaap_menu:
            pos = zaap_menu[destination_name]
            pyautogui.doubleClick(pos["x"], pos["y"])
        
        time.sleep(self.config.data.get("zaap_delay", 2.5))
        return True
    
    def execute_move(self, move_type, target_pos):
        if str(move_type).startswith("zaap:"):
            zaap_name = move_type.split(":")[1]
            self.use_zaap(zaap_name)
            self.current_pos = target_pos
            return True
        else:
            icons = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            self.log(f"🚶 {icons.get(move_type, '?')} [{target_pos[0]}, {target_pos[1]}]")
            
            if self.click_direction(move_type):
                time.sleep(self.config.data.get("move_delay", 1.5))
                self.current_pos = target_pos
                return True
            return False
    
    def start_travel(self):
        if not self.current_path:
            return
        if self.running:
            return
        
        self.running = True
        self.paused = False
        self.stop_requested = False
        self.path_index = 0
        
        threading.Thread(target=self._travel_loop, daemon=True).start()
    
    def _travel_loop(self):
        total = len(self.current_path)
        self.log(f"🚀 Go! {total} étapes")
        
        while self.running and self.path_index < len(self.current_path):
            if self.stop_requested:
                break
            
            while self.paused and not self.stop_requested:
                time.sleep(0.1)
            
            if self.stop_requested:
                break
            
            move_type, target_pos = self.current_path[self.path_index]
            self.log(f"[{self.path_index + 1}/{total}]")
            
            if self.execute_move(move_type, target_pos):
                self.path_index += 1
            else:
                time.sleep(1)
        
        if self.path_index >= len(self.current_path) and not self.stop_requested:
            self.log(f"🎉 Arrivé!")
        
        self.running = False
    
    def pause(self):
        self.paused = not self.paused
        self.log("⏸️ Pause" if self.paused else "▶️ Reprise")
    
    def stop(self):
        self.stop_requested = True
        self.running = False
        self.log("⏹️ Stop")


# ============================================================
#                    INTERFACE
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
        self.bot = TravelBot(self.config, self.log)
        self.preview_image = None
        
        self.setup_window()
        self.create_widgets()
        self.setup_hotkeys()
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🗺️ Dofus Travel Bot v3.1")
        self.root.geometry("800x950")
        self.root.configure(bg=THEME['bg'])
    
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
        header = tk.Frame(self.root, bg=THEME['bg2'], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="🗺️ DOFUS TRAVEL BOT v3.1", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(pady=15)
        
        # Notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.create_navigation_tab(notebook)
        self.create_calibration_tab(notebook)
        self.create_zaaps_tab(notebook)
        
        # Status
        status = tk.Frame(self.root, bg=THEME['bg2'], height=25)
        status.pack(fill='x', side='bottom')
        tk.Label(status, text="F5=Go • F6=Pause • F7=Stop • F8=Détecter",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(pady=3)
    
    def create_navigation_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🗺️ Navigation")
        
        # Position
        pos_frame = tk.LabelFrame(tab, text="📍 Position Actuelle", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        pos_frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(pos_frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.current_x = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.current_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.current_y = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.current_y.pack(side='left', padx=5)
        
        tk.Button(row, text="📍 Définir", bg=THEME['accent2'], fg='white',
                 command=self.set_position).pack(side='left', padx=10)
        
        tk.Button(row, text="🔍 DÉTECTER (F8)", bg=THEME['success'], fg='white',
                 font=('Segoe UI', 9, 'bold'), command=self.detect_position).pack(side='left', padx=5)
        
        # Destination
        dest_frame = tk.LabelFrame(tab, text="🎯 Destination", font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        dest_frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(dest_frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.dest_x = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.dest_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.dest_y = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.dest_y.pack(side='left', padx=5)
        
        tk.Label(dest_frame, text="─── OU Zaap ───", bg=THEME['bg2'], fg=THEME['text2']).pack(pady=5)
        
        self.zaap_var = tk.StringVar()
        ttk.Combobox(dest_frame, textvariable=self.zaap_var, width=30,
                    values=WorldMap.get_zaap_list(), state='readonly').pack()
        self.zaap_var.trace('w', self.on_zaap_selected)
        
        # Options
        opt_frame = tk.LabelFrame(tab, text="⚙️ Options", font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        opt_frame.pack(fill='x', padx=10, pady=5)
        
        self.use_zaaps_var = tk.BooleanVar(value=self.config.data.get("use_zaaps", True))
        tk.Checkbutton(opt_frame, text="🌀 Utiliser Zaaps", variable=self.use_zaaps_var,
                      bg=THEME['bg2'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(anchor='w')
        
        row = tk.Frame(opt_frame, bg=THEME['bg2'])
        row.pack(fill='x', pady=5)
        tk.Label(row, text="Délai:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.delay_var = tk.StringVar(value=str(self.config.data.get("move_delay", 1.5)))
        tk.Spinbox(row, from_=0.5, to=5.0, increment=0.1, width=5,
                  textvariable=self.delay_var).pack(side='left', padx=5)
        tk.Label(row, text="sec", bg=THEME['bg2'], fg=THEME['text2']).pack(side='left')
        
        # Boutons
        btn_frame = tk.Frame(tab, bg=THEME['bg'])
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(btn_frame, text="🔍 CALCULER", font=('Segoe UI', 12, 'bold'),
                 bg=THEME['accent2'], fg='white', width=20,
                 command=self.calculate_path).pack(pady=5)
        
        row = tk.Frame(btn_frame, bg=THEME['bg'])
        row.pack()
        tk.Button(row, text="▶️ GO (F5)", font=('Segoe UI', 11, 'bold'),
                 bg=THEME['success'], fg='white', width=12,
                 command=self.start_travel).pack(side='left', padx=3)
        tk.Button(row, text="⏸️ Pause", bg=THEME['warning'], fg='white', width=10,
                 command=self.pause_travel).pack(side='left', padx=3)
        tk.Button(row, text="⏹️ Stop", bg=THEME['accent'], fg='white', width=10,
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
        self.log_text = tk.Text(log_frame, height=8, font=('Consolas', 9),
                                bg=THEME['bg3'], fg=THEME['text'])
        self.log_text.pack(fill='both', expand=True)
        
        self.log("🗺️ Travel Bot v3.1")
        self.log("─" * 35)
        if not HAS_OCR:
            self.log("⚠️ OCR non dispo - position manuelle")
        else:
            self.log("✅ OCR disponible")
    
    def create_calibration_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🎯 Calibration")
        
        # === ZONE COORDONNÉES ===
        ocr_frame = tk.LabelFrame(tab, text="📍 Zone des coordonnées (OCR)", 
                                  font=('Segoe UI', 10, 'bold'),
                                  bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        ocr_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(ocr_frame, text="Sélectionne la zone où s'affiche '4, -19' dans Dofus",
                bg=THEME['bg2'], fg=THEME['text2']).pack(anchor='w')
        
        # Valeurs actuelles
        row = tk.Frame(ocr_frame, bg=THEME['bg2'])
        row.pack(fill='x', pady=5)
        
        region = self.config.data.get("coords_region", {})
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_x = tk.Entry(row, width=5, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_x.insert(0, str(region.get("x", 232)))
        self.ocr_x.pack(side='left', padx=3)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_y = tk.Entry(row, width=5, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_y.insert(0, str(region.get("y", 78)))
        self.ocr_y.pack(side='left', padx=3)
        
        tk.Label(row, text="L:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_w = tk.Entry(row, width=5, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_w.insert(0, str(region.get("width", 160)))
        self.ocr_w.pack(side='left', padx=3)
        
        tk.Label(row, text="H:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.ocr_h = tk.Entry(row, width=5, bg=THEME['bg3'], fg=THEME['text'])
        self.ocr_h.insert(0, str(region.get("height", 25)))
        self.ocr_h.pack(side='left', padx=3)
        
        # Boutons
        btn_row = tk.Frame(ocr_frame, bg=THEME['bg2'])
        btn_row.pack(fill='x', pady=5)
        
        tk.Button(btn_row, text="🎯 SÉLECTIONNER LA ZONE", font=('Segoe UI', 10, 'bold'),
                 bg=THEME['accent2'], fg='white',
                 command=self.select_ocr_region).pack(side='left', padx=5)
        
        tk.Button(btn_row, text="🧪 Tester OCR", bg=THEME['card'], fg=THEME['text'],
                 command=self.test_ocr).pack(side='left', padx=5)
        
        # Aperçu
        preview_frame = tk.Frame(ocr_frame, bg=THEME['bg3'], padx=5, pady=5)
        preview_frame.pack(fill='x', pady=5)
        
        tk.Label(preview_frame, text="Aperçu de la capture:", 
                bg=THEME['bg3'], fg=THEME['text2']).pack(anchor='w')
        
        self.preview_label = tk.Label(preview_frame, bg=THEME['bg3'], 
                                      text="(clique 'Tester OCR' pour voir)",
                                      fg=THEME['text2'])
        self.preview_label.pack(pady=5)
        
        self.ocr_result_label = tk.Label(ocr_frame, text="Résultat: -", 
                                         font=('Segoe UI', 11, 'bold'),
                                         bg=THEME['bg2'], fg=THEME['success'])
        self.ocr_result_label.pack(pady=5)
        
        # === CLICS DE DÉPLACEMENT ===
        click_frame = tk.LabelFrame(tab, text="🖱️ Clics pour changer de map",
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
            
            x_e = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
            x_e.insert(0, str(pos["x"]))
            x_e.pack(side='left', padx=2)
            
            y_e = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
            y_e.insert(0, str(pos["y"]))
            y_e.pack(side='left', padx=2)
            
            self.click_entries[direction] = (x_e, y_e)
            
            tk.Button(row, text="🎯", bg=THEME['card'], fg=THEME['text'],
                     command=lambda d=direction: self.calibrate_click(d)).pack(side='left', padx=5)
        
        # === ZAAP ===
        zaap_frame = tk.LabelFrame(tab, text="🌀 Position du Zaap",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        zaap_frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(zaap_frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        zaap = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.zaap_x = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.zaap_x.insert(0, str(zaap["x"]))
        self.zaap_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.zaap_y = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.zaap_y.insert(0, str(zaap["y"]))
        self.zaap_y.pack(side='left', padx=5)
        
        tk.Button(row, text="🎯", bg=THEME['card'], fg=THEME['text'],
                 command=self.calibrate_zaap).pack(side='left', padx=5)
        
        # SAUVEGARDER
        tk.Button(tab, text="💾 SAUVEGARDER TOUT", font=('Segoe UI', 11, 'bold'),
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
        
        for name, (x, y) in sorted(WorldMap.ZAAPS.items()):
            var = tk.BooleanVar(value=(name in known))
            self.zaap_vars[name] = var
            
            frame = tk.Frame(scroll_frame, bg=THEME['bg2'])
            frame.pack(fill='x', padx=10, pady=2)
            
            tk.Checkbutton(frame, text=name, variable=var, bg=THEME['bg2'],
                          fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left')
            tk.Label(frame, text=f"[{x}, {y}]", font=('Consolas', 9),
                    bg=THEME['bg2'], fg=THEME['text2']).pack(side='right')
        
        row = tk.Frame(tab, bg=THEME['bg'])
        row.pack(pady=10)
        tk.Button(row, text="✅ Tout", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(True) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(row, text="❌ Rien", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(False) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(row, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 command=self.save_zaaps).pack(side='left', padx=10)
    
    # ===== MÉTHODES =====
    
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self._log(f"[{ts}] {msg}"))
    
    def _log(self, msg):
        self.log_text.insert('end', msg + "\n")
        self.log_text.see('end')
    
    def detect_position(self):
        self.log("🔍 Détection OCR...")
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
    
    def on_zaap_selected(self, *args):
        name = self.zaap_var.get()
        pos = WorldMap.get_zaap_pos(name)
        if pos:
            self.dest_x.delete(0, 'end')
            self.dest_x.insert(0, str(pos[0]))
            self.dest_y.delete(0, 'end')
            self.dest_y.insert(0, str(pos[1]))
    
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
    
    def select_ocr_region(self):
        """Ouvre le sélecteur de zone"""
        self.root.iconify()  # Minimiser
        time.sleep(0.3)
        
        def on_selected(x, y, w, h):
            self.root.deiconify()  # Restaurer
            self.ocr_x.delete(0, 'end')
            self.ocr_x.insert(0, str(x))
            self.ocr_y.delete(0, 'end')
            self.ocr_y.insert(0, str(y))
            self.ocr_w.delete(0, 'end')
            self.ocr_w.insert(0, str(w))
            self.ocr_h.delete(0, 'end')
            self.ocr_h.insert(0, str(h))
            self.log(f"✅ Zone sélectionnée: {x}, {y}, {w}x{h}")
            
            # Tester immédiatement
            self.root.after(500, self.test_ocr)
        
        selector = RegionSelector(on_selected)
        selector.start()
    
    def test_ocr(self):
        """Teste l'OCR et affiche l'aperçu"""
        try:
            self.config.data["coords_region"] = {
                "x": int(self.ocr_x.get()),
                "y": int(self.ocr_y.get()),
                "width": int(self.ocr_w.get()),
                "height": int(self.ocr_h.get())
            }
        except:
            pass
        
        # Capturer
        self.bot.position_detector.config = self.config
        pos = self.bot.position_detector.detect_position()
        
        # Afficher aperçu
        self.preview_image = self.bot.position_detector.get_last_capture_tk()
        if self.preview_image:
            self.preview_label.config(image=self.preview_image, text="")
        
        # Afficher résultat
        if pos:
            self.ocr_result_label.config(text=f"✅ Résultat: [{pos[0]}, {pos[1]}]", fg=THEME['success'])
            self.current_x.delete(0, 'end')
            self.current_x.insert(0, str(pos[0]))
            self.current_y.delete(0, 'end')
            self.current_y.insert(0, str(pos[1]))
        else:
            self.ocr_result_label.config(text="❌ OCR échoué - ajuste la zone", fg=THEME['accent'])
    
    def calibrate_click(self, direction):
        messagebox.showinfo("Calibration", f"OK puis clique sur le bord '{direction}' dans 3s")
        
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
        messagebox.showinfo("OK", f"✅ {len(known)} zaaps!")


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
