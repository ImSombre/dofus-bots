"""
🗡️ Dofus Combat Bot v2.0
Bot de combat automatique avec système d'apprentissage
Record & Replay - Le bot apprend en regardant ton combat !
"""

import cv2
import numpy as np
import pyautogui
import time
from PIL import ImageGrab, Image, ImageTk
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from datetime import datetime, timedelta
from pynput import mouse, keyboard as pynput_keyboard

# Keyboard pour les raccourcis
try:
    import keyboard
    HAS_KEYBOARD = True
    print("✅ Module 'keyboard' disponible")
except ImportError:
    HAS_KEYBOARD = False
    print("⚠️ Module 'keyboard' non disponible")

# Requests pour Discord
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def press_key(key):
    """Appuie sur une touche"""
    if not key:
        return
    key = str(key).strip()
    print(f"  🎹 Touche: {key}")
    
    if HAS_KEYBOARD:
        try:
            keyboard.press_and_release(key)
        except:
            pyautogui.press(key)
    else:
        pyautogui.press(key)


def send_discord(webhook_url, message):
    """Envoie une notification Discord"""
    if not webhook_url or not HAS_REQUESTS:
        return False
    try:
        data = {"username": "Dofus Combat Bot", "content": message}
        response = requests.post(webhook_url, json=data, timeout=10)
        return response.status_code == 204
    except:
        return False


# ============================================================
#                    THEME
# ============================================================
THEME = {
    'bg': '#1a1a2e',
    'bg2': '#16213e',
    'bg3': '#0f3460',
    'accent': '#e94560',
    'success': '#00d26a',
    'warning': '#ff9f1c',
    'text': '#ffffff',
    'text2': '#8b8b9e',
    'record': '#ff0000'
}


# ============================================================
#                    CONFIGURATION
# ============================================================
class Config:
    def __init__(self):
        try:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.script_dir = os.getcwd()
        
        self.config_file = os.path.join(self.script_dir, "combat_config.json")
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ Config chargée: {self.config_file}")
                return data
            except Exception as e:
                print(f"⚠️ Erreur config: {e}")
        
        # Config par défaut
        return {
            "recorded_actions": [],  # Actions enregistrées
            "combat": {
                "search_delay": 2.0,       # Délai recherche mob
                "action_delay": 0.3,       # Délai entre actions (mode rapide)
                "combat_load_delay": 2.0,  # Délai avant replay
                "use_recorded_delays": True # True=avec délais, False=rapide
            },
            "mob_templates": [],
            "hotkeys": {
                "start": "F5",
                "pause": "F6",
                "stop": "F7",
                "record": "F8"
            },
            "discord_webhook": ""
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"✅ Config sauvegardée")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False


# ============================================================
#                    ENREGISTREUR D'ACTIONS
# ============================================================
class ActionRecorder:
    """Enregistre les actions du joueur pendant un combat"""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.recording = False
        self.actions = []
        self.start_time = None
        self.mouse_listener = None
        self.keyboard_listener = None
    
    def log(self, msg):
        print(f"[REC] {msg}")
        if self.callback:
            self.callback("log", msg)
    
    def start_recording(self):
        """Démarre l'enregistrement"""
        self.recording = True
        self.actions = []
        self.start_time = time.time()
        
        self.log("🔴 ENREGISTREMENT DÉMARRÉ")
        self.log("   Fais ton combat normalement!")
        self.log("   Appuie sur F8 pour arrêter")
        
        # Listener souris
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click
        )
        self.mouse_listener.start()
        
        # Listener clavier
        self.keyboard_listener = pynput_keyboard.Listener(
            on_press=self.on_key_press
        )
        self.keyboard_listener.start()
    
    def stop_recording(self):
        """Arrête l'enregistrement"""
        self.recording = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        self.log(f"⏹️ ENREGISTREMENT TERMINÉ")
        self.log(f"   {len(self.actions)} actions enregistrées")
        
        return self.actions
    
    def on_mouse_click(self, x, y, button, pressed):
        """Capture un clic souris"""
        if not self.recording or not pressed:
            return
        
        elapsed = time.time() - self.start_time
        
        action = {
            "type": "click",
            "time": round(elapsed, 3),  # Précision milliseconde
            "x": x,
            "y": y,
            "button": "right" if button == mouse.Button.right else "left"
        }
        
        self.actions.append(action)
        btn_name = "DROIT" if action["button"] == "right" else "gauche"
        self.log(f"  🖱️ +{elapsed:.2f}s Clic {btn_name} ({x}, {y})")
    
    def on_key_press(self, key):
        """Capture une touche"""
        if not self.recording:
            return
        
        elapsed = time.time() - self.start_time
        
        # Convertir la touche en string
        try:
            key_str = key.char if hasattr(key, 'char') and key.char else str(key).replace("Key.", "")
        except:
            key_str = str(key).replace("Key.", "")
        
        # Ignorer F8 (touche d'arrêt)
        if key_str.lower() == "f8":
            return
        
        action = {
            "type": "key",
            "time": round(elapsed, 3),  # Précision milliseconde
            "key": key_str
        }
        
        self.actions.append(action)
        self.log(f"  ⌨️ +{elapsed:.2f}s Touche: {key_str}")


