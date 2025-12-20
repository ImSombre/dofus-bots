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
import requests

# Essayer d'importer keyboard pour un meilleur support des touches
try:
    import keyboard
    HAS_KEYBOARD = True
    print("✅ Module 'keyboard' disponible")
except ImportError:
    HAS_KEYBOARD = False
    print("⚠️ Module 'keyboard' non disponible, utilisation de pyautogui")

def press_key(key):
    """Appuie sur une touche de manière fiable"""
    if not key:
        return
    
    # Nettoyer la touche (mais garder la casse pour les touches spéciales)
    key = str(key).strip()
    
    print(f"    🎹 Touche envoyée: '{key}'")
    
    if HAS_KEYBOARD:
        try:
            keyboard.press_and_release(key)
        except Exception as e:
            print(f"    ⚠️ Erreur keyboard: {e}, fallback pyautogui")
            pyautogui.press(key)
    else:
        pyautogui.press(key)

def send_discord_webhook(webhook_url, message, username="Dofus Bot"):
    """Envoie une notification Discord via webhook"""
    if not webhook_url:
        return False
    
    try:
        data = {
            "username": username,
            "content": message
        }
        response = requests.post(webhook_url, json=data, timeout=10)
        return response.status_code == 204
    except Exception as e:
        print(f"❌ Erreur webhook Discord: {e}")
        return False


def send_ntfy(topic, message):
    """Envoie une notification Ntfy.sh (gratuit)"""
    if not topic:
        return False
    try:
        import urllib.request
        url = f"https://ntfy.sh/{topic}"
        data = message.encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Title', 'Dofus Bot')
        req.add_header('Tags', 'envelope,warning')
        req.add_header('Priority', 'high')
        urllib.request.urlopen(req, timeout=10)
        return True
    except:
        return False


def send_notification(config_data, message):
    """Envoie notification via Discord ET Ntfy"""
    # Discord
    webhook = config_data.get("discord_webhook", "")
    if webhook:
        send_discord_webhook(webhook, message)
    
    # Ntfy
    topic = config_data.get("ntfy_topic", "")
    if topic:
        send_ntfy(topic, message)

# ============================================================
#                    CONFIGURATION
# ============================================================

# Thème de couleurs
THEME = {
    'bg': '#0f0f1a',
    'bg2': '#1a1a2e',
    'bg3': '#252540',
    'accent': '#e94560',
    'accent2': '#0f3460',
    'success': '#00d26a',
    'warning': '#ff9f1c',
    'text': '#ffffff',
    'text2': '#8b8b9e',
    'border': '#3a3a5c'
}

