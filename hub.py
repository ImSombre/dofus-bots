"""
🎮 Dofus Bot Hub v1.0
Hub central pour tous les bots Dofus
Système de mise à jour automatique via GitHub
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import json
import threading
import time
from datetime import datetime

# Pour les mises à jour
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================
#                    CONFIGURATION
# ============================================================

# 🔧 CONFIGURE TON GITHUB ICI
GITHUB_USER = "ton-username"  # Ton nom d'utilisateur GitHub
GITHUB_REPO = "dofus-bots"     # Nom du repo
GITHUB_BRANCH = "main"         # Branche (main ou master)

# URL de base pour les fichiers raw
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

# Version locale
LOCAL_VERSION = "1.0.0"

# ============================================================
#                    THÈME
# ============================================================
THEME = {
    'bg': '#0a0a12',
    'bg2': '#12121c',
    'bg3': '#1a1a2e',
    'card': '#16213e',
    'accent': '#e94560',
    'accent2': '#0f3460',
    'success': '#00d26a',
    'warning': '#ff9f1c',
    'info': '#4cc9f0',
    'text': '#ffffff',
    'text2': '#8b8b9e',
    'gradient1': '#667eea',
    'gradient2': '#764ba2'
}

# ============================================================
#                    GESTIONNAIRE DE CHEMINS
# ============================================================
class PathManager:
    def __init__(self):
        try:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.base_dir = os.getcwd()
        
        self.bots_dir = os.path.join(self.base_dir, "bots")
        self.config_file = os.path.join(self.base_dir, "hub_config.json")
        self.version_file = os.path.join(self.base_dir, "version.json")
        
        # Créer les dossiers si nécessaire
        os.makedirs(self.bots_dir, exist_ok=True)
        os.makedirs(os.path.join(self.bots_dir, "farming"), exist_ok=True)
        os.makedirs(os.path.join(self.bots_dir, "combat"), exist_ok=True)


# ============================================================
#                    SYSTÈME DE MISE À JOUR
# ============================================================
class Updater:
    def __init__(self, paths, callback=None):
        self.paths = paths
        self.callback = callback
        self.current_version = self.get_local_version()
    
    def log(self, msg):
        print(f"[Updater] {msg}")
        if self.callback:
            self.callback(msg)
    
    def get_local_version(self):
        """Récupère la version locale"""
        if os.path.exists(self.paths.version_file):
            try:
                with open(self.paths.version_file, 'r') as f:
                    data = json.load(f)
                    return data.get("version", LOCAL_VERSION)
            except:
                pass
        return LOCAL_VERSION
    
    def save_local_version(self, version):
        """Sauvegarde la version locale"""
        try:
            with open(self.paths.version_file, 'w') as f:
                json.dump({"version": version, "updated": datetime.now().isoformat()}, f)
        except:
            pass
    
    def check_for_updates(self):
        """Vérifie si une mise à jour est disponible"""
        if not HAS_REQUESTS:
            self.log("⚠️ Module 'requests' non disponible")
            return None
        
        try:
            self.log("🔍 Vérification des mises à jour...")
            
            # Télécharger version.json depuis GitHub
            url = f"{GITHUB_RAW_URL}/version.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                remote_data = response.json()
                remote_version = remote_data.get("version", "0.0.0")
                
                self.log(f"   Version locale: {self.current_version}")
                self.log(f"   Version distante: {remote_version}")
                
                if self.compare_versions(remote_version, self.current_version) > 0:
                    self.log(f"✨ Nouvelle version disponible: {remote_version}")
                    return remote_data
                else:
                    self.log("✅ Vous êtes à jour!")
                    return None
            else:
                self.log(f"⚠️ Impossible de vérifier (code {response.status_code})")
                return None
                
        except Exception as e:
            self.log(f"⚠️ Erreur vérification: {e}")
            return None
    
    def compare_versions(self, v1, v2):
        """Compare deux versions (retourne 1 si v1 > v2, -1 si v1 < v2, 0 si égales)"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            return 0
        except:
            return 0
    
    def download_update(self, update_info):
        """Télécharge et applique la mise à jour"""
        if not HAS_REQUESTS:
            return False
        
        try:
            files_to_update = update_info.get("files", [])
            new_version = update_info.get("version", self.current_version)
            
            self.log(f"📥 Téléchargement de {len(files_to_update)} fichiers...")
            
            for file_info in files_to_update:
                file_path = file_info.get("path", "")
                file_url = f"{GITHUB_RAW_URL}/{file_path}"
                
                self.log(f"   📄 {file_path}")
                
                try:
                    response = requests.get(file_url, timeout=30)
                    if response.status_code == 200:
                        # Créer le dossier si nécessaire
                        local_path = os.path.join(self.paths.base_dir, file_path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        
                        # Écrire le fichier
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                    else:
                        self.log(f"      ⚠️ Erreur téléchargement")
                except Exception as e:
                    self.log(f"      ❌ {e}")
            
            # Sauvegarder la nouvelle version
            self.save_local_version(new_version)
            self.current_version = new_version
            
            self.log(f"✅ Mise à jour {new_version} installée!")
            return True
            
        except Exception as e:
            self.log(f"❌ Erreur mise à jour: {e}")
            return False


# ============================================================
#                    DÉFINITION DES BOTS
# ============================================================
BOTS = [
    {
        "id": "farming",
        "name": "🌾 Farming Bot",
        "description": "Récolte automatique de ressources\nDétection MP • Discord • Combat auto",
        "version": "6.0",
        "script": "bots/farming/bot.py",
        "color": "#00d26a",
        "icon": "🌾"
    },
    {
        "id": "combat",
        "name": "🗡️ Combat Bot",
        "description": "Farm de mobs automatique\nRecord & Replay • Détection MP • Discord",
        "version": "2.0",
        "script": "bots/combat/bot_combat.py",
        "color": "#e94560",
        "icon": "🗡️"
    }
]


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================
class HubGUI:
    def __init__(self):
        self.paths = PathManager()
        self.updater = Updater(self.paths, self.update_log)
        self.update_available = None
        
        self.setup_window()
        self.create_widgets()
        
        # Vérifier les mises à jour au démarrage
        threading.Thread(target=self.check_updates_async, daemon=True).start()
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🎮 Dofus Bot Hub")
        self.root.geometry("800x600")
        self.root.configure(bg=THEME['bg'])
        self.root.resizable(True, True)
        
        # Centrer la fenêtre
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 800) // 2
        y = (self.root.winfo_screenheight() - 600) // 2
        self.root.geometry(f"800x600+{x}+{y}")
    
    def create_widgets(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=THEME['bg2'], height=100)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # Logo et titre
        title_frame = tk.Frame(header, bg=THEME['bg2'])
        title_frame.pack(side='left', padx=30, pady=15)
        
        tk.Label(title_frame, text="🎮 DOFUS BOT HUB", font=('Segoe UI', 24, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(anchor='w')
        
        self.version_label = tk.Label(title_frame, text=f"v{self.updater.current_version}", 
                                      font=('Segoe UI', 10),
                                      bg=THEME['bg2'], fg=THEME['text2'])
        self.version_label.pack(anchor='w')
        
        # Bouton mise à jour (caché par défaut)
        self.update_btn = tk.Button(header, text="⬆️ MISE À JOUR DISPONIBLE", 
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=THEME['warning'], fg='black',
                                    command=self.do_update, cursor='hand2')
        # Ne pas pack - sera affiché si mise à jour disponible
        
        # Status
        self.status_frame = tk.Frame(header, bg=THEME['bg2'])
        self.status_frame.pack(side='right', padx=30)
        
        self.status_label = tk.Label(self.status_frame, text="🔍 Vérification...", 
                                     font=('Segoe UI', 10),
                                     bg=THEME['bg2'], fg=THEME['text2'])
        self.status_label.pack()
        
        # ===== MAIN CONTENT =====
        main = tk.Frame(self.root, bg=THEME['bg'])
        main.pack(fill='both', expand=True, padx=30, pady=20)
        
        # Titre section
        tk.Label(main, text="Sélectionne un bot pour commencer", font=('Segoe UI', 12),
                bg=THEME['bg'], fg=THEME['text2']).pack(anchor='w', pady=(0, 15))
        
        # Grille des bots
        self.bots_frame = tk.Frame(main, bg=THEME['bg'])
        self.bots_frame.pack(fill='both', expand=True)
        
        self.create_bot_cards()
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg=THEME['bg2'], height=50)
        footer.pack(fill='x', side='bottom')
        footer.pack_propagate(False)
        
        # Log area (petit)
        self.log_label = tk.Label(footer, text="Prêt", font=('Segoe UI', 9),
                                  bg=THEME['bg2'], fg=THEME['text2'])
        self.log_label.pack(side='left', padx=20, pady=15)
        
        # Bouton paramètres
        tk.Button(footer, text="⚙️ Paramètres", font=('Segoe UI', 9),
                 bg=THEME['bg3'], fg=THEME['text'],
                 command=self.open_settings, cursor='hand2').pack(side='right', padx=20, pady=10)
    
    def create_bot_cards(self):
        """Crée les cartes des bots"""
        for i, bot in enumerate(BOTS):
            self.create_bot_card(bot, i)
    
    def create_bot_card(self, bot, index):
        """Crée une carte pour un bot"""
        # Frame de la carte
        card = tk.Frame(self.bots_frame, bg=THEME['card'], padx=20, pady=15)
        card.pack(fill='x', pady=8)
        
        # Effet hover
        def on_enter(e):
            card.config(bg=THEME['accent2'])
            for child in card.winfo_children():
                try:
                    child.config(bg=THEME['accent2'])
                except:
                    pass
        
        def on_leave(e):
            card.config(bg=THEME['card'])
            for child in card.winfo_children():
                try:
                    child.config(bg=THEME['card'])
                except:
                    pass
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        
        # Contenu gauche
        left = tk.Frame(card, bg=THEME['card'])
        left.pack(side='left', fill='both', expand=True)
        
        # Titre avec icône
        title_frame = tk.Frame(left, bg=THEME['card'])
        title_frame.pack(anchor='w')
        
        tk.Label(title_frame, text=bot['name'], font=('Segoe UI', 16, 'bold'),
                bg=THEME['card'], fg=THEME['text']).pack(side='left')
        
        tk.Label(title_frame, text=f"v{bot['version']}", font=('Segoe UI', 9),
                bg=THEME['card'], fg=bot['color']).pack(side='left', padx=10)
        
        # Description
        tk.Label(left, text=bot['description'], font=('Segoe UI', 10),
                bg=THEME['card'], fg=THEME['text2'], justify='left').pack(anchor='w', pady=5)
        
        # Bouton lancer
        btn = tk.Button(card, text="▶️ LANCER", font=('Segoe UI', 11, 'bold'),
                       bg=bot['color'], fg='white', width=12,
                       command=lambda b=bot: self.launch_bot(b), cursor='hand2')
        btn.pack(side='right', padx=10)
        
        # Status du bot (fichier existe?)
        script_path = os.path.join(self.paths.base_dir, bot['script'])
        if os.path.exists(script_path):
            status_text = "✅ Installé"
            status_color = THEME['success']
        else:
            status_text = "❌ Non trouvé"
            status_color = THEME['accent']
        
        tk.Label(card, text=status_text, font=('Segoe UI', 9),
                bg=THEME['card'], fg=status_color).pack(side='right', padx=10)
    
    def launch_bot(self, bot):
        """Lance un bot"""
        script_path = os.path.join(self.paths.base_dir, bot['script'])
        
        if not os.path.exists(script_path):
            messagebox.showerror("Erreur", 
                f"Le fichier {bot['script']} n'existe pas!\n\n"
                "Vérifie que les fichiers du bot sont dans le bon dossier.")
            return
        
        self.update_log(f"🚀 Lancement de {bot['name']}...")
        
        try:
            # Lancer le bot avec pythonw (sans console)
            if sys.platform == 'win32':
                subprocess.Popen(['pythonw', script_path], 
                               cwd=os.path.dirname(script_path),
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(['python3', script_path],
                               cwd=os.path.dirname(script_path))
            
            self.update_log(f"✅ {bot['name']} lancé!")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer le bot:\n{e}")
            self.update_log(f"❌ Erreur: {e}")
    
    def check_updates_async(self):
        """Vérifie les mises à jour en arrière-plan"""
        time.sleep(1)  # Petite pause pour laisser l'UI se charger
        
        update_info = self.updater.check_for_updates()
        
        if update_info:
            self.update_available = update_info
            self.root.after(0, self.show_update_available)
        else:
            self.root.after(0, lambda: self.status_label.config(text="✅ À jour"))
    
    def show_update_available(self):
        """Affiche qu'une mise à jour est disponible"""
        new_version = self.update_available.get("version", "?")
        self.status_label.config(text=f"⬆️ v{new_version} disponible!", fg=THEME['warning'])
        self.update_btn.pack(side='right', padx=20, pady=25)
    
    def do_update(self):
        """Lance la mise à jour"""
        if not self.update_available:
            return
        
        result = messagebox.askyesno("Mise à jour", 
            f"Nouvelle version disponible: v{self.update_available.get('version')}\n\n"
            f"Changelog:\n{self.update_available.get('changelog', 'Aucune info')}\n\n"
            "Voulez-vous mettre à jour maintenant?")
        
        if result:
            self.update_log("📥 Mise à jour en cours...")
            self.update_btn.config(state='disabled', text="⏳ Mise à jour...")
            
            # Lancer dans un thread
            threading.Thread(target=self._do_update_thread, daemon=True).start()
    
    def _do_update_thread(self):
        """Thread de mise à jour"""
        success = self.updater.download_update(self.update_available)
        
        if success:
            self.root.after(0, self._update_complete)
        else:
            self.root.after(0, lambda: messagebox.showerror("Erreur", "Échec de la mise à jour"))
            self.root.after(0, lambda: self.update_btn.config(state='normal', text="⬆️ MISE À JOUR DISPONIBLE"))
    
    def _update_complete(self):
        """Mise à jour terminée"""
        self.update_btn.pack_forget()
        self.version_label.config(text=f"v{self.updater.current_version}")
        self.status_label.config(text="✅ Mis à jour!", fg=THEME['success'])
        
        messagebox.showinfo("Mise à jour", 
            "Mise à jour installée avec succès!\n\n"
            "Redémarrez le Hub pour appliquer les changements.")
    
    def update_log(self, msg):
        """Met à jour le log"""
        self.root.after(0, lambda: self.log_label.config(text=msg))
    
    def open_settings(self):
        """Ouvre les paramètres"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Paramètres")
        dialog.geometry("500x400")
        dialog.configure(bg=THEME['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centre
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        dialog.geometry(f"500x400+{x}+{y}")
        
        tk.Label(dialog, text="⚙️ Paramètres", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=20)
        
        # Frame contenu
        content = tk.Frame(dialog, bg=THEME['bg2'], padx=20, pady=15)
        content.pack(fill='both', expand=True, padx=20, pady=10)
        
        # GitHub config
        tk.Label(content, text="Configuration GitHub (pour les mises à jour)", 
                font=('Segoe UI', 11, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(anchor='w', pady=(0, 10))
        
        # Username
        row1 = tk.Frame(content, bg=THEME['bg2'])
        row1.pack(fill='x', pady=5)
        tk.Label(row1, text="Username:", width=12, anchor='w',
                bg=THEME['bg2'], fg=THEME['text2']).pack(side='left')
        user_entry = tk.Entry(row1, width=30, bg=THEME['bg3'], fg=THEME['text'])
        user_entry.insert(0, GITHUB_USER)
        user_entry.pack(side='left', padx=10)
        
        # Repo
        row2 = tk.Frame(content, bg=THEME['bg2'])
        row2.pack(fill='x', pady=5)
        tk.Label(row2, text="Repository:", width=12, anchor='w',
                bg=THEME['bg2'], fg=THEME['text2']).pack(side='left')
        repo_entry = tk.Entry(row2, width=30, bg=THEME['bg3'], fg=THEME['text'])
        repo_entry.insert(0, GITHUB_REPO)
        repo_entry.pack(side='left', padx=10)
        
        # Info
        tk.Label(content, text="💡 Pour activer les mises à jour automatiques:\n"
                              "1. Crée un repo GitHub public\n"
                              "2. Mets ton username et repo ci-dessus\n"
                              "3. Upload les fichiers du hub sur GitHub",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2'],
                justify='left').pack(anchor='w', pady=20)
        
        # Version info
        tk.Label(content, text=f"Version actuelle: {self.updater.current_version}",
                font=('Segoe UI', 10), bg=THEME['bg2'], fg=THEME['info']).pack(anchor='w')
        
        # Dossier
        tk.Label(content, text=f"Dossier: {self.paths.base_dir}",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(anchor='w', pady=5)
        
        # Bouton fermer
        tk.Button(dialog, text="Fermer", font=('Segoe UI', 10),
                 bg=THEME['bg3'], fg=THEME['text'],
                 command=dialog.destroy).pack(pady=15)


# ============================================================
#                    MAIN
# ============================================================
if __name__ == "__main__":
    app = HubGUI()
    app.run()