# ============================================================
#                    MOTEUR DE COMBAT
# ============================================================
class CombatEngine:
    def __init__(self, config, callback=None):
        self.config = config
        self.callback = callback
        self.running = False
        self.paused = False
        self.in_combat = False
        
        # Stats
        self.stats = {
            "combats": 0,
            "start_time": None
        }
        
        # Charger les templates de mobs
        self.mob_templates = self.load_mob_templates()
    
    def load_mob_templates(self):
        """Charge les templates de mobs"""
        templates = []
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        
        if not os.path.exists(mob_dir):
            os.makedirs(mob_dir)
            return templates
        
        for f in os.listdir(mob_dir):
            if f.endswith('.png'):
                path = os.path.join(mob_dir, f)
                img = cv2.imread(path)
                if img is not None:
                    templates.append(img)
                    print(f"  📦 Template mob: {f}")
        
        print(f"✅ {len(templates)} templates de mobs chargés")
        return templates
    
    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        if self.callback:
            self.callback("log", msg)
    
    def capture_screen(self):
        """Capture l'écran"""
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    def detect_mob(self, frame):
        """Détecte un mob sur l'écran"""
        if not self.mob_templates:
            return None
        
        h, w = frame.shape[:2]
        game_area = frame[int(h*0.05):int(h*0.75), :]
        
        best_match = None
        best_val = 0
        
        for template in self.mob_templates:
            try:
                result = cv2.matchTemplate(game_area, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > 0.7 and max_val > best_val:
                    best_val = max_val
                    th, tw = template.shape[:2]
                    cx = max_loc[0] + tw // 2
                    cy = max_loc[1] + th // 2 + int(h*0.05)
                    best_match = (cx, cy, max_val)
            except:
                continue
        
        return best_match
    
    def detect_combat_mode(self, frame):
        """Détecte si on est en combat"""
        h, w = frame.shape[:2]
        
        # Chercher le bouton "Auto Pass" (orange en bas à droite)
        bottom_area = frame[int(h*0.88):int(h*0.95), int(w*0.6):int(w*0.85)]
        
        if bottom_area.size > 0:
            hsv = cv2.cvtColor(bottom_area, cv2.COLOR_BGR2HSV)
            orange_mask = cv2.inRange(hsv, np.array([10, 150, 180]), np.array([25, 255, 255]))
            orange_pixels = cv2.countNonZero(orange_mask)
            
            if orange_pixels > 1500:
                return True
        
        return False
    
    def attack_mob(self, pos):
        """Attaque un mob avec CLIC DROIT"""
        self.log(f"🎯 Attaque mob à ({pos[0]}, {pos[1]}) - Clic droit")
        
        # CLIC DROIT pour attaquer
        pyautogui.click(pos[0], pos[1], button='right')
        time.sleep(0.5)
        
        # Attendre le chargement du combat
        self.log("⏳ Attente du combat...")
        time.sleep(3)
    
    def replay_actions(self):
        """Rejoue les actions enregistrées"""
        actions = self.config.data.get("recorded_actions", [])
        
        if not actions:
            self.log("⚠️ Aucune action enregistrée!")
            return
        
        use_delays = self.config.data.get("combat", {}).get("use_recorded_delays", True)
        action_delay = self.config.data.get("combat", {}).get("action_delay", 0.3)
        
        if use_delays:
            self.log(f"▶️ Replay {len(actions)} actions (AVEC délais)...")
            if actions:
                self.log(f"   Durée: {actions[-1]['time']:.1f}s")
        else:
            self.log(f"⚡ Replay {len(actions)} actions (RAPIDE)...")
        
        start_replay = time.time()
        
        for i, action in enumerate(actions):
            if not self.running or self.paused:
                break
            
            if use_delays:
                # AVEC délais - timing exact
                target_time = action["time"]
                elapsed = time.time() - start_replay
                wait_time = target_time - elapsed
                if wait_time > 0:
                    time.sleep(wait_time)
            else:
                # SANS délais - rapide
                if i > 0:
                    time.sleep(action_delay)
            
            # Exécuter l'action
            if action["type"] == "click":
                btn = action.get("button", "left")
                x, y = action["x"], action["y"]
                self.log(f"  🖱️ [{i+1}/{len(actions)}] Clic {btn} ({x}, {y})")
                pyautogui.click(x, y, button=btn)
                
            elif action["type"] == "key":
                key = action.get("key", "")
                if key:
                    self.log(f"  ⌨️ [{i+1}/{len(actions)}] Touche: {key}")
                    press_key(key)
        
        self.log(f"✅ Replay terminé ({time.time() - start_replay:.1f}s)")
    
    def handle_combat(self):
        """Gère un combat en rejouant les actions"""
        self.in_combat = True
        self.stats["combats"] += 1
        self.log(f"⚔️ Combat #{self.stats['combats']} !")
        
        # Attendre que le combat charge (configurable)
        combat_load_delay = self.config.data.get("combat", {}).get("combat_load_delay", 2.0)
        self.log(f"⏳ Chargement ({combat_load_delay}s)...")
        time.sleep(combat_load_delay)
        
        # Rejouer les actions tant qu'on est en combat
        while self.running and not self.paused:
            frame = self.capture_screen()
            
            # Vérifier si toujours en combat
            if not self.detect_combat_mode(frame):
                self.log(f"✅ Combat terminé!")
                break
            
            # Rejouer les actions
            self.replay_actions()
            
            # Petite pause avant de vérifier à nouveau
            time.sleep(1)
        
        self.in_combat = False
    
    def run(self):
        """Boucle principale"""
        self.running = True
        self.stats["start_time"] = datetime.now()
        self.log("🚀 Bot de combat démarré!")
        
        actions = self.config.data.get("recorded_actions", [])
        if not actions:
            self.log("⚠️ ATTENTION: Aucune action enregistrée!")
            self.log("   Utilise F8 pour enregistrer un combat d'abord")
        
        search_delay = self.config.data.get("combat", {}).get("search_delay", 2.0)
        
        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue
            
            try:
                frame = self.capture_screen()
                
                # Si en combat, gérer le combat
                if self.detect_combat_mode(frame):
                    self.handle_combat()
                    continue
                
                # Chercher un mob
                mob = self.detect_mob(frame)
                
                if mob:
                    self.log(f"👾 Mob trouvé! (score={mob[2]:.2f})")
                    self.attack_mob((mob[0], mob[1]))
                else:
                    time.sleep(search_delay)
                
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
                time.sleep(1)
        
        self.log("⏹️ Bot arrêté")
    
    def stop(self):
        self.running = False
    
    def pause(self):
        self.paused = not self.paused
        self.log("⏸️ Pause" if self.paused else "▶️ Reprise")


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================
class CombatGUI:
    def __init__(self):
        self.config = Config()
        self.bot = None
        self.bot_thread = None
        self.recorder = None
        self.is_recording = False
        self.colors = THEME
        
        self.setup_window()
        self.create_widgets()
        self.setup_hotkeys()
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🗡️ Dofus Combat Bot v2.0 - Record & Replay")
        self.root.geometry("850x750")
        self.root.configure(bg=self.colors['bg'])
        self.root.resizable(True, True)
    
    def create_widgets(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=self.colors['bg2'], height=90)
        header.pack(fill='x', padx=10, pady=10)
        header.pack_propagate(False)
        
        # Titre
        title_frame = tk.Frame(header, bg=self.colors['bg2'])
        title_frame.pack(side='left', padx=20, pady=10)
        
        tk.Label(title_frame, text="🗡️ Dofus Combat Bot", font=('Segoe UI', 20, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['accent']).pack(anchor='w')
        tk.Label(title_frame, text="v2.0 • Record & Replay • Apprend de tes combats!", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(anchor='w')
        
        # Status
        self.status_label = tk.Label(header, text="⚪ En attente", font=('Segoe UI', 11),
                                     bg=self.colors['bg2'], fg=self.colors['text2'])
        self.status_label.pack(side='left', padx=20)
        
        # Boutons
        btn_frame = tk.Frame(header, bg=self.colors['bg2'])
        btn_frame.pack(side='right', padx=20)
        
        # Bouton RECORD
        self.record_btn = tk.Button(btn_frame, text="🔴 ENREGISTRER", font=('Segoe UI', 10, 'bold'),
                                    bg=self.colors['record'], fg='white', width=14,
                                    command=self.toggle_recording, cursor='hand2')
        self.record_btn.pack(side='left', padx=5)
        
        self.start_btn = tk.Button(btn_frame, text="▶️ DÉMARRER", font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['success'], fg='white', width=12,
                                   command=self.start_bot, cursor='hand2')
        self.start_btn.pack(side='left', padx=5)
        
        self.pause_btn = tk.Button(btn_frame, text="⏸️ PAUSE", font=('Segoe UI', 10),
                                   bg=self.colors['warning'], fg='black', width=10,
                                   command=self.pause_bot, state='disabled', cursor='hand2')
        self.pause_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹️ STOP", font=('Segoe UI', 10),
                                  bg=self.colors['accent'], fg='white', width=8,
                                  command=self.stop_bot, state='disabled', cursor='hand2')
        self.stop_btn.pack(side='left', padx=5)
        
        # ===== MAIN CONTENT =====
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel
        left = tk.Frame(main, bg=self.colors['bg2'], width=380)
        left.pack(side='left', fill='y', padx=(0,5), pady=5)
        left.pack_propagate(False)
        
        # ===== SECTION ENREGISTREMENT =====
        tk.Label(left, text="🎬 Enregistrement", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=10)
        
        record_info = tk.Frame(left, bg=self.colors['bg3'], padx=15, pady=10)
        record_info.pack(fill='x', padx=10, pady=5)
        
        tk.Label(record_info, text="📋 Comment ça marche:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['bg3'], fg=self.colors['text']).pack(anchor='w')
        tk.Label(record_info, text="1. Clique sur 🔴 ENREGISTRER", font=('Segoe UI', 9),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(anchor='w')
        tk.Label(record_info, text="2. Lance un combat et joue normalement", font=('Segoe UI', 9),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(anchor='w')
        tk.Label(record_info, text="3. Appuie sur F8 pour arrêter", font=('Segoe UI', 9),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(anchor='w')
        tk.Label(record_info, text="4. Le bot répétera tes actions!", font=('Segoe UI', 9),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(anchor='w')
        
        # Actions enregistrées
        actions = self.config.data.get("recorded_actions", [])
        if actions:
            duration = actions[-1]["time"]
            actions_text = f"📝 {len(actions)} actions ({duration:.1f}s)"
        else:
            actions_text = "📝 Actions enregistrées: 0"
        self.actions_label = tk.Label(left, text=actions_text,
                                      font=('Segoe UI', 11), bg=self.colors['bg2'], fg=self.colors['success'])
        self.actions_label.pack(pady=10)
        
        # Boutons enregistrement
        rec_btn_frame = tk.Frame(left, bg=self.colors['bg2'])
        rec_btn_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(rec_btn_frame, text="🗑️ Effacer", font=('Segoe UI', 9),
                 bg=self.colors['bg3'], fg='white',
                 command=self.clear_recording, cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(rec_btn_frame, text="👁️ Voir actions", font=('Segoe UI', 9),
                 bg=self.colors['bg3'], fg='white',
                 command=self.view_recorded_actions, cursor='hand2').pack(side='left', padx=5)
        
        # ===== SECTION MOBS =====
        tk.Frame(left, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(left, text="👾 Mobs à attaquer", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        mob_btn_frame = tk.Frame(left, bg=self.colors['bg2'])
        mob_btn_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(mob_btn_frame, text="📸 Capturer mob", font=('Segoe UI', 10),
                 bg=self.colors['accent'], fg='white',
                 command=self.capture_mob, cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(mob_btn_frame, text="🗑️ Supprimer", font=('Segoe UI', 10),
                 bg=self.colors['bg3'], fg='white',
                 command=self.delete_mob, cursor='hand2').pack(side='left', padx=5)
        
        # Liste des mobs
        self.mob_listbox = tk.Listbox(left, bg=self.colors['bg'], fg=self.colors['text'],
                                      font=('Consolas', 10), height=4,
                                      selectbackground=self.colors['accent'])
        self.mob_listbox.pack(fill='x', padx=10, pady=5)
        self.refresh_mob_list()
        
        # ===== PARAMÈTRES =====
        tk.Frame(left, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(left, text="⚙️ Paramètres", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        param_frame = tk.Frame(left, bg=self.colors['bg2'])
        param_frame.pack(fill='x', padx=15, pady=5)
        
        # Délai recherche mob
        row1 = tk.Frame(param_frame, bg=self.colors['bg2'])
        row1.pack(fill='x', pady=2)
        tk.Label(row1, text="Recherche mob:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.search_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("search_delay", 2.0)))
        tk.Spinbox(row1, from_=0.5, to=10.0, increment=0.5, width=5,
                  textvariable=self.search_delay_var, command=self.save_params).pack(side='right')
        
        # Délai entre actions (mode rapide)
        row2 = tk.Frame(param_frame, bg=self.colors['bg2'])
        row2.pack(fill='x', pady=2)
        tk.Label(row2, text="Entre actions:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.action_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("action_delay", 0.3)))
        tk.Spinbox(row2, from_=0.1, to=2.0, increment=0.1, width=5,
                  textvariable=self.action_delay_var, command=self.save_params).pack(side='right')
        
        # Délai chargement combat
        row3 = tk.Frame(param_frame, bg=self.colors['bg2'])
        row3.pack(fill='x', pady=2)
        tk.Label(row3, text="Chargement combat:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.combat_load_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("combat_load_delay", 2.0)))
        tk.Spinbox(row3, from_=0.5, to=10.0, increment=0.5, width=5,
                  textvariable=self.combat_load_delay_var, command=self.save_params).pack(side='right')
        

        # ===== RIGHT PANEL - LOG =====
        right = tk.Frame(main, bg=self.colors['bg2'])
        right.pack(side='right', fill='both', expand=True, padx=(5,0), pady=5)
        
        # Stats
        stats_frame = tk.Frame(right, bg=self.colors['bg3'], height=80)
        stats_frame.pack(fill='x', padx=10, pady=10)
        stats_frame.pack_propagate(False)
        
        stats_inner = tk.Frame(stats_frame, bg=self.colors['bg3'])
        stats_inner.pack(expand=True)
        
        # Combat count
        tk.Label(stats_inner, text="⚔️ Combats", font=('Segoe UI', 10),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(side='left', padx=20)
        self.combat_count_label = tk.Label(stats_inner, text="0", font=('Segoe UI', 24, 'bold'),
                                           bg=self.colors['bg3'], fg=self.colors['success'])
        self.combat_count_label.pack(side='left', padx=10)
        
        # Time
        tk.Label(stats_inner, text="⏱️ Temps", font=('Segoe UI', 10),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(side='left', padx=20)
        self.time_label = tk.Label(stats_inner, text="00:00:00", font=('Segoe UI', 24, 'bold'),
                                   bg=self.colors['bg3'], fg=self.colors['warning'])
        self.time_label.pack(side='left', padx=10)
        
        # Log
        tk.Label(right, text="📝 Journal", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        self.log_text = tk.Text(right, bg=self.colors['bg'], fg=self.colors['text'],
                                font=('Consolas', 10), height=20, wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg=self.colors['bg2'], height=40)
        footer.pack(fill='x', padx=10, pady=10)
        footer.pack_propagate(False)
        
        # Raccourcis
        hotkeys = self.config.data.get("hotkeys", {})
        hotkey_text = f"▶ {hotkeys.get('start', 'F5')} | ⏸ {hotkeys.get('pause', 'F6')} | ⏹ {hotkeys.get('stop', 'F7')} | 🔴 {hotkeys.get('record', 'F8')}"
        tk.Label(footer, text=hotkey_text, font=('Segoe UI', 10),
                bg=self.colors['bg2'], fg=self.colors['accent']).pack(side='left', padx=20, pady=8)
        
        tk.Button(footer, text="⌨️ Raccourcis", font=('Segoe UI', 9),
                 bg=self.colors['bg3'], fg='white',
                 command=self.open_hotkeys_config, cursor='hand2').pack(side='right', padx=10, pady=5)
        
        # Update time
        self.update_time()
    
    def log(self, msg):
        """Ajoute un message au log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
    
    def bot_callback(self, event, data):
        """Callback du bot"""
        if event == "log":
            self.root.after(0, lambda: self.log(data))
        elif event == "combat":
            self.root.after(0, lambda: self.combat_count_label.config(text=str(data)))
    
    def toggle_recording(self):
        """Démarre/arrête l'enregistrement"""
        if not self.is_recording:
            # Démarrer l'enregistrement
            self.is_recording = True
            self.record_btn.config(text="⏹️ ARRÊTER", bg=self.colors['warning'])
            self.status_label.config(text="🔴 ENREGISTREMENT", fg=self.colors['record'])
            
            self.recorder = ActionRecorder(self.bot_callback)
            self.recorder.start_recording()
            
            self.log("🔴 Enregistrement démarré!")
            self.log("   Fais ton combat normalement")
            self.log("   Appuie sur F8 ou ce bouton pour arrêter")
        else:
            # Arrêter l'enregistrement
            self.is_recording = False
            self.record_btn.config(text="🔴 ENREGISTRER", bg=self.colors['record'])
            self.status_label.config(text="⚪ En attente", fg=self.colors['text2'])
            
            if self.recorder:
                actions = self.recorder.stop_recording()
                self.config.data["recorded_actions"] = actions
                self.config.save()
                
                # Calculer la durée totale
                if actions:
                    duration = actions[-1]["time"]
                    self.actions_label.config(text=f"📝 {len(actions)} actions ({duration:.1f}s)")
                    self.log(f"✅ {len(actions)} actions sauvegardées!")
                    self.log(f"   Durée totale: {duration:.1f} secondes")
                else:
                    self.actions_label.config(text="📝 Actions enregistrées: 0")
                    self.log("⚠️ Aucune action enregistrée")
    
    def clear_recording(self):
        """Efface l'enregistrement"""
        if messagebox.askyesno("Confirmer", "Effacer toutes les actions enregistrées?"):
            self.config.data["recorded_actions"] = []
            self.config.save()
            self.actions_label.config(text="📝 Actions enregistrées: 0")
            self.log("🗑️ Enregistrement effacé")
    
    def view_recorded_actions(self):
        """Affiche les actions enregistrées"""
        actions = self.config.data.get("recorded_actions", [])
        
        if not actions:
            messagebox.showinfo("Actions", "Aucune action enregistrée")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("👁️ Actions enregistrées")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        
        # Header
        duration = actions[-1]["time"]
        tk.Label(dialog, text=f"📝 {len(actions)} actions ({duration:.1f}s)", 
                font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=10)
        
        # Liste des actions
        frame = tk.Frame(dialog, bg=self.colors['bg2'])
        frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(frame, bg=self.colors['bg'], fg=self.colors['text'],
                            font=('Consolas', 10), yscrollcommand=scrollbar.set,
                            selectbackground=self.colors['accent'])
        listbox.pack(fill='both', expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Remplir la liste
        prev_time = 0
        for i, action in enumerate(actions):
            delay = action["time"] - prev_time
            prev_time = action["time"]
            
            if action["type"] == "click":
                btn = "DROIT" if action.get("button") == "right" else "gauche"
                text = f"{i+1}. +{delay:.2f}s 🖱️ Clic {btn} ({action['x']}, {action['y']})"
            else:
                text = f"{i+1}. +{delay:.2f}s ⌨️ Touche: {action.get('key', '?')}"
            
            listbox.insert(tk.END, text)
        
        # Bouton fermer
        tk.Button(dialog, text="Fermer", font=('Segoe UI', 10),
                 bg=self.colors['bg3'], fg='white',
                 command=dialog.destroy).pack(pady=10)
    
    def refresh_mob_list(self):
        """Rafraîchit la liste des mobs"""
        self.mob_listbox.delete(0, tk.END)
        
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        if not os.path.exists(mob_dir):
            os.makedirs(mob_dir)
            return
        
        for f in os.listdir(mob_dir):
            if f.endswith('.png'):
                self.mob_listbox.insert(tk.END, f"👾 {f}")
    
    def capture_mob(self):
        """Capture un template de mob"""
        result = messagebox.askokcancel(
            "Capture Mob",
            "📸 CAPTURE D'UN MOB\n\n"
            "1. Clique OK\n"
            "2. Tu as 3 secondes pour placer ta souris\n"
            "   sur le mob à capturer\n"
            "3. Une zone de 80x80 sera capturée"
        )
        
        if result:
            threading.Thread(target=self._do_capture_mob, daemon=True).start()
    
    def _do_capture_mob(self):
        """Effectue la capture du mob"""
        self.log("📸 Place ta souris sur le mob...")
        time.sleep(1)
        self.log("⏳ 2...")
        time.sleep(1)
        self.log("⏳ 1...")
        time.sleep(1)
        
        x, y = pyautogui.position()
        
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        size = 80
        y1 = max(0, y - size//2)
        y2 = min(frame.shape[0], y + size//2)
        x1 = max(0, x - size//2)
        x2 = min(frame.shape[1], x + size//2)
        
        template = frame[y1:y2, x1:x2]
        
        if template.size > 0:
            mob_dir = os.path.join(self.config.script_dir, "mobs")
            if not os.path.exists(mob_dir):
                os.makedirs(mob_dir)
            
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"mob_{timestamp}.png"
            filepath = os.path.join(mob_dir, filename)
            
            cv2.imwrite(filepath, template)
            self.log(f"✅ Mob capturé: {filename}")
            
            self.root.after(0, self.refresh_mob_list)
        else:
            self.log("❌ Erreur capture")
    
    def delete_mob(self):
        """Supprime un template de mob"""
        selection = self.mob_listbox.curselection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionne un mob à supprimer")
            return
        
        item = self.mob_listbox.get(selection[0])
        filename = item.replace("👾 ", "")
        
        if messagebox.askyesno("Confirmer", f"Supprimer {filename} ?"):
            filepath = os.path.join(self.config.script_dir, "mobs", filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                self.log(f"🗑️ Mob supprimé: {filename}")
                self.refresh_mob_list()
    
    def save_params(self):
        """Sauvegarde les paramètres"""
        try:
            if "combat" not in self.config.data:
                self.config.data["combat"] = {}
            self.config.data["combat"]["search_delay"] = float(self.search_delay_var.get())
            self.config.data["combat"]["action_delay"] = float(self.action_delay_var.get())
            self.config.data["combat"]["combat_load_delay"] = float(self.combat_load_delay_var.get())
            self.config.data["combat"]["use_recorded_delays"] = self.use_delays_var.get()
            self.config.save()
        except:
            pass
    
    def open_hotkeys_config(self):
        """Configure les raccourcis"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⌨️ Raccourcis")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="⌨️ Raccourcis clavier", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=10)
        
        frame = tk.Frame(dialog, bg=self.colors['bg2'], padx=20, pady=15)
        frame.pack(fill='x', padx=20, pady=10)
        
        hotkeys = self.config.data.get("hotkeys", {"start": "F5", "pause": "F6", "stop": "F7", "record": "F8"})
        
        entries = {}
        for key, label in [("start", "▶️ Démarrer"), ("pause", "⏸️ Pause"), ("stop", "⏹️ Arrêter"), ("record", "🔴 Enregistrer")]:
            row = tk.Frame(frame, bg=self.colors['bg2'])
            row.pack(fill='x', pady=3)
            tk.Label(row, text=label, width=15, anchor='w', bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
            entry = tk.Entry(row, width=10, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
            entry.insert(0, hotkeys.get(key, ""))
            entry.pack(side='right')
            entries[key] = entry
        
        def save_hotkeys():
            self.config.data["hotkeys"] = {
                "start": entries["start"].get().strip(),
                "pause": entries["pause"].get().strip(),
                "stop": entries["stop"].get().strip(),
                "record": entries["record"].get().strip()
            }
            self.config.save()
            self.setup_hotkeys()
            self.log("✅ Raccourcis sauvegardés!")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['success'], fg='white',
                 command=save_hotkeys).pack(pady=15)
    
    def setup_hotkeys(self):
        """Configure les raccourcis clavier"""
        if not HAS_KEYBOARD:
            return
        
        try:
            keyboard.unhook_all()
            hotkeys = self.config.data.get("hotkeys", {})
            
            keyboard.add_hotkey(hotkeys.get("start", "F5"), lambda: self.root.after(0, self.start_bot), suppress=False)
            keyboard.add_hotkey(hotkeys.get("pause", "F6"), lambda: self.root.after(0, self.pause_bot), suppress=False)
            keyboard.add_hotkey(hotkeys.get("stop", "F7"), lambda: self.root.after(0, self.stop_bot), suppress=False)
            keyboard.add_hotkey(hotkeys.get("record", "F8"), lambda: self.root.after(0, self.toggle_recording), suppress=False)
        except:
            pass
    
    def update_time(self):
        """Met à jour le temps"""
        if self.bot and self.bot.stats.get("start_time"):
            elapsed = datetime.now() - self.bot.stats["start_time"]
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.combat_count_label.config(text=str(self.bot.stats.get("combats", 0)))
        
        self.root.after(1000, self.update_time)
    
    def start_bot(self):
        """Démarre le bot"""
        actions = self.config.data.get("recorded_actions", [])
        if not actions:
            messagebox.showwarning("Attention", 
                "Aucune action enregistrée!\n\n"
                "1. Clique sur 🔴 ENREGISTRER\n"
                "2. Fais un combat normalement\n"
                "3. Appuie sur F8 pour arrêter\n"
                "4. Puis lance le bot")
            return
        
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        has_mobs = os.path.exists(mob_dir) and any(f.endswith('.png') for f in os.listdir(mob_dir))
        
        if not has_mobs:
            messagebox.showwarning("Attention", "Capture d'abord un mob avec 📸 Capturer mob")
            return
        
        self.log("⏳ Démarrage dans 3 secondes...")
        self.status_label.config(text="⏳ Démarrage...", fg=self.colors['warning'])
        self.start_btn.config(state='disabled')
        self.record_btn.config(state='disabled')
        
        self.root.after(3000, self._start_bot_delayed)
    
    def _start_bot_delayed(self):
        self.bot = CombatEngine(self.config, self.bot_callback)
        self.bot_thread = threading.Thread(target=self.bot.run, daemon=True)
        self.bot_thread.start()
        
        self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
        self.pause_btn.config(state='normal')
        self.stop_btn.config(state='normal')
    
    def pause_bot(self):
        """Pause/reprend"""
        if self.bot:
            self.bot.pause()
            if self.bot.paused:
                self.pause_btn.config(text="▶️ REPRENDRE")
                self.status_label.config(text="⏸️ En pause", fg=self.colors['warning'])
            else:
                self.pause_btn.config(text="⏸️ PAUSE")
                self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
    
    def stop_bot(self):
        """Arrête le bot"""
        if self.bot:
            self.bot.stop()
            self.bot = None
        
        self.status_label.config(text="⚪ Arrêté", fg=self.colors['text2'])
        self.start_btn.config(state='normal')
        self.record_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️ PAUSE")
        self.stop_btn.config(state='disabled')


# ============================================================
#                    MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("🗡️ Dofus Combat Bot v1.0")
    print("=" * 50)
    
    app = CombatGUI()
    app.run()