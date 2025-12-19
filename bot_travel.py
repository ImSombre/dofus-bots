"""
🗺️ Dofus Retro Travel Bot v3.2
Bot de déplacement automatique
- OCR pour lire les coordonnées (optionnel)
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
import re
import webbrowser

try:
    import pyautogui
    import keyboard
    from PIL import ImageGrab, Image, ImageTk
    import numpy as np
    import cv2
    HAS_DEPS = True
except ImportError as e:
    print(f"Import error: {e}")
    HAS_DEPS = False

# OCR
HAS_OCR = False
TESSERACT_PATH = None

try:
    import pytesseract
    # Chercher Tesseract sur Windows
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            TESSERACT_PATH = path
            HAS_OCR = True
            break
    
    if not TESSERACT_PATH:
        # Essayer quand même (peut être dans le PATH)
        try:
            pytesseract.get_tesseract_version()
            HAS_OCR = True
        except:
            pass
            
except ImportError:
    pass


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
#                    WORLD MAP
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
    def find_nearest_zaap(cls, x, y, known):
        nearest, min_dist = None, float('inf')
        for name in known:
            if name in cls.ZAAPS:
                zx, zy = cls.ZAAPS[name]
                dist = abs(x-zx) + abs(y-zy)
                if dist < min_dist:
                    min_dist, nearest = dist, (name, zx, zy)
        return nearest, min_dist
    
    @classmethod
    def is_on_zaap(cls, x, y, known):
        for name in known:
            if name in cls.ZAAPS and cls.ZAAPS[name] == (x, y):
                return name
        return None


# ============================================================
#                    OCR
# ============================================================

class PositionDetector:
    def __init__(self, config):
        self.config = config
        self.last_capture = None
    
    def capture_region(self):
        r = self.config.data.get("coords_region", {})
        x, y = r.get("x", 232), r.get("y", 78)
        w, h = r.get("width", 160), r.get("height", 25)
        self.last_capture = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        return self.last_capture
    
    def detect_position(self):
        if not HAS_OCR:
            return None
        
        try:
            img = self.capture_region()
            img_np = np.array(img)
            
            # Prétraitement
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # OCR
            text = pytesseract.image_to_string(thresh, 
                config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789-,.')
            text = text.strip().replace(' ', '').replace('.', ',')
            
            # Parser
            match = re.search(r'(-?\d+)[,;:\s]+(-?\d+)', text)
            if match:
                return (int(match.group(1)), int(match.group(2)))
            
            numbers = re.findall(r'-?\d+', text)
            if len(numbers) >= 2:
                return (int(numbers[0]), int(numbers[1]))
                
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None
    
    def get_capture_tk(self, max_size=300):
        if not self.last_capture:
            return None
        img = self.last_capture.copy()
        w, h = img.size
        scale = min(max_size/w, max_size/h, 3)
        img = img.resize((int(w*scale), int(h*scale)), Image.NEAREST)
        return ImageTk.PhotoImage(img)


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
                    for dest in self.known_zaaps:
                        if dest != zaap and dest in WorldMap.ZAAPS:
                            pos = WorldMap.ZAAPS[dest]
                            if pos in closed:
                                continue
                            g = g_scores.get(current, float('inf')) + 2
                            if g < g_scores.get(pos, float('inf')):
                                g_scores[pos] = g
                                f = g + abs(goal[0]-pos[0]) + abs(goal[1]-pos[1])
                                counter += 1
                                heapq.heappush(open_set, (f, counter, pos, path + [(f"zaap:{dest}", pos)]))
        
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
        
        self.detector = PositionDetector(config)
        self.pathfinder = Pathfinder(
            use_zaaps=config.data.get("use_zaaps", True),
            known_zaaps=config.data.get("known_zaaps", [])
        )
    
    def detect_position(self):
        pos = self.detector.detect_position()
        if pos:
            self.current_pos = pos
            self.log(f"📍 Position: [{pos[0]}, {pos[1]}]")
        else:
            self.log("⚠️ OCR échoué")
        return pos
    
    def set_position(self, x, y):
        self.current_pos = (x, y)
        self.log(f"📍 Position: [{x}, {y}]")
    
    def calculate_path(self, tx, ty):
        if not self.current_pos:
            self.log("❌ Position inconnue!")
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
        self.log("❌ Pas de chemin!")
        return None
    
    def click_direction(self, d):
        pos = self.config.data.get("click_positions", {}).get(d)
        if pos:
            pyautogui.click(pos["x"], pos["y"])
            return True
        return False
    
    def use_zaap(self, dest):
        self.log(f"🌀 Zaap → {dest}")
        zaap = self.config.data.get("zaap_click", {"x": 600, "y": 400})
        pyautogui.click(zaap["x"], zaap["y"])
        time.sleep(1)
        
        menu = {"Astrub": (500, 280), "Amakna Village": (500, 300), "Bonta": (500, 320)}
        if dest in menu:
            pyautogui.doubleClick(*menu[dest])
        
        time.sleep(self.config.data.get("zaap_delay", 2.5))
        return True
    
    def execute_move(self, move, target):
        if str(move).startswith("zaap:"):
            self.use_zaap(move.split(":")[1])
            self.current_pos = target
            return True
        else:
            icons = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            self.log(f"🚶 {icons.get(move, '?')} [{target[0]},{target[1]}]")
            if self.click_direction(move):
                time.sleep(self.config.data.get("move_delay", 1.5))
                self.current_pos = target
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
        self.log(f"🚀 Go! {total} étapes")
        
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
        self.bot = TravelBot(self.config, self.log)
        self.preview_image = None
        
        self.setup_window()
        self.create_widgets()
        self.setup_hotkeys()
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🗺️ Dofus Travel Bot v3.2")
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
        tk.Label(header, text="🗺️ DOFUS TRAVEL BOT v3.2", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(pady=15)
        
        # Tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.create_navigation_tab(notebook)
        self.create_calibration_tab(notebook)
        self.create_zaaps_tab(notebook)
        
        # Status
        tk.Label(self.root, text="F5=Go • F6=Pause • F7=Stop • F8=Détecter",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(fill='x', pady=3)
    
    def create_navigation_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🗺️ Navigation")
        
        # Position
        frame = tk.LabelFrame(tab, text="📍 Position Actuelle", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.current_x = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.current_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.current_y = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.current_y.pack(side='left', padx=5)
        
        tk.Button(row, text="📍 Définir", bg=THEME['accent2'], fg='white',
                 command=self.set_position).pack(side='left', padx=10)
        
        if HAS_OCR:
            tk.Button(row, text="🔍 Détecter (F8)", bg=THEME['success'], fg='white',
                     command=self.detect_position).pack(side='left')
        
        # Destination
        frame = tk.LabelFrame(tab, text="🎯 Destination", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x')
        
        tk.Label(row, text="X:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.dest_x = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.dest_x.pack(side='left', padx=5)
        
        tk.Label(row, text="Y:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.dest_y = tk.Entry(row, width=7, font=('Segoe UI', 12), bg=THEME['bg3'], fg=THEME['text'])
        self.dest_y.pack(side='left', padx=5)
        
        tk.Label(frame, text="─── OU Zaap ───", bg=THEME['bg2'], fg=THEME['text2']).pack(pady=5)
        
        self.zaap_var = tk.StringVar()
        combo = ttk.Combobox(frame, textvariable=self.zaap_var, width=30,
                            values=WorldMap.get_zaap_list(), state='readonly')
        combo.pack()
        combo.bind('<<ComboboxSelected>>', self.on_zaap_selected)
        
        # Options
        frame = tk.LabelFrame(tab, text="⚙️ Options", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        self.use_zaaps_var = tk.BooleanVar(value=self.config.data.get("use_zaaps", True))
        tk.Checkbutton(frame, text="🌀 Utiliser Zaaps", variable=self.use_zaaps_var,
                      bg=THEME['bg2'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(anchor='w')
        
        row = tk.Frame(frame, bg=THEME['bg2'])
        row.pack(fill='x', pady=5)
        tk.Label(row, text="Délai:", bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        self.delay_var = tk.StringVar(value=str(self.config.data.get("move_delay", 1.5)))
        tk.Spinbox(row, from_=0.5, to=5.0, increment=0.1, width=5,
                  textvariable=self.delay_var).pack(side='left', padx=5)
        
        # Boutons
        frame = tk.Frame(tab, bg=THEME['bg'])
        frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(frame, text="🔍 CALCULER", font=('Segoe UI', 12, 'bold'),
                 bg=THEME['accent2'], fg='white', width=20,
                 command=self.calculate_path).pack(pady=5)
        
        row = tk.Frame(frame, bg=THEME['bg'])
        row.pack()
        tk.Button(row, text="▶️ GO (F5)", font=('Segoe UI', 11, 'bold'),
                 bg=THEME['success'], fg='white', width=12,
                 command=self.start_travel).pack(side='left', padx=3)
        tk.Button(row, text="⏸️ Pause", bg=THEME['warning'], fg='white', width=10,
                 command=self.pause_travel).pack(side='left', padx=3)
        tk.Button(row, text="⏹️ Stop", bg=THEME['accent'], fg='white', width=10,
                 command=self.stop_travel).pack(side='left', padx=3)
        
        # Chemin
        frame = tk.LabelFrame(tab, text="📋 Chemin", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        frame.pack(fill='x', padx=10, pady=5)
        self.path_text = tk.Text(frame, height=5, font=('Consolas', 9),
                                 bg=THEME['bg3'], fg=THEME['text'])
        self.path_text.pack(fill='x')
        
        # Log
        frame = tk.LabelFrame(tab, text="📜 Log", font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=10, pady=5)
        frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.log_text = tk.Text(frame, height=8, font=('Consolas', 9),
                                bg=THEME['bg3'], fg=THEME['text'])
        self.log_text.pack(fill='both', expand=True)
        
        self.log("🗺️ Travel Bot v3.2")
        if HAS_OCR:
            self.log("✅ OCR disponible")
        else:
            self.log("⚠️ OCR non disponible")
            self.log("   → Entre ta position manuellement")
    
    def create_calibration_tab(self, notebook):
        tab = tk.Frame(notebook, bg=THEME['bg'])
        notebook.add(tab, text="🎯 Calibration")
        
        # === OCR SECTION ===
        frame = tk.LabelFrame(tab, text="📍 OCR - Lecture des coordonnées", 
                              font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        if not HAS_OCR:
            # Instructions pour installer Tesseract
            tk.Label(frame, text="⚠️ Tesseract OCR n'est pas installé", 
                    font=('Segoe UI', 11, 'bold'),
                    bg=THEME['bg2'], fg=THEME['warning']).pack(pady=5)
            
            tk.Label(frame, text="Pour activer la détection automatique des coordonnées:",
                    bg=THEME['bg2'], fg=THEME['text']).pack(anchor='w')
            
            instructions = tk.Frame(frame, bg=THEME['bg3'], padx=10, pady=10)
            instructions.pack(fill='x', pady=10)
            
            tk.Label(instructions, text="1. Télécharge Tesseract OCR:", 
                    bg=THEME['bg3'], fg=THEME['text']).pack(anchor='w')
            
            tk.Button(instructions, text="📥 Télécharger Tesseract", 
                     bg=THEME['accent2'], fg='white',
                     command=lambda: webbrowser.open(
                         "https://github.com/UB-Mannheim/tesseract/wiki")).pack(pady=5)
            
            tk.Label(instructions, text="2. Installe-le (garde le chemin par défaut)",
                    bg=THEME['bg3'], fg=THEME['text']).pack(anchor='w')
            
            tk.Label(instructions, text="3. Relance le Travel Bot",
                    bg=THEME['bg3'], fg=THEME['text']).pack(anchor='w')
            
            tk.Label(frame, text="💡 En attendant, entre ta position manuellement\n"
                                "   (regarde en haut à gauche dans Dofus)",
                    bg=THEME['bg2'], fg=THEME['text2']).pack(pady=10)
        else:
            # Zone OCR
            tk.Label(frame, text="✅ Tesseract OCR installé!", 
                    font=('Segoe UI', 10, 'bold'),
                    bg=THEME['bg2'], fg=THEME['success']).pack()
            
            row = tk.Frame(frame, bg=THEME['bg2'])
            row.pack(fill='x', pady=5)
            
            region = self.config.data.get("coords_region", {})
            
            for label, key, default in [("X:", "x", 232), ("Y:", "y", 78), 
                                         ("L:", "width", 160), ("H:", "height", 25)]:
                tk.Label(row, text=label, bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
                entry = tk.Entry(row, width=5, bg=THEME['bg3'], fg=THEME['text'])
                entry.insert(0, str(region.get(key, default)))
                entry.pack(side='left', padx=3)
                setattr(self, f"ocr_{key}", entry)
            
            tk.Button(frame, text="🧪 Tester OCR", bg=THEME['accent2'], fg='white',
                     command=self.test_ocr).pack(pady=5)
            
            # Aperçu
            self.preview_label = tk.Label(frame, bg=THEME['bg3'], text="(tester pour voir)")
            self.preview_label.pack(pady=5)
            
            self.ocr_result = tk.Label(frame, text="", font=('Segoe UI', 11, 'bold'),
                                       bg=THEME['bg2'], fg=THEME['success'])
            self.ocr_result.pack()
        
        # === CLICS ===
        frame = tk.LabelFrame(tab, text="🖱️ Clics changement de map",
                              font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        self.click_entries = {}
        for d, label in [("up", "↑ Haut"), ("down", "↓ Bas"), ("left", "← Gauche"), ("right", "→ Droite")]:
            row = tk.Frame(frame, bg=THEME['bg2'])
            row.pack(fill='x', pady=2)
            
            tk.Label(row, text=f"{label}:", width=10, anchor='w',
                    bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
            
            pos = self.config.data.get("click_positions", {}).get(d, {"x": 0, "y": 0})
            
            x_e = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
            x_e.insert(0, str(pos["x"]))
            x_e.pack(side='left', padx=2)
            
            y_e = tk.Entry(row, width=6, bg=THEME['bg3'], fg=THEME['text'])
            y_e.insert(0, str(pos["y"]))
            y_e.pack(side='left', padx=2)
            
            self.click_entries[d] = (x_e, y_e)
            
            tk.Button(row, text="🎯", bg=THEME['card'], fg=THEME['text'],
                     command=lambda d=d: self.calibrate_click(d)).pack(side='left', padx=5)
        
        # === ZAAP ===
        frame = tk.LabelFrame(tab, text="🌀 Zaap",
                              font=('Segoe UI', 10, 'bold'),
                              bg=THEME['bg2'], fg=THEME['text'], padx=15, pady=10)
        frame.pack(fill='x', padx=10, pady=5)
        
        row = tk.Frame(frame, bg=THEME['bg2'])
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
        
        # SAVE
        tk.Button(tab, text="💾 SAUVEGARDER", font=('Segoe UI', 11, 'bold'),
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
            
            f = tk.Frame(scroll_frame, bg=THEME['bg2'])
            f.pack(fill='x', padx=10, pady=2)
            
            tk.Checkbutton(f, text=name, variable=var, bg=THEME['bg2'],
                          fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left')
            tk.Label(f, text=f"[{x}, {y}]", font=('Consolas', 9),
                    bg=THEME['bg2'], fg=THEME['text2']).pack(side='right')
        
        row = tk.Frame(tab, bg=THEME['bg'])
        row.pack(pady=10)
        tk.Button(row, text="✅ Tout", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(True) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(row, text="❌ Rien", bg=THEME['card'], fg=THEME['text'],
                 command=lambda: [v.set(False) for v in self.zaap_vars.values()]).pack(side='left', padx=5)
        tk.Button(row, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 command=self.save_zaaps).pack(side='left', padx=10)
    
    # ===== METHODS =====
    
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.root.after(0, lambda: self._log(f"[{ts}] {msg}"))
    
    def _log(self, msg):
        self.log_text.insert('end', msg + "\n")
        self.log_text.see('end')
    
    def detect_position(self):
        if not HAS_OCR:
            messagebox.showinfo("OCR", "Tesseract OCR n'est pas installé.\n\n"
                               "Va dans l'onglet Calibration pour voir comment l'installer,\n"
                               "ou entre ta position manuellement.")
            return
        
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
        pos = WorldMap.get_zaap_pos(self.zaap_var.get())
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
            arrows = {"right": "→", "left": "←", "up": "↑", "down": "↓"}
            self.path_text.insert('end', f"[{cx},{cy}] → [{dx},{dy}] = {len(path)} étapes\n\n")
            for i, (m, p) in enumerate(path):
                if str(m).startswith("zaap:"):
                    self.path_text.insert('end', f"{i+1}. 🌀 {m.split(':')[1]}\n")
                else:
                    self.path_text.insert('end', f"{i+1}. {arrows.get(m,'?')} [{p[0]},{p[1]}]\n")
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
        if not HAS_OCR:
            return
        
        try:
            self.config.data["coords_region"] = {
                "x": int(self.ocr_x.get()), "y": int(self.ocr_y.get()),
                "width": int(self.ocr_width.get()), "height": int(self.ocr_height.get())
            }
        except:
            pass
        
        pos = self.bot.detector.detect_position()
        
        self.preview_image = self.bot.detector.get_capture_tk()
        if self.preview_image:
            self.preview_label.config(image=self.preview_image, text="")
        
        if pos:
            self.ocr_result.config(text=f"✅ [{pos[0]}, {pos[1]}]", fg=THEME['success'])
            self.current_x.delete(0, 'end')
            self.current_x.insert(0, str(pos[0]))
            self.current_y.delete(0, 'end')
            self.current_y.insert(0, str(pos[1]))
        else:
            self.ocr_result.config(text="❌ OCR échoué - ajuste la zone", fg=THEME['accent'])
    
    def calibrate_click(self, d):
        messagebox.showinfo("Calibration", f"OK puis clique sur '{d}' dans 3s")
        
        def do():
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            self.click_entries[d][0].delete(0, 'end')
            self.click_entries[d][0].insert(0, str(x))
            self.click_entries[d][1].delete(0, 'end')
            self.click_entries[d][1].insert(0, str(y))
            self.log(f"✅ {d}: {x}, {y}")
        
        threading.Thread(target=do, daemon=True).start()
    
    def calibrate_zaap(self):
        messagebox.showinfo("Calibration", "OK puis clique sur le zaap dans 3s")
        
        def do():
            for i in range(3, 0, -1):
                self.log(f"   {i}...")
                time.sleep(1)
            x, y = pyautogui.position()
            self.zaap_x.delete(0, 'end')
            self.zaap_x.insert(0, str(x))
            self.zaap_y.delete(0, 'end')
            self.zaap_y.insert(0, str(y))
            self.log(f"✅ Zaap: {x}, {y}")
        
        threading.Thread(target=do, daemon=True).start()
    
    def save_calibration(self):
        try:
            if HAS_OCR:
                self.config.data["coords_region"] = {
                    "x": int(self.ocr_x.get()), "y": int(self.ocr_y.get()),
                    "width": int(self.ocr_width.get()), "height": int(self.ocr_height.get())
                }
            
            for d, (x_e, y_e) in self.click_entries.items():
                self.config.data["click_positions"][d] = {"x": int(x_e.get()), "y": int(y_e.get())}
            
            self.config.data["zaap_click"] = {"x": int(self.zaap_x.get()), "y": int(self.zaap_y.get())}
            
            self.config.save()
            messagebox.showinfo("OK", "✅ Sauvegardé!")
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
