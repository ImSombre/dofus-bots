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


def send_ntfy(topic, message):
    """Envoie une notification Ntfy.sh"""
    if not topic:
        return False
    try:
        import urllib.request
        url = f"https://ntfy.sh/{topic}"
        data = message.encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Title', 'Dofus Combat Bot')
        req.add_header('Tags', 'envelope,warning')
        req.add_header('Priority', 'high')
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"Ntfy error: {e}")
        return False


def send_notification(config_data, message):
    """Envoie notification via Discord ET Ntfy"""
    config_data = config_data or {}
    
    webhook = config_data.get("discord_webhook", "")
    if webhook:
        send_discord(webhook, message)
    
    topic = config_data.get("ntfy_topic", "")
    if topic:
        send_ntfy(topic, message)


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
        
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()
        
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
            action = {"type": "click", "x": x, "y": y, "time": elapsed}
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
            
            action = {"type": "key", "key": key_str, "time": elapsed}
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
        
        self.stats = {"combats": 0, "start_time": None}
        
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
        
        chat_top = int(h * 0.5)
        chat_bottom = h
        chat_left = 0
        chat_right = int(w * 0.6)
        
        chat_area = frame[chat_top:chat_bottom, chat_left:chat_right]
        
        if chat_area.size == 0:
            return False
        
        try:
            result = cv2.matchTemplate(chat_area, self.mp_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.5:
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
        
        message = "📩 MP recu sur Dofus! Le bot s'est arrete."
        send_notification(self.config.data, message)
        self.log("📱 Notification envoyee!")
        
        if self.callback:
            self.callback("mp_detected", None)
    
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
        """Détecte si on est en mode combat - ULTRA STRICT"""
        h, w = frame.shape[:2]
        
        # SEULE méthode fiable: timeline verte en haut
        timeline_area = frame[5:50, int(w*0.3):int(w*0.7)]
        
        if timeline_area.size == 0:
            return False
        
        hsv = cv2.cvtColor(timeline_area, cv2.COLOR_BGR2HSV)
        
        # Vert très spécifique de la timeline Dofus
        green_mask = cv2.inRange(hsv, np.array([45, 150, 150]), np.array([75, 255, 255]))
        green_pixels = cv2.countNonZero(green_mask)
        
        total_pixels = timeline_area.shape[0] * timeline_area.shape[1]
        ratio = green_pixels / total_pixels
        
        # Doit avoir AU MOINS 5% de vert
        return ratio > 0.05
    
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
        
        search_delay = self.config.data.get("combat", {}).get("search_delay", 2.0)
        
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
            
            try:
                frame = self.capture_screen()
                
                # Vérifier les MP
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
    
    def pause(self):
        self.paused = not self.paused


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
        self.root.title("🗡️ Dofus Combat Bot - By ImSombre")
        self.root.geometry("780x520")
        self.root.configure(bg=self.colors['bg'])
        self.root.resizable(True, True)
        
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 780) // 2
        y = (self.root.winfo_screenheight() - 520) // 2
        self.root.geometry(f"780x520+{x}+{y}")
    
    def create_widgets(self):
        # HEADER
        header = tk.Frame(self.root, bg=self.colors['bg2'], height=55)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🗡️ Combat Bot", font=('Segoe UI', 15, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['accent']).pack(side='left', padx=15, pady=10)
        
        self.status_label = tk.Label(header, text="⚪ En attente", font=('Segoe UI', 10),
                                     bg=self.colors['bg2'], fg=self.colors['text2'])
        self.status_label.pack(side='left', padx=10)
        
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
        
        # MAIN
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill='both', expand=True, padx=8, pady=5)
        
        # LEFT: Config
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
            actions_text = f"✅ {len(actions)} actions"
            actions_color = self.colors['success']
        else:
            actions_text = "❌ Aucune action"
            actions_color = self.colors['accent']
        self.actions_label = tk.Label(left, text=actions_text, font=('Segoe UI', 9),
                                      bg=self.colors['bg2'], fg=actions_color)
        self.actions_label.pack()
        
        rec_btns = tk.Frame(left, bg=self.colors['bg2'])
        rec_btns.pack(pady=3)
        tk.Button(rec_btns, text="🗑️ Effacer", font=('Segoe UI', 9), bg=self.colors['bg3'], fg='white',
                 command=self.clear_recording).pack(side='left', padx=2)
        
        tk.Frame(left, bg=self.colors['bg3'], height=1).pack(fill='x', padx=15, pady=6)
        
        # Section Mobs
        tk.Label(left, text="👾 Mobs", font=('Segoe UI', 11, 'bold'),
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
        tk.Button(notif_btns, text="📱 Config", font=('Segoe UI', 9), bg='#5865F2', fg='white',
                 command=self.open_webhook_config).pack(side='left', padx=2)
        
        tk.Frame(left, bg=self.colors['bg3'], height=1).pack(fill='x', padx=15, pady=6)
        
        # Délais
        tk.Label(left, text="⚙️ Délais", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=(3,3))
        
        param_f = tk.Frame(left, bg=self.colors['bg2'])
        param_f.pack(fill='x', padx=20, pady=3)
        
        r1 = tk.Frame(param_f, bg=self.colors['bg2'])
        r1.pack(fill='x', pady=1)
        tk.Label(r1, text="Recherche:", font=('Segoe UI', 9), bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.search_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("search_delay", 2.0)))
        tk.Spinbox(r1, from_=0.5, to=10.0, increment=0.5, width=5, textvariable=self.search_delay_var,
                  command=self.save_params).pack(side='right')
        
        r2 = tk.Frame(param_f, bg=self.colors['bg2'])
        r2.pack(fill='x', pady=1)
        tk.Label(r2, text="Entre actions:", font=('Segoe UI', 9), bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        self.action_delay_var = tk.StringVar(value=str(self.config.data.get("combat", {}).get("action_delay", 0.3)))
        tk.Spinbox(r2, from_=0.1, to=2.0, increment=0.1, width=5, textvariable=self.action_delay_var,
                  command=self.save_params).pack(side='right')
        
        # RIGHT: Log
        right = tk.Frame(main, bg=self.colors['bg2'])
        right.pack(side='right', fill='both', expand=True)
        
        tk.Label(right, text="📝 Journal", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        self.log_text = tk.Text(right, bg=self.colors['bg'], fg=self.colors['text'],
                                font=('Consolas', 9), wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=8, pady=(0,8))
        
        # FOOTER
        footer = tk.Frame(self.root, bg=self.colors['bg2'], height=28)
        footer.pack(fill='x')
        footer.pack_propagate(False)
        
        tk.Label(footer, text="F5: Start | F6: Pause | F7: Stop | F8: Record", font=('Segoe UI', 9),
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
            self.root.after(0, lambda: self.on_mp_detected())
    
    def on_mp_detected(self):
        self.status_label.config(text="🚨 MP!", fg=self.colors['record'])
        self.start_btn.config(state='normal')
        self.record_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️")
        self.stop_btn.config(state='disabled')
        
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass
        
        messagebox.showwarning("MP Reçu!", "📩 Tu as reçu un MP!\n\nLe bot s'est arrêté automatiquement.")
    
    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.config(text="⏹️ STOP", bg=self.colors['warning'])
            self.status_label.config(text="🔴 REC", fg=self.colors['record'])
            
            self.recorder = ActionRecorder(self.bot_callback)
            self.recorder.start_recording()
            
            self.log("🔴 Enregistrement démarré!")
        else:
            self.is_recording = False
            self.record_btn.config(text="🔴 REC", bg=self.colors['record'])
            self.status_label.config(text="⚪ En attente", fg=self.colors['text2'])
            
            if self.recorder:
                actions = self.recorder.stop_recording()
                self.config.data["recorded_actions"] = actions
                self.config.save()
                
                if actions:
                    self.actions_label.config(text=f"✅ {len(actions)} actions", fg=self.colors['success'])
                    self.log(f"✅ {len(actions)} actions enregistrées!")
    
    def clear_recording(self):
        if messagebox.askyesno("Confirmer", "Effacer toutes les actions?"):
            self.config.data["recorded_actions"] = []
            self.config.save()
            self.actions_label.config(text="❌ Aucune action", fg=self.colors['accent'])
            self.log("🗑️ Actions effacées")
    
    def refresh_mob_list(self):
        self.mob_listbox.delete(0, 'end')
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        
        if os.path.exists(mob_dir):
            for filename in os.listdir(mob_dir):
                if filename.endswith('.png'):
                    self.mob_listbox.insert('end', f"  👾 {filename}")
    
    def capture_mob(self):
        if messagebox.askokcancel("Capture Mob", "📸 Survole le mob avec ta souris.\nTu as 3 secondes après OK."):
            threading.Thread(target=self._do_capture_mob, daemon=True).start()
    
    def _do_capture_mob(self):
        self.log("📸 Survole le mob...")
        for i in range(3, 0, -1):
            self.log(f"⏳ {i}...")
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
        selection = self.mob_listbox.curselection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionne un mob")
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
        try:
            self.config.data["combat"]["search_delay"] = float(self.search_delay_var.get())
            self.config.data["combat"]["action_delay"] = float(self.action_delay_var.get())
            self.config.save()
        except:
            pass
    
    def toggle_mp_detection(self):
        self.config.data["mp_detection"] = self.mp_detection_var.get()
        self.config.save()
    
    def capture_mp_template(self):
        if messagebox.askokcancel("Capture MP", "📸 Place ta souris sur le 'de' cyan du MP.\nTu as 3 secondes après OK."):
            threading.Thread(target=self._do_capture_mp, daemon=True).start()
    
    def _do_capture_mp(self):
        self.log("📸 Place ta souris sur 'de'...")
        for i in range(3, 0, -1):
            self.log(f"⏳ {i}...")
            time.sleep(1)
        
        x, y = pyautogui.position()
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
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
    
    def open_webhook_config(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("📱 Notifications")
        dialog.geometry("450x300")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="📱 Notifications", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=10)
        
        # Ntfy
        ntfy_frame = tk.LabelFrame(dialog, text="📲 Ntfy.sh", font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['bg2'], fg=self.colors['text'], padx=15, pady=10)
        ntfy_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(ntfy_frame, text="Topic:", bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        ntfy_entry = tk.Entry(ntfy_frame, width=40, bg=self.colors['bg3'], fg=self.colors['text'])
        ntfy_entry.insert(0, self.config.data.get("ntfy_topic", ""))
        ntfy_entry.pack(fill='x', pady=5)
        
        # Discord
        discord_frame = tk.LabelFrame(dialog, text="💬 Discord", font=('Segoe UI', 10, 'bold'),
                                      bg=self.colors['bg2'], fg=self.colors['text'], padx=15, pady=10)
        discord_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(discord_frame, text="Webhook URL:", bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        url_entry = tk.Entry(discord_frame, width=50, bg=self.colors['bg3'], fg=self.colors['text'])
        url_entry.insert(0, self.config.data.get("discord_webhook", ""))
        url_entry.pack(fill='x', pady=5)
        
        def save_config():
            self.config.data["ntfy_topic"] = ntfy_entry.get().strip()
            self.config.data["discord_webhook"] = url_entry.get().strip()
            self.config.save()
            self.log("✅ Notifications sauvegardées!")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['success'], fg='white', command=save_config).pack(pady=15)
    
    def setup_hotkeys(self):
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
        if self.bot and self.bot.stats.get("start_time"):
            elapsed = datetime.now() - self.bot.stats["start_time"]
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.combat_count_label.config(text=str(self.bot.stats.get("combats", 0)))
        
        self.root.after(1000, self.update_time)
    
    def start_bot(self):
        actions = self.config.data.get("recorded_actions", [])
        if not actions:
            messagebox.showwarning("Attention", "Aucune action enregistrée!\n\n1. Clique REC\n2. Fais un combat\n3. Stop REC\n4. Lance")
            return
        
        mob_dir = os.path.join(self.config.script_dir, "mobs")
        has_mobs = os.path.exists(mob_dir) and any(f.endswith('.png') for f in os.listdir(mob_dir))
        
        if not has_mobs:
            messagebox.showwarning("Attention", "Capture d'abord un mob!")
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
        if self.bot:
            self.bot.pause()
            if self.bot.paused:
                self.pause_btn.config(text="▶️")
                self.status_label.config(text="⏸️ Pause", fg=self.colors['warning'])
            else:
                self.pause_btn.config(text="⏸️")
                self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
    
    def stop_bot(self):
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