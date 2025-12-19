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


def send_ntfy(topic, message, image_path=None):
    """Envoie une notification Ntfy.sh avec image optionnelle"""
    if not topic:
        return False
    try:
        import urllib.request
        url = f"https://ntfy.sh/{topic}"
        
        if image_path and os.path.exists(image_path):
            # Envoyer avec image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            req = urllib.request.Request(url, data=image_data)
            req.add_header('Title', 'MP Dofus!')
            req.add_header('Tags', 'envelope,warning')
            req.add_header('Filename', 'screenshot.png')
            req.add_header('Message', message)
            urllib.request.urlopen(req, timeout=15)
        else:
            # Envoyer sans image
            data = message.encode('utf-8')
            req = urllib.request.Request(url, data=data)
            req.add_header('Title', 'Dofus Combat Bot')
            req.add_header('Tags', 'crossed_swords')
            urllib.request.urlopen(req, timeout=5)
        
        return True
    except Exception as e:
        print(f"Ntfy error: {e}")
        return False


def send_notification(config_data, message, image_path=None):
    """Envoie notification via Discord ET Ntfy"""
    config_data = config_data or {}
    
    # Discord
    webhook = config_data.get("discord_webhook", "")
    if webhook:
        send_discord(webhook, message)
    
    # Ntfy (avec image si dispo)
    topic = config_data.get("ntfy_topic", "")
    if topic:
        send_ntfy(topic, message, image_path)


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
            "recorded_actions": [],
            "combat": {
                "search_delay": 2.0,
                "action_delay": 0.3
            },
            "mob_templates": [],
            "hotkeys": {
                "start": "F5",
                "pause": "F6",
                "stop": "F7",
                "record": "F8"
            },
            "discord_webhook": "",
            "ntfy_topic": "",
            "mp_detection": True
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
    def __init__(self, callback=None):
        self.actions = []
        self.recording = False
        self.start_time = None
        self.callback = callback
        self.mouse_listener = None
        self.keyboard_listener = None
    
    def start_recording(self):
        self.actions = []
        self.recording = True
        self.start_time = time.time()
        
        # Mouse listener
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()
        
        # Keyboard listener
        self.keyboard_listener = pynput_keyboard.Listener(on_press=self.on_key)
        self.keyboard_listener.start()
        
        print("🔴 Enregistrement démarré")
    
    def stop_recording(self):
        self.recording = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        print(f"⏹️ Enregistrement arrêté: {len(self.actions)} actions")
        return self.actions
    
    def on_click(self, x, y, button, pressed):
        if not self.recording or not pressed:
            return
        
        if button == mouse.Button.left:
            elapsed = time.time() - self.start_time
            action = {
                "type": "click",
                "x": x,
                "y": y,
                "time": elapsed
            }
            self.actions.append(action)
            print(f"  📍 Clic ({x}, {y}) à {elapsed:.2f}s")
            
            if self.callback:
                self.callback("log", f"📍 Clic enregistré ({x}, {y})")
    
    def on_key(self, key):
        if not self.recording:
            return
        
        try:
            key_str = key.char if hasattr(key, 'char') and key.char else str(key).replace("Key.", "")
            elapsed = time.time() - self.start_time
            
            action = {
                "type": "key",
                "key": key_str,
                "time": elapsed
            }
            self.actions.append(action)
            print(f"  ⌨️ Touche '{key_str}' à {elapsed:.2f}s")
            
            if self.callback:
                self.callback("log", f"⌨️ Touche '{key_str}' enregistrée")
        except:
            pass


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
        
        self.stats = {
            "combats": 0,
            "start_time": None
        }
        
        self.mob_templates = self.load_mob_templates()
        self.mp_template = self.load_mp_template()
    
    def load_mob_templates(self):
        templates = []
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        
        if os.path.exists(mob_dir):
            for filename in os.listdir(mob_dir):
                if filename.endswith('.png'):
                    path = os.path.join(mob_dir, filename)
                    template = cv2.imread(path)
                    if template is not None:
                        templates.append(template)
                        print(f"✅ Mob chargé: {filename}")
        
        return templates
    
    def load_mp_template(self):
        mp_path = os.path.join(self.config.script_dir, "mp_template.png")
        if os.path.exists(mp_path):
            template = cv2.imread(mp_path)
            if template is not None:
                h, w = template.shape[:2]
                print(f"✅ Template MP chargé ({w}x{h}px)")
                return template
            else:
                print(f"❌ Template MP invalide")
        else:
            print(f"⚠️ Pas de template MP - configure 📸 MP pour détecter les MP")
        return None
    
    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        if self.callback:
            self.callback("log", msg)
    
    def capture_screen(self):
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    def detect_mp(self, frame):
        """Détecte les MP par template matching"""
        if self.mp_template is None:
            return False
        
        if not self.config.data.get("mp_detection", True):
            return False
        
        h, w = frame.shape[:2]
        
        # Zone du chat - toute la partie basse de l'écran
        chat_top = int(h * 0.4)  # Depuis 40% de l'écran
        chat_bottom = h
        chat_left = 0
        chat_right = int(w * 0.65)  # 65% de la largeur
        
        chat_area = frame[chat_top:chat_bottom, chat_left:chat_right]
        
        if chat_area.size == 0:
            return False
        
        try:
            result = cv2.matchTemplate(chat_area, self.mp_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Debug: afficher le score toutes les fois
            if max_val > 0.3:
                self.log(f"🔍 MP scan: score={max_val:.2f}")
            
            if max_val > 0.45:  # Seuil encore plus bas
                self.log(f"\n🚨🚨🚨 MP DÉTECTÉ! (score={max_val:.2f}) 🚨🚨🚨\n")
                return True
        except Exception as e:
            self.log(f"⚠️ Erreur détection MP: {e}")
        
        return False
    
    def on_mp_detected(self):
        """Appelé quand un MP est détecté"""
        self.running = False
        self.paused = True
        
        self.log("⚠️ BOT ARRÊTÉ - MP reçu!")
        
        # Prendre un screenshot automatique
        screenshot_path = None
        try:
            screenshot = ImageGrab.grab()
            screenshot_path = os.path.join(self.config.script_dir, "last_mp.png")
            screenshot.save(screenshot_path)
            self.log("📸 Screenshot sauvegardé")
        except:
            pass
        
        # Envoyer notification avec screenshot
        message = "Tu as recu un MP sur Dofus!"
        send_notification(self.config.data, message, screenshot_path)
        self.log("📱 Notification envoyee!")
        
        if self.callback:
            self.callback("mp_detected", screenshot_path)
    
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
                
                if max_val > 0.6 and max_val > best_val:
                    best_val = max_val
                    th, tw = template.shape[:2]
                    cx = max_loc[0] + tw // 2
                    cy = max_loc[1] + th // 2 + int(h * 0.05)
                    best_match = (cx, cy, max_val)
            except:
                continue
        
        return best_match
    
    def detect_combat_mode(self, frame):
        """Détecte si on est en mode combat"""
        h, w = frame.shape[:2]
        timeline_area = frame[0:int(h*0.15), int(w*0.3):int(w*0.7)]
        
        hsv = cv2.cvtColor(timeline_area, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 100, 100])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        green_pixels = cv2.countNonZero(mask)
        total_pixels = mask.shape[0] * mask.shape[1]
        ratio = green_pixels / total_pixels
        
        return ratio > 0.01
    
    def attack_mob(self, position):
        """Attaque un mob"""
        x, y = position
        self.log(f"⚔️ Attaque mob en ({x}, {y})")
        pyautogui.click(x, y)
    
    def replay_actions(self):
        """Rejoue les actions enregistrées"""
        actions = self.config.data.get("recorded_actions", [])
        if not actions:
            self.log("⚠️ Aucune action enregistrée!")
            return
        
        action_delay = self.config.data.get("combat", {}).get("action_delay", 0.3)
        
        self.log(f"🔄 Replay de {len(actions)} actions...")
        
        last_time = 0
        for action in actions:
            if not self.running or self.paused:
                break
            
            delay = action["time"] - last_time
            if delay > 0:
                time.sleep(min(delay, 2.0))
            last_time = action["time"]
            
            if action["type"] == "click":
                pyautogui.click(action["x"], action["y"])
                self.log(f"  📍 Clic ({action['x']}, {action['y']})")
            elif action["type"] == "key":
                press_key(action["key"])
            
            time.sleep(action_delay)
        
        self.log("✅ Replay terminé")
    
    def handle_combat(self):
        """Gère un combat"""
        if self.in_combat:
            return
        
        self.in_combat = True
        self.stats["combats"] += 1
        self.log(f"⚔️ Combat #{self.stats['combats']} détecté!")
        
        if self.callback:
            self.callback("combat", self.stats["combats"])
        
        time.sleep(1)
        self.replay_actions()
        
        while self.running and not self.paused:
            frame = self.capture_screen()
            if not self.detect_combat_mode(frame):
                break
            time.sleep(0.5)
        
        self.in_combat = False
        self.log("✅ Combat terminé!")
        time.sleep(2)
    
    def run(self):
        """Boucle principale"""
        self.running = True
        self.paused = False
        self.stats["start_time"] = datetime.now()
        
        self.log("🟢 Bot démarré!")
        
        # Vérifier si le template MP est chargé
        if self.mp_template is not None:
            h, w = self.mp_template.shape[:2]
            self.log(f"✅ Template MP actif ({w}x{h}px)")
        else:
            self.log("⚠️ Pas de template MP - détection MP désactivée")
        
        search_delay = self.config.data.get("combat", {}).get("search_delay", 2.0)
        mp_check_counter = 0
        
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
            
            try:
                frame = self.capture_screen()
                
                # Vérifier les MP à CHAQUE itération
                if self.detect_mp(frame):
                    self.on_mp_detected()
                    break
                
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
        
        self.log("🔴 Bot arrêté")
    
    def stop(self):
        self.running = False
        self.log("⏹️ Arrêt demandé")
    
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
        self.root.title("🗡️ Dofus Combat Bot v2.0")
        self.root.geometry("780x520")
        self.root.configure(bg=self.colors['bg'])
        self.root.resizable(True, True)
        
        # Center
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 780) // 2
        y = (self.root.winfo_screenheight() - 520) // 2
        self.root.geometry(f"780x520+{x}+{y}")
    
    def create_widgets(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=self.colors['bg2'], height=55)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # Titre
        tk.Label(header, text="🗡️ Combat Bot", font=('Segoe UI', 15, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['accent']).pack(side='left', padx=15, pady=10)
        
        self.status_label = tk.Label(header, text="⚪ En attente", font=('Segoe UI', 10),
                                     bg=self.colors['bg2'], fg=self.colors['text2'])
        self.status_label.pack(side='left', padx=10)
        
        # Boutons
        self.record_btn = tk.Button(header, text="🔴 REC", font=('Segoe UI', 9, 'bold'),
                                    bg=self.colors['record'], fg='white', width=7,
                                    command=self.toggle_recording, cursor='hand2')
        self.record_btn.pack(side='right', padx=5, pady=10)
        
        self.stop_btn = tk.Button(header, text="⏹️ STOP", font=('Segoe UI', 9),
                                  bg=self.colors['accent'], fg='white', width=7,
                                  command=self.stop_bot, state='disabled', cursor='hand2')
        self.stop_btn.pack(side='right', padx=3, pady=10)
        
        self.pause_btn = tk.Button(header, text="⏸️", font=('Segoe UI', 9),
                                   bg=self.colors['warning'], fg='black', width=4,
                                   command=self.pause_bot, state='disabled', cursor='hand2')
        self.pause_btn.pack(side='right', padx=3, pady=10)
        
        self.start_btn = tk.Button(header, text="▶️ START", font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['success'], fg='white', width=9,
                                   command=self.start_bot, cursor='hand2')
        self.start_btn.pack(side='right', padx=5, pady=10)
        
        # ===== MAIN =====
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill='both', expand=True, padx=8, pady=5)
        
        # === LEFT: Config ===
        left = tk.Frame(main, bg=self.colors['bg2'], width=270)
        left.pack(side='left', fill='y', padx=(0,5))
        left.pack_propagate(False)
        
        # Stats
        stats = tk.Frame(left, bg=self.colors['bg3'], height=45)
        stats.pack(fill='x', padx=8, pady=8)
        stats.pack_propagate(False)
        
        sf = tk.Frame(stats, bg=self.colors['bg3'])
        sf.pack(expand=True)
        tk.Label(sf, text="⚔️ Combats:", font=('Segoe UI', 10), bg=self.colors['bg3'], fg=self.colors['text']).pack(side='left')
        self.combat_count_label = tk.Label(sf, text="0", font=('Segoe UI', 14, 'bold'),
                                           bg=self.colors['bg3'], fg=self.colors['success'])
        self.combat_count_label.pack(side='left', padx=(5,15))
        tk.Label(sf, text="⏱️", font=('Segoe UI', 10), bg=self.colors['bg3'], fg=self.colors['text']).pack(side='left')
        self.time_label = tk.Label(sf, text="00:00:00", font=('Segoe UI', 12, 'bold'),
                                   bg=self.colors['bg3'], fg=self.colors['warning'])
        self.time_label.pack(side='left', padx=5)
        
        # Section Enregistrement
        tk.Label(left, text="🎬 Enregistrement", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=(8,3))
        
        actions = self.config.data.get("recorded_actions", [])
        if actions:
            actions_text = f"✅ {len(actions)} actions ({actions[-1]['time']:.1f}s)"
            actions_color = self.colors['success']
        else:
            actions_text = "❌ Aucune action enregistrée"
            actions_color = self.colors['accent']
        self.actions_label = tk.Label(left, text=actions_text, font=('Segoe UI', 9),
                                      bg=self.colors['bg2'], fg=actions_color)
        self.actions_label.pack()
        
        rec_btns = tk.Frame(left, bg=self.colors['bg2'])
        rec_btns.pack(pady=3)
        tk.Button(rec_btns, text="👁️ Voir", font=('Segoe UI', 9), bg=self.colors['bg3'], fg='white',
                 command=self.view_recorded_actions).pack(side='left', padx=2)
        tk.Button(rec_btns, text="🗑️ Effacer", font=('Segoe UI', 9), bg=self.colors['bg3'], fg='white',
                 command=self.clear_recording).pack(side='left', padx=2)
        
        # Séparateur
        tk.Frame(left, bg=self.colors['bg3'], height=1).pack(fill='x', padx=15, pady=6)
        
        # Section Mobs
        tk.Label(left, text="👾 Mobs à attaquer", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=(3,3))
        
        mob_btns = tk.Frame(left, bg=self.colors['bg2'])
        mob_btns.pack(pady=3)
        tk.Button(mob_btns, text="📸 Capturer", font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 command=self.capture_mob).pack(side='left', padx=2)
        tk.Button(mob_btns, text="🗑️ Supprimer", font=('Segoe UI', 9), bg=self.colors['bg3'], fg='white',
                 command=self.delete_mob).pack(side='left', padx=2)
        
        self.mob_listbox = tk.Listbox(left, bg=self.colors['bg'], fg=self.colors['text'],
                                      font=('Consolas', 9), height=2, selectbackground=self.colors['accent'])
        self.mob_listbox.pack(fill='x', padx=10, pady=3)
        self.refresh_mob_list()
        
        # Séparateur
        tk.Frame(left, bg=self.colors['bg3'], height=1).pack(fill='x', padx=15, pady=6)
        
        # Section Notifications
        tk.Label(left, text="📱 Notifications", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=(3,3))
        
        self.mp_detection_var = tk.BooleanVar(value=self.config.data.get("mp_detection", True))
        tk.Checkbutton(left, text="Détecter les MP", variable=self.mp_detection_var,
                      bg=self.colors['bg2'], fg=self.colors['text'], selectcolor=self.colors['bg3'],
                      command=self.toggle_mp_detection, font=('Segoe UI', 9)).pack()
        
        notif_btns = tk.Frame(left, bg=self.colors['bg2'])
        notif_btns.pack(pady=3)
        tk.Button(notif_btns, text="📸 MP", font=('Segoe UI', 9), bg=self.colors['warning'], fg='white',
                 command=self.capture_mp_template).pack(side='left', padx=2)
        tk.Button(notif_btns, text="🧪 Test", font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 command=self.test_mp_detection).pack(side='left', padx=2)
        tk.Button(notif_btns, text="📱", font=('Segoe UI', 9), bg='#5865F2', fg='white',
                 command=self.open_webhook_config).pack(side='left', padx=2)
        tk.Button(notif_btns, text="⌨️", font=('Segoe UI', 9), bg=self.colors['bg3'], fg='white',
                 command=self.open_hotkeys_config).pack(side='left', padx=2)
        
        mp_path = os.path.join(self.config.script_dir, "mp_template.png")
        mp_ok = os.path.exists(mp_path)
        notif_ok = self.config.data.get("discord_webhook") or self.config.data.get("ntfy_topic")
        status_text = f"MP: {'✅' if mp_ok else '❌'}  |  Notif: {'✅' if notif_ok else '❌'}"
        self.mp_status_label = tk.Label(left, text=status_text, font=('Segoe UI', 8),
                                        bg=self.colors['bg2'], fg=self.colors['text2'])
        self.mp_status_label.pack(pady=2)
        
        # Séparateur
        tk.Frame(left, bg=self.colors['bg3'], height=1).pack(fill='x', padx=15, pady=6)
        
        # Section Délais
        tk.Label(left, text="⚙️ Délais", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=(3,3))
        
        param_f = tk.Frame(left, bg=self.colors['bg2'])
        param_f.pack(fill='x', padx=20, pady=3)
        
        r1 = tk.Frame(param_f, bg=self.colors['bg2'])
        r1.pack(fill='x', pady=1)
        tk.Label(r1, text="Recherche mob:", font=('Segoe UI', 9), bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.search_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("search_delay", 2.0)))
        tk.Spinbox(r1, from_=0.5, to=10.0, increment=0.5, width=5, textvariable=self.search_delay_var,
                  command=self.save_params).pack(side='right')
        
        r2 = tk.Frame(param_f, bg=self.colors['bg2'])
        r2.pack(fill='x', pady=1)
        tk.Label(r2, text="Entre actions:", font=('Segoe UI', 9), bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.action_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("action_delay", 0.3)))
        tk.Spinbox(r2, from_=0.1, to=2.0, increment=0.1, width=5, textvariable=self.action_delay_var,
                  command=self.save_params).pack(side='right')
        
        # === RIGHT: Log ===
        right = tk.Frame(main, bg=self.colors['bg2'])
        right.pack(side='right', fill='both', expand=True)
        
        tk.Label(right, text="📝 Journal", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        self.log_text = tk.Text(right, bg=self.colors['bg'], fg=self.colors['text'],
                                font=('Consolas', 9), wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=8, pady=(0,8))
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg=self.colors['bg2'], height=28)
        footer.pack(fill='x')
        footer.pack_propagate(False)
        
        tk.Label(footer, text="F5: Start  |  F6: Pause  |  F7: Stop  |  F8: Record", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(pady=4)
        
        self.update_time()
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
    
    def bot_callback(self, event, data):
        if event == "log":
            self.root.after(0, lambda: self.log(data))
        elif event == "combat":
            self.root.after(0, lambda: self.combat_count_label.config(text=str(data)))
        elif event == "mp_detected":
            self.root.after(0, lambda: self.on_mp_detected(data))
    
    def on_mp_detected(self, screenshot_path=None):
        """Appelé quand un MP est détecté"""
        self.status_label.config(text="🚨 MP!", fg=self.colors['record'])
        self.start_btn.config(state='normal')
        self.record_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️")
        self.stop_btn.config(state='disabled')
        
        # Jouer un son d'alerte
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass
        
        # Afficher la popup simple
        self.show_mp_popup(screenshot_path)
    
    def show_mp_popup(self, screenshot_path=None):
        """Affiche une popup simple d'alerte MP"""
        popup = tk.Toplevel(self.root)
        popup.title("📩 MP Reçu!")
        popup.geometry("350x200")
        popup.configure(bg=self.colors['bg'])
        popup.transient(self.root)
        popup.grab_set()
        popup.attributes('-topmost', True)
        
        # Centre la popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 350) // 2
        y = (popup.winfo_screenheight() - 200) // 2
        popup.geometry(f"350x200+{x}+{y}")
        
        # Header
        tk.Label(popup, text="📩 Tu as reçu un MP!", font=('Segoe UI', 18, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=20)
        
        tk.Label(popup, text="Le bot s'est arrêté automatiquement.\nVa voir dans Dofus qui t'a écrit!", 
                font=('Segoe UI', 11), bg=self.colors['bg'], fg=self.colors['text'],
                justify='center').pack(pady=10)
        
        # Boutons
        btn_frame = tk.Frame(popup, bg=self.colors['bg'])
        btn_frame.pack(pady=20)
        
        def close_popup():
            popup.destroy()
        
        def view_screenshot():
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    os.startfile(screenshot_path)
                except:
                    try:
                        import subprocess
                        subprocess.run(['xdg-open', screenshot_path])
                    except:
                        pass
        
        tk.Button(btn_frame, text="✅ OK", font=('Segoe UI', 12, 'bold'),
                 bg=self.colors['success'], fg='white', width=10,
                 command=close_popup).pack(side='left', padx=10)
        
        if screenshot_path and os.path.exists(screenshot_path):
            tk.Button(btn_frame, text="📸 Screenshot", font=('Segoe UI', 10),
                     bg=self.colors['bg3'], fg='white', width=12,
                     command=view_screenshot).pack(side='left', padx=10)
        
        popup.bind('<Return>', lambda e: close_popup())
        popup.bind('<Escape>', lambda e: close_popup())
    
    def toggle_recording(self):
        """Démarre/arrête l'enregistrement"""
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.config(text="⏹️ STOP", bg=self.colors['warning'])
            self.status_label.config(text="🔴 ENREGISTREMENT", fg=self.colors['record'])
            
            self.recorder = ActionRecorder(self.bot_callback)
            self.recorder.start_recording()
            
            self.log("🔴 Enregistrement démarré!")
            self.log("   Fais ton combat normalement")
            self.log("   Appuie sur F8 ou ce bouton pour arrêter")
        else:
            self.is_recording = False
            self.record_btn.config(text="🔴 REC", bg=self.colors['record'])
            self.status_label.config(text="⚪ En attente", fg=self.colors['text2'])
            
            if self.recorder:
                actions = self.recorder.stop_recording()
                self.config.data["recorded_actions"] = actions
                self.config.save()
                
                if actions:
                    duration = actions[-1]["time"]
                    self.actions_label.config(
                        text=f"✅ {len(actions)} actions ({duration:.1f}s)",
                        fg=self.colors['success']
                    )
                    self.log(f"✅ {len(actions)} actions enregistrées!")
                else:
                    self.log("⚠️ Aucune action enregistrée")
    
    def view_recorded_actions(self):
        """Affiche les actions enregistrées"""
        actions = self.config.data.get("recorded_actions", [])
        if not actions:
            messagebox.showinfo("Actions", "Aucune action enregistrée")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title("👁️ Actions enregistrées")
        popup.geometry("400x300")
        popup.configure(bg=self.colors['bg'])
        
        text = tk.Text(popup, bg=self.colors['bg2'], fg=self.colors['text'], font=('Consolas', 9))
        text.pack(fill='both', expand=True, padx=10, pady=10)
        
        for i, action in enumerate(actions):
            if action["type"] == "click":
                text.insert('end', f"{i+1}. 📍 Clic ({action['x']}, {action['y']}) @ {action['time']:.2f}s\n")
            else:
                text.insert('end', f"{i+1}. ⌨️ Touche '{action['key']}' @ {action['time']:.2f}s\n")
    
    def clear_recording(self):
        """Efface l'enregistrement"""
        if messagebox.askyesno("Confirmer", "Effacer toutes les actions enregistrées?"):
            self.config.data["recorded_actions"] = []
            self.config.save()
            self.actions_label.config(text="❌ Aucune action enregistrée", fg=self.colors['accent'])
            self.log("🗑️ Actions effacées")
    
    def refresh_mob_list(self):
        """Rafraîchit la liste des mobs"""
        self.mob_listbox.delete(0, 'end')
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        
        if os.path.exists(mob_dir):
            for filename in os.listdir(mob_dir):
                if filename.endswith('.png'):
                    self.mob_listbox.insert('end', f"  👾 {filename}")
    
    def capture_mob(self):
        """Capture un mob"""
        result = messagebox.askokcancel("Capture Mob",
            "📸 CAPTURE D'UN MOB\n\n"
            "1. Clique OK\n"
            "2. Tu as 3 secondes\n"
            "3. Survole le mob avec ta souris\n"
            "4. Ne bouge plus!")
        
        if result:
            threading.Thread(target=self._do_capture_mob, daemon=True).start()
    
    def _do_capture_mob(self):
        self.log("📸 Survole le mob...")
        time.sleep(1)
        self.log("⏳ 2...")
        time.sleep(1)
        self.log("⏳ 1...")
        time.sleep(1)
        
        x, y = pyautogui.position()
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        region_size = 60
        y1 = max(0, y - region_size)
        y2 = min(frame.shape[0], y + region_size)
        x1 = max(0, x - region_size)
        x2 = min(frame.shape[1], x + region_size)
        
        template = frame[y1:y2, x1:x2]
        
        if template.size > 0:
            mob_dir = os.path.join(self.config.script_dir, "mobs")
            os.makedirs(mob_dir, exist_ok=True)
            
            filename = f"mob_{datetime.now().strftime('%H%M%S')}.png"
            path = os.path.join(mob_dir, filename)
            cv2.imwrite(path, template)
            
            self.log(f"✅ Mob sauvegardé: {filename}")
            self.root.after(0, self.refresh_mob_list)
    
    def delete_mob(self):
        """Supprime un mob"""
        selection = self.mob_listbox.curselection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionne un mob à supprimer")
            return
        
        item = self.mob_listbox.get(selection[0])
        filename = item.strip().replace("👾 ", "")
        
        if messagebox.askyesno("Confirmer", f"Supprimer {filename}?"):
            path = os.path.join(self.config.script_dir, "mobs", filename)
            if os.path.exists(path):
                os.remove(path)
                self.log(f"🗑️ {filename} supprimé")
                self.refresh_mob_list()
    
    def save_params(self):
        """Sauvegarde les paramètres"""
        try:
            self.config.data["combat"]["search_delay"] = float(self.search_delay_var.get())
            self.config.data["combat"]["action_delay"] = float(self.action_delay_var.get())
            self.config.save()
        except:
            pass
    
    def toggle_mp_detection(self):
        self.config.data["mp_detection"] = self.mp_detection_var.get()
        self.config.save()
        status = "activée" if self.mp_detection_var.get() else "désactivée"
        self.log(f"💬 Détection MP {status}")
    
    def test_mp_detection(self):
        """Teste la détection MP en temps réel"""
        mp_path = os.path.join(self.config.script_dir, "mp_template.png")
        
        if not os.path.exists(mp_path):
            messagebox.showwarning("Attention", "Capture d'abord un template MP avec 📸 MP")
            return
        
        template = cv2.imread(mp_path)
        if template is None:
            messagebox.showerror("Erreur", "Template MP invalide")
            return
        
        self.log("🧪 Test détection MP...")
        self.log("   Assure-toi d'avoir un MP visible dans le chat!")
        
        # Capturer l'écran
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        h, w = frame.shape[:2]
        th, tw = template.shape[:2]
        
        # Zone de recherche
        chat_top = int(h * 0.4)
        chat_bottom = h
        chat_left = 0
        chat_right = int(w * 0.65)
        
        chat_area = frame[chat_top:chat_bottom, chat_left:chat_right]
        
        try:
            result = cv2.matchTemplate(chat_area, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            self.log(f"📊 Score de détection: {max_val:.3f}")
            self.log(f"   Template: {tw}x{th}px")
            self.log(f"   Zone recherche: {chat_right}x{chat_bottom-chat_top}px")
            
            if max_val > 0.45:
                self.log(f"✅ MP DÉTECTÉ! Le bot s'arrêterait.")
                messagebox.showinfo("Test MP", f"✅ MP détecté!\nScore: {max_val:.3f}\n\nLe bot s'arrêterait si il tournait.")
            elif max_val > 0.3:
                self.log(f"⚠️ Détection faible. Recapture le template.")
                messagebox.showwarning("Test MP", f"⚠️ Détection faible\nScore: {max_val:.3f}\n\nRecapture le template MP\nen ciblant mieux le texte 'de'")
            else:
                self.log(f"❌ Pas de MP détecté (score trop bas)")
                messagebox.showinfo("Test MP", f"❌ Pas de MP détecté\nScore: {max_val:.3f}\n\n1. Vérifie qu'un MP est visible\n2. Recapture le template")
        except Exception as e:
            self.log(f"❌ Erreur test: {e}")
            messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def update_mp_status(self):
        """Met à jour le statut MP"""
        mp_path = os.path.join(self.config.script_dir, "mp_template.png")
        mp_ok = os.path.exists(mp_path)
        notif_ok = self.config.data.get("discord_webhook") or self.config.data.get("ntfy_topic")
        status_text = f"MP: {'✅' if mp_ok else '❌'}  |  Notif: {'✅' if notif_ok else '❌'}"
        self.root.after(0, lambda: self.mp_status_label.config(text=status_text))
    
    def capture_mp_template(self):
        """Capture le template MP"""
        result = messagebox.askokcancel(
            "Capture MP",
            "📸 CAPTURE DU TEXTE MP\n\n"
            "⚠️ IMPORTANT: Capture UNIQUEMENT\n"
            "le petit texte cyan 'de' au début du MP!\n\n"
            "1. Reçois un MP (visible dans le chat)\n"
            "2. Clique OK\n"
            "3. Place ta souris EXACTEMENT sur le 'de'\n"
            "   (le texte cyan avant le pseudo)\n"
            "4. Attends 3 secondes, ne bouge plus!\n\n"
            "💡 Plus la zone est petite et unique,\n"
            "   mieux ça détecte!"
        )
        
        if result:
            threading.Thread(target=self._do_capture_mp, daemon=True).start()
    
    def _do_capture_mp(self):
        """Effectue la capture du template MP"""
        self.log("📸 Place ta souris sur le 'de' cyan...")
        time.sleep(1)
        self.log("⏳ 2... Ne bouge plus!")
        time.sleep(1)
        self.log("⏳ 1...")
        time.sleep(1)
        
        x, y = pyautogui.position()
        
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Zone PETITE: juste "de" (environ 25x20 pixels)
        region_w, region_h = 40, 20
        y1 = max(0, y - 5)
        y2 = min(frame.shape[0], y + region_h)
        x1 = max(0, x - 5)
        x2 = min(frame.shape[1], x + region_w)
        
        template = frame[y1:y2, x1:x2]
        
        if template.size > 0:
            template_path = os.path.join(self.config.script_dir, "mp_template.png")
            cv2.imwrite(template_path, template)
            h, w = template.shape[:2]
            self.log(f"✅ Template MP sauvegardé! ({w}x{h}px)")
            self.log(f"💡 Relance le bot pour charger le nouveau template")
            
            self.update_mp_status()
        else:
            self.log("❌ Erreur capture")
    
    def open_webhook_config(self):
        """Configure les notifications (Discord + Ntfy)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📱 Configuration Notifications")
        dialog.geometry("500x350")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="📱 Notifications Push", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=10)
        
        # === NTFY ===
        ntfy_frame = tk.LabelFrame(dialog, text="📲 Ntfy.sh (gratuit & recommandé)", 
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['bg2'], fg=self.colors['text'], padx=15, pady=10)
        ntfy_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(ntfy_frame, text="Topic:", bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        ntfy_entry = tk.Entry(ntfy_frame, width=40, bg=self.colors['bg3'], fg=self.colors['text'],
                             insertbackground=self.colors['text'])
        ntfy_entry.insert(0, self.config.data.get("ntfy_topic", ""))
        ntfy_entry.pack(fill='x', pady=5)
        
        tk.Label(ntfy_frame, text="1. Installe l'app ntfy sur ton tel\n2. Abonne-toi au même topic\n3. Screenshot envoyé automatiquement!",
                font=('Segoe UI', 8), bg=self.colors['bg2'], fg=self.colors['text2'], justify='left').pack(anchor='w')
        
        # === Discord ===
        discord_frame = tk.LabelFrame(dialog, text="💬 Discord Webhook (optionnel)", 
                                      font=('Segoe UI', 10, 'bold'),
                                      bg=self.colors['bg2'], fg=self.colors['text'], padx=15, pady=10)
        discord_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(discord_frame, text="URL Webhook:", bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        url_entry = tk.Entry(discord_frame, width=50, bg=self.colors['bg3'], fg=self.colors['text'],
                            insertbackground=self.colors['text'])
        url_entry.insert(0, self.config.data.get("discord_webhook", ""))
        url_entry.pack(fill='x', pady=5)
        
        def test_ntfy():
            topic = ntfy_entry.get().strip()
            if topic:
                success = send_ntfy(topic, "Test Dofus Combat Bot - Ca marche!")
                if success:
                    messagebox.showinfo("Succès", "Notification envoyée!")
                else:
                    messagebox.showerror("Erreur", "Échec. Vérifie le topic.")
            else:
                messagebox.showwarning("Attention", "Entre un topic!")
        
        def test_discord():
            url = url_entry.get().strip()
            if url:
                success = send_discord(url, "🧪 **Test Dofus Combat Bot**\n\nLe webhook fonctionne!")
                if success:
                    messagebox.showinfo("Succès", "Message envoyé!")
                else:
                    messagebox.showerror("Erreur", "Échec. Vérifie l'URL.")
            else:
                messagebox.showwarning("Attention", "Entre une URL!")
        
        def save_config():
            self.config.data["ntfy_topic"] = ntfy_entry.get().strip()
            self.config.data["discord_webhook"] = url_entry.get().strip()
            self.config.save()
            
            self.update_mp_status()
            self.log("✅ Notifications sauvegardées!")
            dialog.destroy()
        
        # Boutons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        tk.Button(btn_frame, text="🧪 Test Ntfy", font=('Segoe UI', 10),
                 bg='#ff9f1c', fg='white', width=12,
                 command=test_ntfy).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="🧪 Test Discord", font=('Segoe UI', 10),
                 bg='#5865F2', fg='white', width=12,
                 command=test_discord).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['success'], fg='white', width=15,
                 command=save_config).pack(side='right', padx=5)
    
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
                "1. Clique sur REC\n"
                "2. Fais un combat\n"
                "3. Appuie F8 pour arrêter\n"
                "4. Lance le bot")
            return
        
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        has_mobs = os.path.exists(mob_dir) and any(f.endswith('.png') for f in os.listdir(mob_dir))
        
        if not has_mobs:
            messagebox.showwarning("Attention", "Capture d'abord un mob avec 📸 Capturer")
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
                self.pause_btn.config(text="▶️")
                self.status_label.config(text="⏸️ Pause", fg=self.colors['warning'])
            else:
                self.pause_btn.config(text="⏸️")
                self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
    
    def stop_bot(self):
        """Arrête le bot"""
        if self.bot:
            self.bot.stop()
            self.bot = None
        
        self.status_label.config(text="⚪ Arrêté", fg=self.colors['text2'])
        self.start_btn.config(state='normal')
        self.record_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️")
        self.stop_btn.config(state='disabled')


# ============================================================
#                    MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("🗡️ Dofus Combat Bot v2.0")
    print("=" * 50)
    
    app = CombatGUI()
    app.run()