class Config:
    def __init__(self):
        # Utiliser le dossier du script OU le dossier courant
        try:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.script_dir = os.getcwd()
        
        self.config_file = os.path.join(self.script_dir, "bot_config.json")
        self.resources_dir = os.path.join(self.script_dir, "resources")
        
        print(f"📁 Config: {self.config_file}")
        
        if not os.path.exists(self.resources_dir):
            os.makedirs(self.resources_dir)
        
        self.data = self.load()
    
    def load(self):
        # Si le fichier existe, le charger directement
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ Config chargée depuis {self.config_file}")
                
                # S'assurer que les clés essentielles existent
                if "match_threshold" not in data:
                    data["match_threshold"] = 0.7
                if "harvest_delay" not in data:
                    data["harvest_delay"] = 1.5
                if "move_delay" not in data:
                    data["move_delay"] = 2.0
                if "scan_delay" not in data:
                    data["scan_delay"] = 0.3
                if "resources" not in data:
                    data["resources"] = {}
                if "combat" not in data:
                    data["combat"] = {
                        "enabled": True,
                        "spells": [],
                        "end_turn_key": "space",
                        "spell_delay": 0.5,
                        "turn_delay": 2.0
                    }
                # Positions des cibles en combat
                if "combat_positions" not in data:
                    data["combat_positions"] = {
                        "2560x1440": {"self": [2006, 1032], "enemy": [2092, 1028]},
                        "1920x1080": {"self": [1489, 773], "enemy": [1547, 759]}
                    }
                
                # Webhook Discord et détection MP
                if "discord_webhook" not in data:
                    data["discord_webhook"] = ""
                if "ntfy_topic" not in data:
                    data["ntfy_topic"] = ""
                if "mp_detection" not in data:
                    data["mp_detection"] = True
                
                # Raccourcis clavier
                if "hotkeys" not in data:
                    data["hotkeys"] = {
                        "start": "F5",
                        "pause": "F6",
                        "stop": "F7"
                    }
                
                return data
            except Exception as e:
                print(f"⚠️ Erreur chargement config: {e}")
        
        # Sinon, créer une config par défaut
        print(f"📝 Nouvelle config sera créée")
        return {
            "match_threshold": 0.7,
            "harvest_delay": 1.5,
            "move_delay": 2.0,
            "scan_delay": 0.3,
            "resources": {},
            "combat": {
                "enabled": True,
                "spells": [],
                "end_turn_key": "space",
                "spell_delay": 0.5,
                "turn_delay": 2.0
            },
            "combat_positions": {
                "2560x1440": {"self": [2006, 1032], "enemy": [2092, 1028]},
                "1920x1080": {"self": [1489, 773], "enemy": [1547, 759]}
            },
            "discord_webhook": "",
            "ntfy_topic": "",
            "mp_detection": True,
            "hotkeys": {
                "start": "F5",
                "pause": "F6",
                "stop": "F7"
            }
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"💾 Config sauvegardée: {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False
    
    def get_resource_dir(self, name):
        path = os.path.join(self.resources_dir, name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path
    
    def add_resource(self, name):
        if name not in self.data["resources"]:
            self.data["resources"][name] = {"enabled": True, "count": 0}
            self.get_resource_dir(name)
            self.save()
            return True
        return False
    
    def remove_resource(self, name):
        if name in self.data["resources"]:
            del self.data["resources"][name]
            import shutil
            path = os.path.join(self.resources_dir, name)
            if os.path.exists(path):
                shutil.rmtree(path)
            self.save()
            return True
        return False


# ============================================================
#                    BOT ENGINE
# ============================================================

class BotEngine:
    def __init__(self, config, gui_callback=None):
        self.config = config
        self.gui_callback = gui_callback
        self.running = False
        self.paused = False
        self.in_combat = False
        
        # Stats
        self.stats = {
            "total_harvested": 0,
            "combats": 0,
            "session_start": None,
            "resources": {}  # Par ressource
        }
        
        self.templates = {}  # {"resource_name": [template1, template2, ...]}
        self.load_templates()
    
    def load_templates(self):
        """Charge tous les templates de toutes les ressources"""
        self.templates = {}
        for res_name in self.config.data["resources"]:
            self.templates[res_name] = []
            res_dir = self.config.get_resource_dir(res_name)
            for f in sorted(os.listdir(res_dir)):
                if f.endswith(".png"):
                    t = cv2.imread(os.path.join(res_dir, f))
                    if t is not None:
                        self.templates[res_name].append(t)
            self.stats["resources"][res_name] = 0
    
    def log(self, message):
        """Envoie un message au GUI"""
        if self.gui_callback:
            self.gui_callback("log", message)
        print(message)
    
    def update_stats(self):
        """Met à jour les stats dans le GUI"""
        if self.gui_callback:
            self.gui_callback("stats", self.stats)
    
    def capture_screen(self):
        screenshot = ImageGrab.grab()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    def detect_popup(self, frame):
        """Détecte les popups (level up, succès, etc.) - UNIQUEMENT par template matching"""
        # JAMAIS détecter si on est en combat
        if self.in_combat:
            return None
        
        # Cooldown pour éviter le spam (minimum 2 secondes entre les clics)
        if not hasattr(self, '_last_popup_click'):
            self._last_popup_click = 0
        
        if time.time() - self._last_popup_click < 2.0:
            return None
        
        # UNIQUEMENT template matching (les autres méthodes causent des faux positifs)
        result = self._detect_popup_template(frame)
        if result:
            self._last_popup_click = time.time()
            return result
        
        return None
    
    def _detect_popup_template(self, frame):
        """Détecte le popup par template matching"""
        if not hasattr(self, '_popup_template'):
            popup_path = os.path.join(self.config.script_dir, "popup_template.png")
            if os.path.exists(popup_path):
                self._popup_template = cv2.imread(popup_path)
                print(f"✅ Template popup chargé")
            else:
                self._popup_template = None
        
        if self._popup_template is None:
            return None
        
        h, w = frame.shape[:2]
        
        # Chercher dans la zone centrale
        search_area = frame[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
        
        if search_area.size == 0:
            return None
        
        try:
            result = cv2.matchTemplate(search_area, self._popup_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Seuil élevé pour éviter les faux positifs
            if max_val > 0.8:
                th, tw = self._popup_template.shape[:2]
                # Position dans l'écran complet
                cx = max_loc[0] + tw // 2 + int(w*0.2)
                cy = max_loc[1] + th // 2 + int(h*0.2)
                return (cx, cy)
        except:
            pass
        
        return None
    
    def capture_popup_template(self):
        """Capture le template du bouton popup"""
        print("📸 Capture du bouton popup...")
        print("   Place ta souris sur le bouton 'Ok' du popup")
        time.sleep(3)
        
        x, y = pyautogui.position()
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Capturer une zone de 120x50 autour du bouton
        region_w, region_h = 120, 50
        y1 = max(0, y - region_h // 2)
        y2 = min(frame.shape[0], y + region_h // 2)
        x1 = max(0, x - region_w // 2)
        x2 = min(frame.shape[1], x + region_w // 2)
        
        template = frame[y1:y2, x1:x2]
        
        if template.size > 0:
            template_path = os.path.join(self.config.script_dir, "popup_template.png")
            cv2.imwrite(template_path, template)
            print(f"✅ Template popup sauvegardé: {template_path}")
            self._popup_template = template
            return True
        else:
            print("❌ Erreur capture")
            return False
    
    def detect_combat(self, frame):
        """Détecte le mode combat - ULTRA STRICT pour éviter les faux positifs"""
        h, w = frame.shape[:2]
        
        # SEULE méthode fiable: détecter la timeline de combat en haut
        # C'est une barre verte qui n'existe QUE en combat
        timeline_area = frame[5:50, int(w*0.3):int(w*0.7)]
        
        if timeline_area.size == 0:
            return False
        
        hsv = cv2.cvtColor(timeline_area, cv2.COLOR_BGR2HSV)
        
        # Vert très spécifique de la timeline Dofus
        green_mask = cv2.inRange(hsv, np.array([45, 150, 150]), np.array([75, 255, 255]))
        green_pixels = cv2.countNonZero(green_mask)
        
        total_pixels = timeline_area.shape[0] * timeline_area.shape[1]
        ratio = green_pixels / total_pixels
        
        # Doit avoir AU MOINS 5% de vert pour être en combat
        if ratio > 0.05:
            print(f"  ⚔️ Combat détecté: {ratio*100:.1f}% timeline verte")
            return True
        
        return False
    
    def detect_resources(self, frame):
        """Détecte toutes les ressources activées"""
        all_positions = []
        threshold = self.config.data["match_threshold"]
        
        for res_name, templates in self.templates.items():
            # Vérifier si la ressource est activée
            if not self.config.data["resources"].get(res_name, {}).get("enabled", False):
                continue
            
            for template in templates:
                res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(res >= threshold)
                
                h, w = template.shape[:2]
                
                for pt in zip(*locations[::-1]):
                    cx = pt[0] + w // 2
                    cy = pt[1] + h // 2
                    
                    # Éviter doublons
                    is_dup = False
                    for existing in all_positions:
                        if abs(cx - existing[0]) < 40 and abs(cy - existing[1]) < 40:
                            is_dup = True
                            break
                    
                    if not is_dup:
                        score = res[pt[1], pt[0]]
                        all_positions.append((cx, cy, score, res_name))
        
        all_positions.sort(key=lambda x: x[2], reverse=True)
        return all_positions
    
    def harvest(self, pos, res_name):
        """Récolte une ressource"""
        self.log(f"🌾 Récolte {res_name} ({pos[0]}, {pos[1]})")
        
        pyautogui.moveTo(pos[0], pos[1], duration=0.15)
        time.sleep(0.1)
        pyautogui.click(pos[0], pos[1], button='right')
        time.sleep(0.4)
        pyautogui.click(pos[0] + 15, pos[1] + 35)
        time.sleep(self.config.data["harvest_delay"])
        
        self.stats["total_harvested"] += 1
        self.stats["resources"][res_name] = self.stats["resources"].get(res_name, 0) + 1
        self.update_stats()
    
    def detect_mp(self, frame):
        """Détecte les MP par template matching (image du texte 'de')"""
        h, w = frame.shape[:2]
        
        # Zone du chat élargie
        chat_top = int(h * 0.50)
        chat_bottom = h
        chat_left = 0
        chat_right = int(w * 0.60)
        
        chat_area = frame[chat_top:chat_bottom, chat_left:chat_right]
        
        if chat_area.size == 0:
            return False
        
        # Charger le template MP si disponible
        if not hasattr(self, '_mp_template'):
            mp_template_path = os.path.join(self.config.script_dir, "mp_template.png")
            if os.path.exists(mp_template_path):
                self._mp_template = cv2.imread(mp_template_path)
                if self._mp_template is not None:
                    th, tw = self._mp_template.shape[:2]
                    print(f"✅ Template MP chargé ({tw}x{th}px)")
                else:
                    self._mp_template = None
            else:
                self._mp_template = None
        
        if self._mp_template is None:
            return False
        
        # Template matching
        try:
            result = cv2.matchTemplate(chat_area, self._mp_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # Seuil de détection (0.5 = 50% de correspondance)
            if max_val > 0.5:
                print(f"\n🚨🚨🚨 MP DÉTECTÉ! Score={max_val:.2f} 🚨🚨🚨\n")
                return True
                
        except Exception as e:
            print(f"  ⚠️ Erreur détection MP: {e}")
        
        return False
    
    def capture_mp_template(self):
        """Capture le template du texte MP 'de NomJoueur'"""
        self.log("📸 Capture du template MP...")
        self.log("⏳ Place ta souris sur le 'de' cyan du MP...")
        self.log("   3 secondes...")
        
        time.sleep(1)
        self.log("   2...")
        time.sleep(1)
        self.log("   1...")
        time.sleep(1)
        
        # Capturer l'écran
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Position de la souris
        x, y = pyautogui.position()
        
        # Zone petite: juste "de" (40x20 pixels)
        region_w, region_h = 40, 20
        
        y1 = max(0, y - 5)
        y2 = min(frame.shape[0], y + region_h)
        x1 = max(0, x - 5)
        x2 = min(frame.shape[1], x + region_w)
        
        template = frame[y1:y2, x1:x2]
        
        if template.size > 0:
            # Sauvegarder le template
            template_path = os.path.join(self.config.script_dir, "mp_template.png")
            cv2.imwrite(template_path, template)
            
            # Recharger le template
            self._mp_template = template
            h, w = template.shape[:2]
            
            self.log(f"✅ Template MP sauvegardé! ({w}x{h}px)")
            return True
        else:
            self.log("❌ Erreur capture template")
            return False
    
    def on_mp_detected(self):
        """Appelé quand un MP est détecté"""
        self.log("💬 MP DÉTECTÉ! Arrêt du bot...")
        print("\n" + "🚨" * 20)
        print("MESSAGE PRIVÉ REÇU - BOT ARRÊTÉ")
        print("🚨" * 20 + "\n")
        
        # Arrêter le bot
        self.running = False
        self.paused = True
        
        # Envoyer notification simple (Discord + Ntfy)
        message = "📩 MP recu sur Dofus! Le bot s'est arrete."
        send_notification(self.config.data, message)
        self.log("📱 Notification envoyee!")
    
    def find_timeline_portraits(self, frame):
        """Retourne les positions fixes des cercles selon la résolution"""
        h, w = frame.shape[:2]
        
        # Récupérer les positions depuis la config
        positions = self.config.data.get("combat_positions", {})
        
        # Déterminer la résolution
        if w >= 2560:
            res_key = "2560x1440"
        elif w >= 1920:
            res_key = "1920x1080"
        else:
            res_key = "1920x1080"  # Fallback
        
        # Récupérer les positions pour cette résolution
        res_positions = positions.get(res_key, {})
        
        if res_positions:
            self_pos = tuple(res_positions.get("self", [1489, 773]))
            enemy_pos = tuple(res_positions.get("enemy", [1547, 759]))
        else:
            # Valeurs par défaut si pas trouvé
            if w >= 2560:
                self_pos = (2006, 1032)
                enemy_pos = (2092, 1028)
            else:
                self_pos = (1489, 773)
                enemy_pos = (1547, 759)
        
        print(f"  📺 Résolution {w}x{h} -> {res_key}")
        print(f"  🔴 Moi: {self_pos}")
        print(f"  🔵 Ennemi: {enemy_pos}")
        
        return self_pos, enemy_pos
    
    def find_enemy_position(self, frame):
        """Trouve la position de l'ennemi (2ème portrait)"""
        self_pos, enemy_pos = self.find_timeline_portraits(frame)
        return enemy_pos
    
    def find_self_position(self, frame):
        """Trouve ta position (1er portrait)"""
        self_pos, enemy_pos = self.find_timeline_portraits(frame)
        return self_pos
    
    def handle_combat(self):
        """Gère un combat avec les sorts configurés"""
        if not self.config.data.get("combat", {}).get("enabled", True):
            self.log("⚔️ Combat détecté mais gestion désactivée")
            return
        
        self.log("⚔️ Combat détecté!")
        self.in_combat = True
        start = time.time()
        last_action = 0
        turn_count = 0
        
        combat_config = self.config.data.get("combat", {})
        spells = combat_config.get("spells", [])
        end_turn_key = combat_config.get("end_turn_key", "space")
        spell_delay = combat_config.get("spell_delay", 0.5)
        turn_delay = combat_config.get("turn_delay", 2.0)
        
        # Attendre un peu que le combat se charge
        time.sleep(2)
        self.log("⚔️ Début des actions...")
        
        # Boucle de combat
        while self.in_combat and self.running and (time.time() - start) < 180:
            if self.paused:
                time.sleep(0.5)
                continue
                
            frame = self.capture_screen()
            
            # Vérifier si le combat est terminé
            if not self.detect_combat(frame):
                self.log(f"✅ Combat terminé! ({turn_count} tours)")
                self.stats["combats"] += 1
                self.in_combat = False
                self.update_stats()
                time.sleep(2)
                break
            
            # Exécuter les sorts configurés
            if time.time() - last_action > turn_delay:
                turn_count += 1
                self.log(f"🗡️ Tour {turn_count}")
                
                # Trouver les portraits
                self_pos, enemy_pos = self.find_timeline_portraits(frame)
                
                self.log(f"  📍 Moi: {self_pos}, Ennemi: {enemy_pos}")
                
                # Lancer chaque sort activé
                for spell in spells:
                    if spell.get("enabled", False) and spell.get("key"):
                        key = spell.get("key", "")
                        name = spell.get("name", f"Sort {key}")
                        target = spell.get("target", "enemy")
                        
                        # Appuyer sur la touche du sort
                        self.log(f"  🔮 {name} (touche {key})")
                        press_key(key)
                        time.sleep(0.4)
                        
                        # Cliquer sur la cible
                        if target == "self" and self_pos:
                            self.log(f"    → Clic sur MOI")
                            pyautogui.click(self_pos[0], self_pos[1])
                        elif target == "enemy" and enemy_pos:
                            self.log(f"    → Clic sur ENNEMI")
                            pyautogui.click(enemy_pos[0], enemy_pos[1])
                        elif target == "self" and not self_pos:
                            self.log(f"    ⚠️ Portrait MOI non trouvé!")
                        elif target == "enemy" and not enemy_pos:
                            self.log(f"    ⚠️ Portrait ENNEMI non trouvé!")
                        
                        time.sleep(spell_delay)
                
                # Fin du tour
                if end_turn_key:
                    time.sleep(0.3)
                    press_key(end_turn_key)
                    self.log(f"  ⏭️ Fin du tour ({end_turn_key})")
                
                last_action = time.time()
            
            time.sleep(0.5)
        
        self.in_combat = False
    
    def run(self):
        """Boucle principale du bot"""
        self.running = True
        self.stats["session_start"] = datetime.now()
        self.log("🚀 Bot démarré!")
        
        no_resource = 0
        last_harvest = time.time()
        
        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue
            
            try:
                frame = self.capture_screen()
                
                # Détection MP (priorité maximum)
                if self.config.data.get("mp_detection", True):
                    if self.detect_mp(frame):
                        self.on_mp_detected()
                        break
                
                # Combat d'abord! (priorité absolue)
                if self.detect_combat(frame):
                    if not self.in_combat:
                        self.handle_combat()
                    continue
                
                # Popup SEULEMENT si PAS en combat
                if not self.in_combat:
                    popup = self.detect_popup(frame)
                    if popup:
                        self.log("📢 Popup - Clic Ok")
                        pyautogui.click(popup[0], popup[1])
                        time.sleep(0.5)
                        continue
                
                # Ressources SEULEMENT si PAS en combat
                if not self.in_combat:
                    resources = self.detect_resources(frame)
                    
                    if resources:
                        no_resource = 0
                        if time.time() - last_harvest > self.config.data["harvest_delay"]:
                            res = resources[0]
                            self.harvest((res[0], res[1]), res[3])
                            last_harvest = time.time()
                    else:
                        no_resource += 1
                        if no_resource > 30:
                            self.log("🔍 Déplacement...")
                            h, w = frame.shape[:2]
                            pyautogui.click(
                                w//2 + np.random.randint(-200, 200),
                                h//2 + np.random.randint(-150, 150)
                            )
                            time.sleep(self.config.data["move_delay"])
                            no_resource = 0
                
                time.sleep(self.config.data["scan_delay"])
                
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

class BotGUI:
    def __init__(self):
        self.config = Config()
        self.bot = None
        self.bot_thread = None
        
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.refresh_resources()
    
    def run(self):
        """Lance la boucle principale"""
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🌾 Dofus Farming Bot - by ImSombre")
        self.root.geometry("950x800")
        self.root.configure(bg=THEME['bg'])
        self.root.resizable(True, True)
        
        # Icône (optionnel)
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
    
    def setup_styles(self):
        self.colors = {
            'bg': '#1a1a2e',
            'bg2': '#16213e',
            'bg3': '#0f3460',
            'accent': '#e94560',
            'accent2': '#ff6b6b',
            'success': '#4ecca3',
            'warning': '#ffc107',
            'text': '#eaeaea',
            'text2': '#a0a0a0'
        }
        
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['bg2'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'])
        style.configure('Title.TLabel', font=('Segoe UI', 24, 'bold'), foreground=self.colors['accent'])
        style.configure('Subtitle.TLabel', font=('Segoe UI', 11), foreground=self.colors['text2'])
        style.configure('Stat.TLabel', font=('Segoe UI', 14, 'bold'), foreground=self.colors['success'])
    
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.colors['bg2'], height=80)
        header.pack(fill='x', padx=10, pady=10)
        header.pack_propagate(False)
        
        # Title + version
        title_frame = tk.Frame(header, bg=self.colors['bg2'])
        title_frame.pack(side='left', padx=20, pady=10)
        
        tk.Label(title_frame, text="🌾 Dofus Farming Bot", font=('Segoe UI', 20, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['accent']).pack(anchor='w')
        tk.Label(title_frame, text="v6.0 • Combat • MP Detection • Discord", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(anchor='w')
        
        # Status indicator
        self.status_label = tk.Label(header, text="⚪ En attente", font=('Segoe UI', 11),
                                     bg=self.colors['bg2'], fg=self.colors['text2'])
        self.status_label.pack(side='left', padx=30)
        
        # Boutons de contrôle
        ctrl_frame = tk.Frame(header, bg=self.colors['bg2'])
        ctrl_frame.pack(side='right', padx=20)
        
        self.start_btn = tk.Button(ctrl_frame, text="▶️ DÉMARRER", font=('Segoe UI', 11, 'bold'),
                                   bg=self.colors['success'], fg='white', width=12,
                                   command=self.start_bot, cursor='hand2')
        self.start_btn.pack(side='left', padx=5)
        
        self.pause_btn = tk.Button(ctrl_frame, text="⏸️ PAUSE", font=('Segoe UI', 11),
                                   bg=self.colors['warning'], fg='black', width=10,
                                   command=self.pause_bot, state='disabled', cursor='hand2')
        self.pause_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(ctrl_frame, text="⏹️ STOP", font=('Segoe UI', 11),
                                  bg=self.colors['accent'], fg='white', width=10,
                                  command=self.stop_bot, state='disabled', cursor='hand2')
        self.stop_btn.pack(side='left', padx=5)
        
        # Main content
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel - Resources
        left = tk.Frame(main, bg=self.colors['bg2'], width=350)
        left.pack(side='left', fill='y', padx=(0,5), pady=5)
        left.pack_propagate(False)
        
        tk.Label(left, text="📦 Ressources", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=10)
        
        # Boutons ressources
        res_btn_frame = tk.Frame(left, bg=self.colors['bg2'])
        res_btn_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(res_btn_frame, text="➕ Ajouter", font=('Segoe UI', 9),
                 bg=self.colors['bg3'], fg='white', command=self.add_resource).pack(side='left', padx=2)
        tk.Button(res_btn_frame, text="🗑️ Supprimer", font=('Segoe UI', 9),
                 bg=self.colors['bg3'], fg='white', command=self.remove_resource).pack(side='left', padx=2)
        tk.Button(res_btn_frame, text="📷 Calibrer", font=('Segoe UI', 9),
                 bg=self.colors['accent'], fg='white', command=self.calibrate_resource).pack(side='right', padx=2)
        
        # Liste des ressources
        self.res_frame = tk.Frame(left, bg=self.colors['bg2'])
        self.res_frame.pack(fill='x', padx=10, pady=5)
        
        # ====== Section Combat ======
        tk.Frame(left, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(left, text="⚔️ Combat", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        # Checkbox activer combat
        self.combat_enabled_var = tk.BooleanVar(value=self.config.data.get("combat", {}).get("enabled", True))
        tk.Checkbutton(left, text="Gérer les combats automatiquement", 
                      variable=self.combat_enabled_var, bg=self.colors['bg2'], fg=self.colors['text'],
                      selectcolor=self.colors['bg3'], activebackground=self.colors['bg2'],
                      command=self.toggle_combat).pack(anchor='w', padx=15)
        
        # Bouton configurer sorts
        tk.Button(left, text="🎯 Configurer les sorts", font=('Segoe UI', 10),
                 bg=self.colors['accent'], fg='white', 
                 command=self.open_spell_config, cursor='hand2').pack(pady=10)
        
        # Affichage rapide des sorts actifs
        self.spells_preview = tk.Label(left, text="", font=('Segoe UI', 9),
                                       bg=self.colors['bg2'], fg=self.colors['text2'])
        self.spells_preview.pack(pady=5)
        self.update_spells_preview()
        
        # ====== Section Notifications ======
        tk.Frame(left, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(left, text="🔔 Notifications", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        # Checkbox détection MP
        self.mp_detection_var = tk.BooleanVar(value=self.config.data.get("mp_detection", True))
        tk.Checkbutton(left, text="Détecter les MP et arrêter", 
                      variable=self.mp_detection_var, bg=self.colors['bg2'], fg=self.colors['text'],
                      selectcolor=self.colors['bg3'], activebackground=self.colors['bg2'],
                      command=self.toggle_mp_detection).pack(anchor='w', padx=15)
        
        # Frame pour les boutons MP
        mp_buttons = tk.Frame(left, bg=self.colors['bg2'])
        mp_buttons.pack(pady=5)
        
        # Bouton capturer template MP
        tk.Button(mp_buttons, text="📸 Capturer MP", font=('Segoe UI', 9),
                 bg=self.colors['warning'], fg='white', 
                 command=self.start_mp_calibration, cursor='hand2').pack(side='left', padx=5)
        
        # Bouton configurer webhook
        tk.Button(mp_buttons, text="📱 Discord", font=('Segoe UI', 9),
                 bg='#5865F2', fg='white', 
                 command=self.open_webhook_config, cursor='hand2').pack(side='left', padx=5)
        
        # Afficher le statut du template MP
        mp_template_path = os.path.join(self.config.script_dir, "mp_template.png")
        if os.path.exists(mp_template_path):
            mp_status = "Template MP: ✅ Configuré"
        else:
            mp_status = "Template MP: ❌ Non configuré"
        self.mp_color_label = tk.Label(left, text=mp_status, font=('Segoe UI', 8),
                                       bg=self.colors['bg2'], fg=self.colors['text2'])
        self.mp_color_label.pack(pady=2)
        
        # Indicateur webhook
        has_notif = self.config.data.get("discord_webhook") or self.config.data.get("ntfy_topic")
        webhook_status = "✅ Configure" if has_notif else "❌ Non configure"
        self.webhook_label = tk.Label(left, text=f"Notif: {webhook_status}", font=('Segoe UI', 9),
                                      bg=self.colors['bg2'], fg=self.colors['text2'])
        self.webhook_label.pack(pady=2)
        
        # ===== SECTION POPUP =====
        tk.Frame(left, bg=self.colors['bg3'], height=1).pack(fill='x', padx=10, pady=5)
        tk.Label(left, text="📢 Popup Level Up", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=2)
        
        # Bouton capturer popup
        tk.Button(left, text="📸 Capturer Popup", font=('Segoe UI', 9),
                 bg=self.colors['accent'], fg='white', 
                 command=self.start_popup_calibration, cursor='hand2').pack(pady=3)
        
        # Statut popup template
        popup_template_path = os.path.join(self.config.script_dir, "popup_template.png")
        if os.path.exists(popup_template_path):
            popup_status = "Template Popup: ✅ Configuré"
        else:
            popup_status = "Template Popup: ❌ Non configuré"
        self.popup_status_label = tk.Label(left, text=popup_status, font=('Segoe UI', 8),
                                           bg=self.colors['bg2'], fg=self.colors['text2'])
        self.popup_status_label.pack(pady=2)
        
        # Right panel
        right = tk.Frame(main, bg=self.colors['bg'])
        right.pack(side='right', fill='both', expand=True, padx=(5,0), pady=5)
        
        # Stats
        stats_frame = tk.Frame(right, bg=self.colors['bg2'], height=150)
        stats_frame.pack(fill='x', pady=(0,5))
        stats_frame.pack_propagate(False)
        
        tk.Label(stats_frame, text="📊 Statistiques", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=10)
        
        stats_grid = tk.Frame(stats_frame, bg=self.colors['bg2'])
        stats_grid.pack(fill='x', padx=20)
        
        # Stats labels
        self.stat_labels = {}
        stats_data = [
            ("total", "🌾 Total récolté", "0"),
            ("combats", "⚔️ Combats", "0"),
            ("time", "⏱️ Temps", "00:00:00"),
            ("rate", "📈 Récoltes/h", "0")
        ]
        
        for i, (key, label, default) in enumerate(stats_data):
            frame = tk.Frame(stats_grid, bg=self.colors['bg3'], padx=15, pady=8)
            frame.grid(row=0, column=i, padx=5, pady=5, sticky='nsew')
            stats_grid.columnconfigure(i, weight=1)
            
            tk.Label(frame, text=label, font=('Segoe UI', 9),
                    bg=self.colors['bg3'], fg=self.colors['text2']).pack()
            self.stat_labels[key] = tk.Label(frame, text=default, font=('Segoe UI', 16, 'bold'),
                                             bg=self.colors['bg3'], fg=self.colors['success'])
            self.stat_labels[key].pack()
        
        # Log
        log_frame = tk.Frame(right, bg=self.colors['bg2'])
        log_frame.pack(fill='both', expand=True)
        
        tk.Label(log_frame, text="📝 Journal", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=10)
        
        self.log_text = tk.Text(log_frame, bg=self.colors['bg'], fg=self.colors['text'],
                                font=('Consolas', 10), height=15, wrap='word',
                                insertbackground=self.colors['text'])
        self.log_text.pack(fill='both', expand=True, padx=10, pady=(0,10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Settings bar
        settings = tk.Frame(self.root, bg=self.colors['bg2'], height=50)
        settings.pack(fill='x', padx=10, pady=10)
        settings.pack_propagate(False)
        
        tk.Label(settings, text="⚙️ Paramètres:", font=('Segoe UI', 10),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left', padx=10)
        
        # Threshold
        tk.Label(settings, text="Seuil détection:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(20,5))
        self.threshold_var = tk.StringVar(value=str(int(self.config.data["match_threshold"]*100)))
        threshold_spin = tk.Spinbox(settings, from_=50, to=95, width=5, textvariable=self.threshold_var,
                                    command=self.update_threshold)
        threshold_spin.pack(side='left')
        tk.Label(settings, text="%", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        
        # Delay
        tk.Label(settings, text="Délai récolte:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(20,5))
        self.delay_var = tk.StringVar(value=str(self.config.data["harvest_delay"]))
        delay_spin = tk.Spinbox(settings, from_=0.5, to=10.0, increment=0.5, width=5, 
                                textvariable=self.delay_var)
        delay_spin.pack(side='left')
        
        # Sauvegarder à chaque changement (bouton ou frappe)
        self.delay_var.trace_add("write", lambda *args: self.update_delay())
        delay_spin.bind("<FocusOut>", lambda e: self.update_delay())
        delay_spin.bind("<Return>", lambda e: self.update_delay())
        tk.Label(settings, text="sec", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        
        # Bouton raccourcis
        tk.Button(settings, text="⌨️ Raccourcis", font=('Segoe UI', 9),
                 bg=self.colors['bg3'], fg=self.colors['text'],
                 command=self.open_hotkeys_config, cursor='hand2').pack(side='right', padx=10)
        
        # Afficher les raccourcis actuels
        hotkeys = self.config.data.get("hotkeys", {})
        hotkey_text = f"▶ {hotkeys.get('start', 'F5')} | ⏸ {hotkeys.get('pause', 'F6')} | ⏹ {hotkeys.get('stop', 'F7')}"
        self.hotkey_label = tk.Label(settings, text=hotkey_text, font=('Segoe UI', 9),
                                     bg=self.colors['bg2'], fg=self.colors['accent'])
        self.hotkey_label.pack(side='right', padx=10)
        
        # Activer les raccourcis clavier
        self.setup_hotkeys()
        
        # Timer pour update stats
        self.update_time()
    
    def refresh_resources(self):
        """Rafraîchit la liste des ressources"""
        for widget in self.res_frame.winfo_children():
            widget.destroy()
        
        if not self.config.data["resources"]:
            tk.Label(self.res_frame, text="Aucune ressource\n\nClique sur ➕ Ajouter\npour commencer",
                    font=('Segoe UI', 10), bg=self.colors['bg2'], fg=self.colors['text2']).pack(pady=30)
            return
        
        for res_name, res_data in self.config.data["resources"].items():
            frame = tk.Frame(self.res_frame, bg=self.colors['bg3'], padx=10, pady=8)
            frame.pack(fill='x', pady=3)
            
            # Checkbox pour activer/désactiver
            var = tk.BooleanVar(value=res_data.get("enabled", True))
            cb = tk.Checkbutton(frame, variable=var, bg=self.colors['bg3'],
                               activebackground=self.colors['bg3'],
                               command=lambda n=res_name, v=var: self.toggle_resource(n, v))
            cb.pack(side='left')
            
            # Nom
            tk.Label(frame, text=f"🌿 {res_name}", font=('Segoe UI', 11),
                    bg=self.colors['bg3'], fg=self.colors['text']).pack(side='left', padx=5)
            
            # Nombre de templates
            res_dir = self.config.get_resource_dir(res_name)
            template_count = len([f for f in os.listdir(res_dir) if f.endswith('.png')])
            tk.Label(frame, text=f"({template_count} templates)", font=('Segoe UI', 9),
                    bg=self.colors['bg3'], fg=self.colors['text2']).pack(side='right')
    
    def toggle_resource(self, name, var):
        """Active/désactive une ressource"""
        self.config.data["resources"][name]["enabled"] = var.get()
        self.config.save()
    
    def add_resource(self):
        """Ajoute une nouvelle ressource"""
        name = simpledialog.askstring("Nouvelle ressource", 
                                      "Nom de la ressource (ex: ble, orge, chanvre):",
                                      parent=self.root)
        if name:
            name = name.lower().strip().replace(" ", "_")
            if self.config.add_resource(name):
                self.log(f"✅ Ressource '{name}' ajoutée")
                self.refresh_resources()
            else:
                messagebox.showwarning("Attention", "Cette ressource existe déjà!")
    
    def remove_resource(self):
        """Supprime une ressource"""
        if not self.config.data["resources"]:
            messagebox.showinfo("Info", "Aucune ressource à supprimer")
            return
        
        # Créer une fenêtre de sélection
        dialog = tk.Toplevel(self.root)
        dialog.title("Supprimer une ressource")
        dialog.geometry("300x200")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Sélectionne la ressource à supprimer:",
                font=('Segoe UI', 10), bg=self.colors['bg'], fg=self.colors['text']).pack(pady=10)
        
        listbox = tk.Listbox(dialog, bg=self.colors['bg2'], fg=self.colors['text'],
                            font=('Segoe UI', 11), selectbackground=self.colors['accent'])
        listbox.pack(fill='both', expand=True, padx=20, pady=10)
        
        for name in self.config.data["resources"]:
            listbox.insert('end', name)
        
        def do_delete():
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0])
                if messagebox.askyesno("Confirmer", f"Supprimer '{name}' et ses templates?"):
                    self.config.remove_resource(name)
                    self.log(f"🗑️ Ressource '{name}' supprimée")
                    self.refresh_resources()
                    dialog.destroy()
        
        tk.Button(dialog, text="Supprimer", bg=self.colors['accent'], fg='white',
                 command=do_delete).pack(pady=10)
    
    def calibrate_resource(self):
        """Lance la calibration pour une ressource"""
        if not self.config.data["resources"]:
            messagebox.showinfo("Info", "Ajoute d'abord une ressource!")
            return
        
        # Sélection de la ressource
        dialog = tk.Toplevel(self.root)
        dialog.title("Calibrer une ressource")
        dialog.geometry("350x300")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Quelle ressource calibrer?",
                font=('Segoe UI', 12, 'bold'), bg=self.colors['bg'], fg=self.colors['text']).pack(pady=15)
        
        # Frame pour la listbox
        list_frame = tk.Frame(dialog, bg=self.colors['bg'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=5)
        
        listbox = tk.Listbox(list_frame, bg=self.colors['bg2'], fg=self.colors['text'],
                            font=('Segoe UI', 12), selectbackground=self.colors['accent'],
                            height=6)
        listbox.pack(fill='both', expand=True)
        
        for name in self.config.data["resources"]:
            listbox.insert('end', f"  🌿 {name}")
        
        # Sélectionner le premier par défaut
        if listbox.size() > 0:
            listbox.selection_set(0)
        
        def do_calibrate():
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0]).replace("  🌿 ", "")
                dialog.destroy()
                self.root.withdraw()
                time.sleep(0.5)
                self.open_calibration(name)
                self.root.deiconify()
            else:
                messagebox.showwarning("Attention", "Sélectionne une ressource!")
        
        # Bouton bien visible
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        tk.Button(btn_frame, text="📷 CALIBRER", bg=self.colors['success'], fg='white',
                 font=('Segoe UI', 12, 'bold'), width=20, height=2,
                 command=do_calibrate, cursor='hand2').pack()
        
        # Double-clic pour calibrer directement
        listbox.bind('<Double-Button-1>', lambda e: do_calibrate())
    
    def open_calibration(self, resource_name):
        """Ouvre la fenêtre de calibration pour une ressource"""
        # Fermer proprement la fenêtre principale
        self.root.quit()
        self.root.destroy()
        
        # Lancer la calibration
        calibrator = CalibrationWindow(self.config, resource_name)
        calibrator.run()
        
        # Relancer l'interface principale
        self.config = Config()  # Recharger la config
        self.bot = None
        self.bot_thread = None
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.refresh_resources()
        self.run()  # Relancer le mainloop
    
    def toggle_combat(self):
        """Active/désactive la gestion des combats"""
        enabled = self.combat_enabled_var.get()
        if "combat" not in self.config.data:
            self.config.data["combat"] = {}
        self.config.data["combat"]["enabled"] = enabled
        self.config.save()
        self.log(f"⚔️ Combat automatique: {'activé' if enabled else 'désactivé'}")
    
    def toggle_mp_detection(self):
        """Active/désactive la détection des MP"""
        enabled = self.mp_detection_var.get()
        self.config.data["mp_detection"] = enabled
        self.config.save()
        self.log(f"💬 Détection MP: {'activée' if enabled else 'désactivée'}")
    
    def start_mp_calibration(self):
        """Lance la capture du template MP"""
        result = messagebox.askokcancel(
            "Capture Template MP",
            "📸 CAPTURE DU TEXTE MP\n\n"
            "1. Assure-toi d'avoir un MP visible dans le chat\n"
            "   (texte cyan 'de NomJoueur : message')\n\n"
            "2. Clique OK\n\n"
            "3. Tu as 3 secondes pour placer ta souris\n"
            "   AU DÉBUT du texte 'de NomJoueur'\n"
            "   (juste avant le 'd' de 'de')\n\n"
            "4. Une image sera capturée automatiquement"
        )
        
        if result:
            threading.Thread(target=self._do_mp_capture, daemon=True).start()
    
    def _do_mp_capture(self):
        """Effectue la capture du template MP"""
        self.log("📸 Place ta souris au DÉBUT de 'de NomJoueur'...")
        self.log("⏳ 3 secondes...")
        time.sleep(1)
        self.log("⏳ 2 secondes...")
        time.sleep(1)
        self.log("⏳ 1 seconde...")
        time.sleep(1)
        self.log("📸 Capture!")
        
        success = self.bot.capture_mp_template() if self.bot else False
        
        if not success:
            # Essayer directement
            try:
                screenshot = ImageGrab.grab()
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                x, y = pyautogui.position()
                
                region_w, region_h = 100, 25
                y1 = max(0, y - 5)
                y2 = min(frame.shape[0], y + region_h)
                x1 = max(0, x)
                x2 = min(frame.shape[1], x + region_w)
                
                template = frame[y1:y2, x1:x2]
                
                if template.size > 0:
                    template_path = os.path.join(self.config.script_dir, "mp_template.png")
                    cv2.imwrite(template_path, template)
                    self.log(f"✅ Template MP sauvegardé!")
                    
                    # Mettre à jour le label
                    self.root.after(0, lambda: self.mp_color_label.config(text="Template MP: ✅ Configuré"))
                else:
                    self.log("❌ Erreur capture")
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
    
    def start_popup_calibration(self):
        """Lance la capture du template Popup"""
        result = messagebox.askokcancel(
            "Capture Bouton Popup",
            "📸 CAPTURE DU BOUTON POPUP\n\n"
            "1. Fais apparaître un popup (level up, succès...)\n\n"
            "2. Clique OK\n\n"
            "3. Tu as 3 secondes pour placer ta souris\n"
            "   SUR LE BOUTON 'Ok' ou 'Fermer'\n\n"
            "4. Le bouton sera capturé automatiquement"
        )
        
        if result:
            threading.Thread(target=self._do_popup_capture, daemon=True).start()
    
    def _do_popup_capture(self):
        """Effectue la capture du template Popup"""
        self.log("📸 Place ta souris sur le bouton 'Ok'...")
        self.log("⏳ 3 secondes...")
        time.sleep(1)
        self.log("⏳ 2 secondes...")
        time.sleep(1)
        self.log("⏳ 1 seconde...")
        time.sleep(1)
        self.log("📸 Capture!")
        
        success = False
        if self.bot:
            success = self.bot.capture_popup_template()
        
        if not success:
            # Essayer directement
            try:
                screenshot = ImageGrab.grab()
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                x, y = pyautogui.position()
                
                # Zone 120x50 autour du bouton
                region_w, region_h = 120, 50
                y1 = max(0, y - region_h // 2)
                y2 = min(frame.shape[0], y + region_h // 2)
                x1 = max(0, x - region_w // 2)
                x2 = min(frame.shape[1], x + region_w // 2)
                
                template = frame[y1:y2, x1:x2]
                
                if template.size > 0:
                    template_path = os.path.join(self.config.script_dir, "popup_template.png")
                    cv2.imwrite(template_path, template)
                    self.log(f"✅ Template Popup sauvegardé!")
                    
                    # Mettre à jour le label
                    self.root.after(0, lambda: self.popup_status_label.config(text="Template Popup: ✅ Configuré"))
                    success = True
                else:
                    self.log("❌ Erreur capture")
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
        
        if success:
            self.root.after(0, lambda: self.popup_status_label.config(text="Template Popup: ✅ Configuré"))
    
    def update_mp_color_label(self, r, g, b):
        """Met à jour l'affichage de la couleur MP"""
        if hasattr(self, 'mp_color_label'):
            self.mp_color_label.config(text=f"Template MP: ✅ Configuré")
    
    def setup_hotkeys(self):
        """Configure les raccourcis clavier globaux"""
        if not HAS_KEYBOARD:
            print("⚠️ Raccourcis clavier non disponibles (installer keyboard)")
            return
        
        try:
            hotkeys = self.config.data.get("hotkeys", {})
            
            # Supprimer les anciens raccourcis
            keyboard.unhook_all()
            
            # Configurer les nouveaux
            start_key = hotkeys.get("start", "F5")
            pause_key = hotkeys.get("pause", "F6")
            stop_key = hotkeys.get("stop", "F7")
            
            keyboard.add_hotkey(start_key, self.hotkey_start, suppress=False)
            keyboard.add_hotkey(pause_key, self.hotkey_pause, suppress=False)
            keyboard.add_hotkey(stop_key, self.hotkey_stop, suppress=False)
            
            print(f"✅ Raccourcis: Start={start_key}, Pause={pause_key}, Stop={stop_key}")
        except Exception as e:
            print(f"⚠️ Erreur config raccourcis: {e}")
    
    def hotkey_start(self):
        """Raccourci pour démarrer"""
        self.root.after(0, self.start_bot)
    
    def hotkey_pause(self):
        """Raccourci pour pause"""
        self.root.after(0, self.toggle_pause)
    
    def hotkey_stop(self):
        """Raccourci pour arrêter"""
        self.root.after(0, self.stop_bot)
    
    def open_hotkeys_config(self):
        """Ouvre la fenêtre de configuration des raccourcis"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⌨️ Raccourcis clavier")
        dialog.geometry("400x350")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="⌨️ Raccourcis clavier", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=15)
        
        tk.Label(dialog, text="Configure les touches pour contrôler le bot:",
                font=('Segoe UI', 10), bg=self.colors['bg'], fg=self.colors['text2']).pack(pady=5)
        
        # Frame pour les raccourcis
        keys_frame = tk.Frame(dialog, bg=self.colors['bg2'], padx=20, pady=15)
        keys_frame.pack(fill='x', padx=20, pady=10)
        
        hotkeys = self.config.data.get("hotkeys", {"start": "F5", "pause": "F6", "stop": "F7"})
        
        # Démarrer
        start_frame = tk.Frame(keys_frame, bg=self.colors['bg2'])
        start_frame.pack(fill='x', pady=5)
        tk.Label(start_frame, text="▶️ Démarrer:", font=('Segoe UI', 11), width=15, anchor='w',
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        start_entry = tk.Entry(start_frame, width=10, bg=self.colors['bg3'], fg=self.colors['text'],
                              insertbackground=self.colors['text'], justify='center', font=('Segoe UI', 11))
        start_entry.insert(0, hotkeys.get("start", "F5"))
        start_entry.pack(side='left', padx=10)
        
        # Pause
        pause_frame = tk.Frame(keys_frame, bg=self.colors['bg2'])
        pause_frame.pack(fill='x', pady=5)
        tk.Label(pause_frame, text="⏸️ Pause:", font=('Segoe UI', 11), width=15, anchor='w',
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        pause_entry = tk.Entry(pause_frame, width=10, bg=self.colors['bg3'], fg=self.colors['text'],
                              insertbackground=self.colors['text'], justify='center', font=('Segoe UI', 11))
        pause_entry.insert(0, hotkeys.get("pause", "F6"))
        pause_entry.pack(side='left', padx=10)
        
        # Stop
        stop_frame = tk.Frame(keys_frame, bg=self.colors['bg2'])
        stop_frame.pack(fill='x', pady=5)
        tk.Label(stop_frame, text="⏹️ Arrêter:", font=('Segoe UI', 11), width=15, anchor='w',
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        stop_entry = tk.Entry(stop_frame, width=10, bg=self.colors['bg3'], fg=self.colors['text'],
                             insertbackground=self.colors['text'], justify='center', font=('Segoe UI', 11))
        stop_entry.insert(0, hotkeys.get("stop", "F7"))
        stop_entry.pack(side='left', padx=10)
        
        # Info
        tk.Label(dialog, text="💡 Exemples: F1, F5, ctrl+shift+s, alt+p",
                font=('Segoe UI', 9), bg=self.colors['bg'], fg=self.colors['text2']).pack(pady=10)
        
        def save_hotkeys():
            self.config.data["hotkeys"] = {
                "start": start_entry.get().strip(),
                "pause": pause_entry.get().strip(),
                "stop": stop_entry.get().strip()
            }
            self.config.save()
            
            # Mettre à jour l'affichage
            hotkeys = self.config.data["hotkeys"]
            hotkey_text = f"▶ {hotkeys['start']} | ⏸ {hotkeys['pause']} | ⏹ {hotkeys['stop']}"
            self.hotkey_label.config(text=hotkey_text)
            
            # Reconfigurer les raccourcis
            self.setup_hotkeys()
            
            self.log("✅ Raccourcis sauvegardés!")
            messagebox.showinfo("OK", "Raccourcis sauvegardés!")
            dialog.destroy()
        
        # Boutons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        tk.Button(btn_frame, text="❌ Annuler", font=('Segoe UI', 10),
                 bg=self.colors['bg3'], fg='white', width=12,
                 command=dialog.destroy).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['success'], fg='white', width=15,
                 command=save_hotkeys).pack(side='right', padx=5)
    
    def open_webhook_config(self):
        """Configure les notifications (Discord + Ntfy)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📱 Configuration Notifications")
        dialog.geometry("550x420")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="📱 Notifications Push", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=10)
        
        # === NTFY ===
        ntfy_frame = tk.LabelFrame(dialog, text="📲 Ntfy.sh (gratuit & recommande)", 
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['bg2'], fg=self.colors['text'], padx=15, pady=10)
        ntfy_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(ntfy_frame, text="Topic:", bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        ntfy_entry = tk.Entry(ntfy_frame, width=40, bg=self.colors['bg3'], fg=self.colors['text'],
                             insertbackground=self.colors['text'])
        ntfy_entry.insert(0, self.config.data.get("ntfy_topic", ""))
        ntfy_entry.pack(fill='x', pady=5)
        
        tk.Label(ntfy_frame, text="Installe l'app 'ntfy' sur ton tel, abonne-toi au meme topic",
                font=('Segoe UI', 8), bg=self.colors['bg2'], fg=self.colors['text2']).pack(anchor='w')
        
        # === DISCORD ===
        discord_frame = tk.LabelFrame(dialog, text="🎮 Discord Webhook", 
                                      font=('Segoe UI', 10, 'bold'),
                                      bg=self.colors['bg2'], fg=self.colors['text'], padx=15, pady=10)
        discord_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(discord_frame, text="URL Webhook:", bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        url_entry = tk.Entry(discord_frame, width=50, bg=self.colors['bg3'], fg=self.colors['text'],
                            insertbackground=self.colors['text'])
        url_entry.insert(0, self.config.data.get("discord_webhook", ""))
        url_entry.pack(fill='x', pady=5)
        
        tk.Label(discord_frame, text="Serveur Discord > Salon > Modifier > Integrations > Webhooks",
                font=('Segoe UI', 8), bg=self.colors['bg2'], fg=self.colors['text2']).pack(anchor='w')
        
        def test_ntfy():
            topic = ntfy_entry.get().strip()
            if topic:
                success = send_ntfy(topic, "Test Dofus Farm Bot - Ca marche!")
                if success:
                    messagebox.showinfo("Succes", "Notification envoyee!")
                else:
                    messagebox.showerror("Erreur", "Echec. Verifie le topic.")
            else:
                messagebox.showwarning("Attention", "Entre un topic!")
        
        def test_discord():
            url = url_entry.get().strip()
            if url:
                success = send_discord_webhook(url, "🧪 **Test Dofus Bot**\n\nLe webhook fonctionne!")
                if success:
                    messagebox.showinfo("Succes", "Message envoye!")
                else:
                    messagebox.showerror("Erreur", "Echec. Verifie l'URL.")
            else:
                messagebox.showwarning("Attention", "Entre une URL!")
        
        def save_config():
            self.config.data["ntfy_topic"] = ntfy_entry.get().strip()
            self.config.data["discord_webhook"] = url_entry.get().strip()
            self.config.save()
            
            has_notif = self.config.data["ntfy_topic"] or self.config.data["discord_webhook"]
            status = "✅ Configure" if has_notif else "❌ Non configure"
            self.webhook_label.config(text=f"Webhook: {status}")
            
            self.log("✅ Notifications sauvegardees!")
            messagebox.showinfo("OK", "Configuration sauvegardee!")
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
    
    def update_spells_preview(self):
        """Met à jour l'aperçu des sorts configurés"""
        spells = self.config.data.get("combat", {}).get("spells", [])
        active_spells = [s for s in spells if s.get("enabled", False)]
        
        if active_spells:
            preview_parts = []
            for s in active_spells:
                target_icon = "💚" if s.get("target") == "self" else "🎯"
                preview_parts.append(f"{target_icon}{s['name']}({s['key']})")
            preview = " ".join(preview_parts)
        else:
            preview = "Aucun sort configuré"
        
        if hasattr(self, 'spells_preview'):
            self.spells_preview.config(text=preview)
    
    def open_spell_config(self):
        """Ouvre la fenêtre de configuration des sorts"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🎯 Configuration des sorts")
        dialog.geometry("650x800")  # Plus grand
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        tk.Label(dialog, text="⚔️ Configuration des sorts de combat",
                font=('Segoe UI', 14, 'bold'), bg=self.colors['bg'], fg=self.colors['accent']).pack(pady=10)
        
        # Frame pour les sorts
        spells_frame = tk.Frame(dialog, bg=self.colors['bg2'], padx=20, pady=10)
        spells_frame.pack(fill='x', padx=20, pady=5)
        
        # Header
        header_frame = tk.Frame(spells_frame, bg=self.colors['bg2'])
        header_frame.pack(fill='x', pady=(0,5))
        tk.Label(header_frame, text="Actif", width=5, font=('Segoe UI', 9, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        tk.Label(header_frame, text="Nom", width=12, font=('Segoe UI', 9, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left', padx=10)
        tk.Label(header_frame, text="Touche", width=8, font=('Segoe UI', 9, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left', padx=10)
        tk.Label(header_frame, text="Cible", width=15, font=('Segoe UI', 9, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left', padx=10)
        
        # Recharger la config depuis le fichier
        self.config.data = self.config.load()
        
        if "combat" not in self.config.data:
            self.config.data["combat"] = {}
        
        spells = self.config.data["combat"].get("spells", [])
        
        # Debug
        print(f"\n=== CHARGEMENT CONFIG SORTS ===")
        print(f"Sorts trouvés: {len(spells)}")
        
        # S'assurer qu'on a 6 slots
        while len(spells) < 6:
            spells.append({"key": str(len(spells)+1), "name": f"Sort {len(spells)+1}", "enabled": False, "target": "enemy"})
        
        spell_widgets = []
        
        for i, spell in enumerate(spells[:6]):
            frame = tk.Frame(spells_frame, bg=self.colors['bg2'])
            frame.pack(fill='x', pady=3)
            
            # Checkbox activer
            enabled_var = tk.BooleanVar(value=spell.get("enabled", False))
            cb = tk.Checkbutton(frame, variable=enabled_var, bg=self.colors['bg2'],
                               selectcolor=self.colors['bg3'], activebackground=self.colors['bg2'])
            cb.pack(side='left', padx=(0,10))
            
            # Nom du sort
            name_entry = tk.Entry(frame, width=12, bg=self.colors['bg3'], fg=self.colors['text'],
                                 insertbackground=self.colors['text'])
            name_entry.insert(0, spell.get("name", f"Sort {i+1}"))
            name_entry.pack(side='left', padx=5)
            
            # Touche
            key_entry = tk.Entry(frame, width=6, bg=self.colors['bg3'], fg=self.colors['text'],
                                insertbackground=self.colors['text'], justify='center')
            key_entry.insert(0, spell.get("key", ""))
            key_entry.pack(side='left', padx=10)
            
            # Cible
            target_var = tk.StringVar(value=spell.get("target", "enemy"))
            target_frame = tk.Frame(frame, bg=self.colors['bg2'])
            target_frame.pack(side='left', padx=10)
            
            tk.Radiobutton(target_frame, text="🎯 Ennemi", variable=target_var, value="enemy",
                          bg=self.colors['bg2'], fg=self.colors['text'], selectcolor=self.colors['bg3'],
                          activebackground=self.colors['bg2']).pack(side='left')
            tk.Radiobutton(target_frame, text="💚 Moi", variable=target_var, value="self",
                          bg=self.colors['bg2'], fg=self.colors['text'], selectcolor=self.colors['bg3'],
                          activebackground=self.colors['bg2']).pack(side='left')
            
            spell_widgets.append({
                "enabled": enabled_var,
                "name": name_entry,
                "key": key_entry,
                "target": target_var
            })
        
        # Paramètres
        params_frame = tk.Frame(dialog, bg=self.colors['bg2'], padx=20, pady=10)
        params_frame.pack(fill='x', padx=20, pady=5)
        
        tk.Label(params_frame, text="⚙️ Paramètres", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w', pady=(0,5))
        
        # Touche fin de tour
        end_turn_frame = tk.Frame(params_frame, bg=self.colors['bg2'])
        end_turn_frame.pack(fill='x', pady=3)
        tk.Label(end_turn_frame, text="Touche fin de tour:", font=('Segoe UI', 10),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        end_turn_entry = tk.Entry(end_turn_frame, width=10, bg=self.colors['bg3'], fg=self.colors['text'],
                                  insertbackground=self.colors['text'], justify='center')
        end_turn_entry.insert(0, self.config.data.get("combat", {}).get("end_turn_key", "space"))
        end_turn_entry.pack(side='left', padx=10)
        
        # Délai entre sorts
        delay_frame = tk.Frame(params_frame, bg=self.colors['bg2'])
        delay_frame.pack(fill='x', pady=3)
        tk.Label(delay_frame, text="Délai entre sorts:", font=('Segoe UI', 10),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        spell_delay_entry = tk.Entry(delay_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'],
                                     insertbackground=self.colors['text'], justify='center')
        spell_delay_entry.insert(0, str(self.config.data.get("combat", {}).get("spell_delay", 0.5)))
        spell_delay_entry.pack(side='left', padx=10)
        tk.Label(delay_frame, text="sec", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        
        # Délai entre tours
        turn_frame = tk.Frame(params_frame, bg=self.colors['bg2'])
        turn_frame.pack(fill='x', pady=3)
        tk.Label(turn_frame, text="Délai entre tours:", font=('Segoe UI', 10),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        turn_delay_entry = tk.Entry(turn_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'],
                                    insertbackground=self.colors['text'], justify='center')
        turn_delay_entry.insert(0, str(self.config.data.get("combat", {}).get("turn_delay", 2.0)))
        turn_delay_entry.pack(side='left', padx=10)
        tk.Label(turn_frame, text="sec", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left')
        
        # ===== POSITIONS DES CIBLES =====
        pos_frame = tk.Frame(dialog, bg=self.colors['bg2'], padx=20, pady=10)
        pos_frame.pack(fill='x', padx=20, pady=5)
        
        tk.Label(pos_frame, text="📍 Positions des cibles (selon résolution)", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w', pady=(0,5))
        
        # Récupérer les positions actuelles
        positions = self.config.data.get("combat_positions", {})
        pos_2k = positions.get("2560x1440", {"self": [2006, 1032], "enemy": [2092, 1028]})
        pos_fhd = positions.get("1920x1080", {"self": [1489, 773], "enemy": [1547, 759]})
        
        # 2560x1440
        res_2k_frame = tk.Frame(pos_frame, bg=self.colors['bg2'])
        res_2k_frame.pack(fill='x', pady=2)
        tk.Label(res_2k_frame, text="2560x1440:", font=('Segoe UI', 9, 'bold'), width=10,
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        tk.Label(res_2k_frame, text="Moi X:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(5,2))
        self_2k_x = tk.Entry(res_2k_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        self_2k_x.insert(0, str(pos_2k["self"][0]))
        self_2k_x.pack(side='left')
        tk.Label(res_2k_frame, text="Y:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(5,2))
        self_2k_y = tk.Entry(res_2k_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        self_2k_y.insert(0, str(pos_2k["self"][1]))
        self_2k_y.pack(side='left')
        tk.Label(res_2k_frame, text="Ennemi X:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(15,2))
        enemy_2k_x = tk.Entry(res_2k_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        enemy_2k_x.insert(0, str(pos_2k["enemy"][0]))
        enemy_2k_x.pack(side='left')
        tk.Label(res_2k_frame, text="Y:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(5,2))
        enemy_2k_y = tk.Entry(res_2k_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        enemy_2k_y.insert(0, str(pos_2k["enemy"][1]))
        enemy_2k_y.pack(side='left')
        
        # 1920x1080
        res_fhd_frame = tk.Frame(pos_frame, bg=self.colors['bg2'])
        res_fhd_frame.pack(fill='x', pady=2)
        tk.Label(res_fhd_frame, text="1920x1080:", font=('Segoe UI', 9, 'bold'), width=10,
                bg=self.colors['bg2'], fg=self.colors['text']).pack(side='left')
        tk.Label(res_fhd_frame, text="Moi X:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(5,2))
        self_fhd_x = tk.Entry(res_fhd_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        self_fhd_x.insert(0, str(pos_fhd["self"][0]))
        self_fhd_x.pack(side='left')
        tk.Label(res_fhd_frame, text="Y:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(5,2))
        self_fhd_y = tk.Entry(res_fhd_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        self_fhd_y.insert(0, str(pos_fhd["self"][1]))
        self_fhd_y.pack(side='left')
        tk.Label(res_fhd_frame, text="Ennemi X:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(15,2))
        enemy_fhd_x = tk.Entry(res_fhd_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        enemy_fhd_x.insert(0, str(pos_fhd["enemy"][0]))
        enemy_fhd_x.pack(side='left')
        tk.Label(res_fhd_frame, text="Y:", font=('Segoe UI', 9),
                bg=self.colors['bg2'], fg=self.colors['text2']).pack(side='left', padx=(5,2))
        enemy_fhd_y = tk.Entry(res_fhd_frame, width=5, bg=self.colors['bg3'], fg=self.colors['text'], justify='center')
        enemy_fhd_y.insert(0, str(pos_fhd["enemy"][1]))
        enemy_fhd_y.pack(side='left')
        
        def save_spells():
            """Sauvegarde la configuration des sorts"""
            print("\n=== SAUVEGARDE DES SORTS ===")
            
            new_spells = []
            for i, w in enumerate(spell_widgets):
                spell_data = {
                    "enabled": w["enabled"].get(),
                    "name": w["name"].get(),
                    "key": w["key"].get(),
                    "target": w["target"].get()
                }
                new_spells.append(spell_data)
                if spell_data["enabled"]:
                    print(f"  Sort {i+1}: {spell_data['name']} ({spell_data['key']}) -> {spell_data['target']}")
            
            self.config.data["combat"]["spells"] = new_spells
            self.config.data["combat"]["end_turn_key"] = end_turn_entry.get()
            
            try:
                self.config.data["combat"]["spell_delay"] = float(spell_delay_entry.get())
            except:
                self.config.data["combat"]["spell_delay"] = 0.5
            
            try:
                self.config.data["combat"]["turn_delay"] = float(turn_delay_entry.get())
            except:
                self.config.data["combat"]["turn_delay"] = 2.0
            
            # Sauvegarder les positions
            try:
                self.config.data["combat_positions"] = {
                    "2560x1440": {
                        "self": [int(self_2k_x.get()), int(self_2k_y.get())],
                        "enemy": [int(enemy_2k_x.get()), int(enemy_2k_y.get())]
                    },
                    "1920x1080": {
                        "self": [int(self_fhd_x.get()), int(self_fhd_y.get())],
                        "enemy": [int(enemy_fhd_x.get()), int(enemy_fhd_y.get())]
                    }
                }
            except:
                pass
            
            success = self.config.save()
            
            if success:
                self.update_spells_preview()
                self.log("✅ Sorts sauvegardés!")
                messagebox.showinfo("OK", "Configuration sauvegardée!")
            else:
                messagebox.showerror("Erreur", "Erreur de sauvegarde!")
            
            dialog.destroy()
        
        # ===== BOUTONS EN BAS =====
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill='x', padx=20, pady=15, side='bottom')
        
        tk.Button(btn_frame, text="❌ Annuler", font=('Segoe UI', 11),
                 bg=self.colors['bg3'], fg='white', width=15, height=2,
                 command=dialog.destroy).pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="💾 SAUVEGARDER", font=('Segoe UI', 12, 'bold'),
                 bg=self.colors['success'], fg='white', width=18, height=2,
                 command=save_spells).pack(side='right', padx=10)
    
    def log(self, message):
        """Ajoute un message au log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
    
    def bot_callback(self, msg_type, data):
        """Callback depuis le bot"""
        if msg_type == "log":
            self.root.after(0, lambda: self.log(data))
        elif msg_type == "stats":
            self.root.after(0, lambda: self.update_stats_display(data))
    
    def update_stats_display(self, stats):
        """Met à jour l'affichage des stats"""
        self.stat_labels["total"].config(text=str(stats["total_harvested"]))
        self.stat_labels["combats"].config(text=str(stats["combats"]))
    
    def update_time(self):
        """Met à jour le temps de session"""
        try:
            if self.bot and self.bot.running and self.bot.stats["session_start"]:
                elapsed = datetime.now() - self.bot.stats["session_start"]
                hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.stat_labels["time"].config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Calculer le rate
                if elapsed.total_seconds() > 0:
                    rate = self.bot.stats["total_harvested"] / (elapsed.total_seconds() / 3600)
                    self.stat_labels["rate"].config(text=f"{rate:.0f}")
            
            if self.root.winfo_exists():
                self.root.after(1000, self.update_time)
        except:
            pass
    
    def update_threshold(self):
        try:
            val = int(self.threshold_var.get()) / 100
            self.config.data["match_threshold"] = val
            self.config.save()
        except:
            pass
    
    def update_delay(self):
        try:
            val = float(self.delay_var.get())
            if val > 0:
                self.config.data["harvest_delay"] = val
                self.config.save()
                # Log seulement si changement significatif
                if hasattr(self, '_last_delay_logged') and self._last_delay_logged != val:
                    self.log(f"⏱️ Délai récolte: {val}s")
                self._last_delay_logged = val
        except:
            pass
    
    def start_bot(self):
        """Démarre le bot"""
        # Vérifier qu'il y a des templates
        has_templates = False
        for res_name in self.config.data["resources"]:
            res_dir = self.config.get_resource_dir(res_name)
            if any(f.endswith('.png') for f in os.listdir(res_dir)):
                has_templates = True
                break
        
        if not has_templates:
            messagebox.showwarning("Attention", 
                "Aucun template trouvé!\n\nAjoute une ressource et calibre-la d'abord.")
            return
        
        self.log("⏳ Démarrage dans 3 secondes...")
        self.status_label.config(text="⏳ Démarrage...", fg=self.colors['warning'])
        self.root.after(3000, self._start_bot_delayed)
        
        self.start_btn.config(state='disabled')
    
    def _start_bot_delayed(self):
        self.bot = BotEngine(self.config, self.bot_callback)
        self.bot_thread = threading.Thread(target=self.bot.run, daemon=True)
        self.bot_thread.start()
        
        self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
        self.pause_btn.config(state='normal')
        self.stop_btn.config(state='normal')
    
    def pause_bot(self):
        """Pause/reprend le bot"""
        if self.bot:
            self.bot.pause()
            if self.bot.paused:
                self.pause_btn.config(text="▶️ REPRENDRE")
                self.status_label.config(text="⏸️ En pause", fg=self.colors['warning'])
            else:
                self.pause_btn.config(text="⏸️ PAUSE")
                self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
    
    def toggle_pause(self):
        """Alias pour pause_bot"""
        self.pause_bot()
    
    def stop_bot(self):
        """Arrête le bot"""
        if self.bot:
            self.bot.stop()
            self.bot = None
        
        self.status_label.config(text="⚪ Arrêté", fg=self.colors['text2'])
        self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️ PAUSE")
        self.stop_btn.config(state='disabled')


# ============================================================
#                FENÊTRE DE CALIBRATION
# ============================================================

class CalibrationWindow:
    def __init__(self, config, resource_name):
        self.config = config
        self.resource_name = resource_name
        self.screenshot = None
        self.tk_image = None
        self.pil_image = None
        self.scale = 1.0
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.templates_added = 0
        self.root = None
        self.canvas = None
        self.image_on_canvas = None
    
    def take_screenshot(self):
        """Prend un screenshot"""
        try:
            pil_image = ImageGrab.grab()
            self.screenshot = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            h, w = self.screenshot.shape[:2]
            print(f"📸 Capture: {w}x{h} pixels")
            
            self.scale = min(1400/w, 900/h, 1.0)
            
            if self.scale < 1.0:
                new_w = int(w * self.scale)
                new_h = int(h * self.scale)
                display = cv2.resize(self.screenshot, (new_w, new_h))
            else:
                display = self.screenshot.copy()
            
            display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            self.pil_image = Image.fromarray(display_rgb)
            
            return True
        except Exception as e:
            print(f"❌ Erreur screenshot: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def on_mouse_down(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
    
    def on_mouse_drag(self, event):
        if self.start_x is not None and self.start_y is not None:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, cur_x, cur_y,
                outline='#00ff00', width=3)
    
    def on_mouse_up(self, event):
        if self.start_x is None or self.start_y is None:
            return
        
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        
        x1 = int(min(self.start_x, end_x) / self.scale)
        y1 = int(min(self.start_y, end_y) / self.scale)
        x2 = int(max(self.start_x, end_x) / self.scale)
        y2 = int(max(self.start_y, end_y) / self.scale)
        
        if x2 - x1 < 20 or y2 - y1 < 20:
            print("⚠️ Sélection trop petite! (min 20x20 pixels)")
            self.start_x = None
            self.start_y = None
            return
        
        template = self.screenshot[y1:y2, x1:x2].copy()
        
        res_dir = self.config.get_resource_dir(self.resource_name)
        existing = len([f for f in os.listdir(res_dir) if f.endswith('.png')])
        template_path = os.path.join(res_dir, f"template_{existing}.png")
        cv2.imwrite(template_path, template)
        
        self.templates_added += 1
        print(f"✅ Template #{self.templates_added} sauvegardé ({x2-x1}x{y2-y1} pixels)")
        
        mid_x = (self.start_x + end_x) / 2
        mid_y = (self.start_y + end_y) / 2
        self.canvas.create_oval(mid_x-15, mid_y-15, mid_x+15, mid_y+15, 
                                fill='#00ff00', outline='white', width=2)
        self.canvas.create_text(mid_x, mid_y, text=str(self.templates_added),
                               fill='black', font=('Arial', 12, 'bold'))
        
        self.info_label.config(text=f"Templates ajoutés: {self.templates_added}")
        
        self.start_x = None
        self.start_y = None
    
    def new_screenshot(self):
        """Prend un nouveau screenshot"""
        self.root.withdraw()
        
        print("📸 Nouveau screenshot dans 2 secondes...")
        time.sleep(2)
        
        if self.take_screenshot():
            self.tk_image = ImageTk.PhotoImage(self.pil_image, master=self.root)
            self.canvas.delete("all")
            self.image_on_canvas = self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)
            self.canvas.config(scrollregion=(0, 0, self.tk_image.width(), self.tk_image.height()))
        
        self.root.deiconify()
        self.root.lift()
    
    def run(self):
        """Lance la fenêtre de calibration"""
        print(f"\n{'='*50}")
        print(f"📸 Calibration de: {self.resource_name}")
        print(f"{'='*50}")
        print("⏳ Screenshot dans 2 secondes...")
        print("👉 Mets DOFUS au premier plan maintenant!")
        time.sleep(2)
        
        if not self.take_screenshot():
            print("❌ Échec de la capture d'écran")
            return
        
        print("✅ Screenshot capturé!")
        
        # Créer une fenêtre Tk indépendante
        self.root = tk.Tk()
        self.root.title(f"🎯 Calibration: {self.resource_name}")
        self.root.configure(bg='#1a1a2e')
        self.root.geometry("1400x900")
        
        # Créer PhotoImage avec le bon master
        self.tk_image = ImageTk.PhotoImage(self.pil_image, master=self.root)
        
        # Header
        header = tk.Frame(self.root, bg='#16213e', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text=f"🎯 Dessine un rectangle autour de: {self.resource_name}",
                font=('Segoe UI', 14, 'bold'), bg='#16213e', fg='#ffd700').pack(side='left', padx=20, pady=15)
        
        self.info_label = tk.Label(header, text="Templates ajoutés: 0",
                                   font=('Segoe UI', 12, 'bold'), bg='#16213e', fg='#4ecca3')
        self.info_label.pack(side='right', padx=20)
        
        # Frame pour canvas
        canvas_frame = tk.Frame(self.root, bg='#1a1a2e')
        canvas_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollbars
        h_scroll = tk.Scrollbar(canvas_frame, orient='horizontal')
        h_scroll.pack(side='bottom', fill='x')
        v_scroll = tk.Scrollbar(canvas_frame, orient='vertical')
        v_scroll.pack(side='right', fill='y')
        
        # Canvas
        self.canvas = tk.Canvas(canvas_frame, cursor='crosshair', bg='#2a2a2a',
                               xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set,
                               highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        
        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)
        
        # Afficher l'image
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, self.tk_image.width(), self.tk_image.height()))
        
        # Bind souris
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        
        # Boutons
        btn_frame = tk.Frame(self.root, bg='#1a1a2e', height=70)
        btn_frame.pack(fill='x', padx=10, pady=10)
        btn_frame.pack_propagate(False)
        
        tk.Button(btn_frame, text="📷 Nouveau Screenshot", font=('Segoe UI', 11, 'bold'),
                 bg='#0f3460', fg='white', padx=20, pady=10,
                 command=self.new_screenshot, cursor='hand2').pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="✅ Terminé", font=('Segoe UI', 12, 'bold'),
                 bg='#4ecca3', fg='black', padx=40, pady=10,
                 command=self.root.destroy, cursor='hand2').pack(side='right', padx=10)
        
        print("🖱️ Dessine un rectangle autour de la ressource!")
        
        self.root.mainloop()


# ============================================================
#                         MAIN
# ============================================================

if __name__ == "__main__":
    pyautogui.FAILSAFE = False
    gui = BotGUI()
    gui.run()