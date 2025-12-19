"""
🎮 Dofus Bot Hub v1.0
Hub central pour tous les bots Dofus
Système de mise à jour automatique via GitHub
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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
class HubConfig:
    def __init__(self):
        try:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.base_dir = os.getcwd()
        
        self.config_file = os.path.join(self.base_dir, "hub_config.json")
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Config par défaut
        return {
            "github_user": "",
            "github_repo": "dofus-bots",
            "github_branch": "main",
            "first_run": True
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            return True
        except:
            return False
    
    def get_github_url(self):
        user = self.data.get("github_user", "")
        repo = self.data.get("github_repo", "dofus-bots")
        branch = self.data.get("github_branch", "main")
        
        if not user:
            return None
        
        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}"


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
    def __init__(self, paths, config, callback=None):
        self.paths = paths
        self.config = config
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
        
        github_url = self.config.get_github_url()
        if not github_url:
            self.log("⚠️ GitHub non configuré")
            return None
        
        try:
            self.log("🔍 Vérification des mises à jour...")
            
            # Télécharger version.json depuis GitHub
            url = f"{github_url}/version.json"
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
        """Compare deux versions"""
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
        
        github_url = self.config.get_github_url()
        if not github_url:
            return False
        
        try:
            files_to_update = update_info.get("files", [])
            new_version = update_info.get("version", self.current_version)
            
            self.log(f"📥 Téléchargement de {len(files_to_update)} fichiers...")
            
            for file_info in files_to_update:
                file_path = file_info.get("path", "")
                file_url = f"{github_url}/{file_path}"
                
                self.log(f"   📄 {file_path}")
                
                try:
                    response = requests.get(file_url, timeout=30)
                    if response.status_code == 200:
                        local_path = os.path.join(self.paths.base_dir, file_path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                    else:
                        self.log(f"      ⚠️ Erreur téléchargement")
                except Exception as e:
                    self.log(f"      ❌ {e}")
            
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
#                    ASSISTANT DE CONFIGURATION
# ============================================================
class SetupWizard:
    def __init__(self, parent, config, on_complete):
        self.config = config
        self.on_complete = on_complete
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🚀 Configuration initiale")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg=THEME['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 600) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        # Header
        tk.Label(self.dialog, text="🎮 Bienvenue dans Dofus Bot Hub!", 
                font=('Segoe UI', 20, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=20)
        
        tk.Label(self.dialog, text="Configure les mises à jour automatiques (optionnel)", 
                font=('Segoe UI', 11),
                bg=THEME['bg'], fg=THEME['text2']).pack()
        
        # Frame principale
        main = tk.Frame(self.dialog, bg=THEME['bg2'], padx=30, pady=20)
        main.pack(fill='both', expand=True, padx=30, pady=20)
        
        # Instructions
        instructions = """
📋 Pour activer les mises à jour automatiques:

1. Va sur github.com et crée un compte (gratuit)

2. Crée un "Repository":
   • Clique sur le "+" en haut à droite
   • Clique sur "New repository"
   • Nom: dofus-bots
   • ⚠️ Coche "Public" !
   • Clique "Create repository"

3. Upload les fichiers du Hub sur ton repo

4. Entre ton username GitHub ci-dessous:
"""
        
        tk.Label(main, text=instructions, font=('Segoe UI', 10),
                bg=THEME['bg2'], fg=THEME['text'], justify='left').pack(anchor='w')
        
        # Username entry
        user_frame = tk.Frame(main, bg=THEME['bg2'])
        user_frame.pack(fill='x', pady=10)
        
        tk.Label(user_frame, text="GitHub Username:", font=('Segoe UI', 11, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        
        self.user_entry = tk.Entry(user_frame, width=25, font=('Segoe UI', 12),
                                   bg=THEME['bg3'], fg=THEME['text'],
                                   insertbackground=THEME['text'])
        self.user_entry.pack(side='left', padx=15)
        self.user_entry.insert(0, self.config.data.get("github_user", ""))
        
        # Info
        tk.Label(main, text="💡 Tu peux aussi faire ça plus tard dans les paramètres",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2']).pack(pady=10)
        
        # Boutons
        btn_frame = tk.Frame(self.dialog, bg=THEME['bg'])
        btn_frame.pack(fill='x', padx=30, pady=15)
        
        tk.Button(btn_frame, text="⏭️ Passer (configurer plus tard)", 
                 font=('Segoe UI', 10),
                 bg=THEME['bg3'], fg=THEME['text'],
                 command=self.skip, cursor='hand2').pack(side='left')
        
        tk.Button(btn_frame, text="✅ Sauvegarder et continuer", 
                 font=('Segoe UI', 11, 'bold'),
                 bg=THEME['success'], fg='white',
                 command=self.save, cursor='hand2').pack(side='right')
    
    def save(self):
        username = self.user_entry.get().strip()
        self.config.data["github_user"] = username
        self.config.data["first_run"] = False
        self.config.save()
        
        self.dialog.destroy()
        self.on_complete()
    
    def skip(self):
        self.config.data["first_run"] = False
        self.config.save()
        
        self.dialog.destroy()
        self.on_complete()


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================
class HubGUI:
    def __init__(self):
        self.paths = PathManager()
        self.config = HubConfig()
        self.updater = Updater(self.paths, self.config, self.update_log)
        self.update_available = None
        
        self.setup_window()
        self.create_widgets()
        
        # Premier lancement = assistant de config
        if self.config.data.get("first_run", True):
            self.root.after(500, self.show_setup_wizard)
        else:
            # Vérifier les mises à jour au démarrage
            threading.Thread(target=self.check_updates_async, daemon=True).start()
    
    def run(self):
        self.root.mainloop()
    
    def show_setup_wizard(self):
        SetupWizard(self.root, self.config, self.on_setup_complete)
    
    def on_setup_complete(self):
        # Rafraîchir l'updater avec la nouvelle config
        self.updater = Updater(self.paths, self.config, self.update_log)
        # Vérifier les mises à jour
        threading.Thread(target=self.check_updates_async, daemon=True).start()
    
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
        self.update_btn = tk.Button(header, text="⬆️ MISE À JOUR", 
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=THEME['warning'], fg='black',
                                    command=self.do_update, cursor='hand2')
        
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
        
        # Log area
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
        card = tk.Frame(self.bots_frame, bg=THEME['card'], padx=20, pady=15)
        card.pack(fill='x', pady=8)
        
        # Effet hover
        def on_enter(e):
            card.config(bg=THEME['accent2'])
            for child in card.winfo_children():
                try:
                    child.config(bg=THEME['accent2'])
                    for subchild in child.winfo_children():
                        try:
                            subchild.config(bg=THEME['accent2'])
                        except:
                            pass
                except:
                    pass
        
        def on_leave(e):
            card.config(bg=THEME['card'])
            for child in card.winfo_children():
                try:
                    child.config(bg=THEME['card'])
                    for subchild in child.winfo_children():
                        try:
                            subchild.config(bg=THEME['card'])
                        except:
                            pass
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
        
        # Status du bot
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
        time.sleep(1)
        
        # Vérifier si GitHub est configuré
        if not self.config.data.get("github_user"):
            self.root.after(0, lambda: self.status_label.config(text="⚙️ GitHub non configuré"))
            return
        
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
            
            threading.Thread(target=self._do_update_thread, daemon=True).start()
    
    def _do_update_thread(self):
        """Thread de mise à jour"""
        success = self.updater.download_update(self.update_available)
        
        if success:
            self.root.after(0, self._update_complete)
        else:
            self.root.after(0, lambda: messagebox.showerror("Erreur", "Échec de la mise à jour"))
            self.root.after(0, lambda: self.update_btn.config(state='normal', text="⬆️ MISE À JOUR"))
    
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
        dialog.geometry("550x450")
        dialog.configure(bg=THEME['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centre
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 550) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 450) // 2
        dialog.geometry(f"550x450+{x}+{y}")
        
        tk.Label(dialog, text="⚙️ Paramètres", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=15)
        
        # Frame contenu
        content = tk.Frame(dialog, bg=THEME['bg2'], padx=25, pady=20)
        content.pack(fill='both', expand=True, padx=20, pady=10)
        
        # GitHub config
        tk.Label(content, text="🔄 Configuration GitHub (mises à jour)", 
                font=('Segoe UI', 12, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(anchor='w', pady=(0, 15))
        
        # Username
        row1 = tk.Frame(content, bg=THEME['bg2'])
        row1.pack(fill='x', pady=8)
        tk.Label(row1, text="Username GitHub:", width=15, anchor='w',
                font=('Segoe UI', 10),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        user_entry = tk.Entry(row1, width=25, font=('Segoe UI', 11),
                             bg=THEME['bg3'], fg=THEME['text'],
                             insertbackground=THEME['text'])
        user_entry.insert(0, self.config.data.get("github_user", ""))
        user_entry.pack(side='left', padx=10)
        
        # Repo
        row2 = tk.Frame(content, bg=THEME['bg2'])
        row2.pack(fill='x', pady=8)
        tk.Label(row2, text="Nom du repo:", width=15, anchor='w',
                font=('Segoe UI', 10),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        repo_entry = tk.Entry(row2, width=25, font=('Segoe UI', 11),
                             bg=THEME['bg3'], fg=THEME['text'],
                             insertbackground=THEME['text'])
        repo_entry.insert(0, self.config.data.get("github_repo", "dofus-bots"))
        repo_entry.pack(side='left', padx=10)
        
        # Aide
        help_text = """
💡 Comment ça marche:

1. Crée un compte sur github.com (gratuit)
2. Crée un repo public nommé "dofus-bots"  
3. Upload tous les fichiers du Hub
4. Entre ton username ci-dessus
5. Quand tu fais une modif, upload les fichiers
   → Tous les utilisateurs reçoivent la mise à jour !
"""
        tk.Label(content, text=help_text, font=('Segoe UI', 9),
                bg=THEME['bg2'], fg=THEME['text2'], justify='left').pack(anchor='w', pady=10)
        
        # Infos
        tk.Label(content, text=f"📂 Dossier: {self.paths.base_dir}",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['info']).pack(anchor='w', pady=5)
        
        # Boutons
        btn_frame = tk.Frame(dialog, bg=THEME['bg'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        def save_settings():
            self.config.data["github_user"] = user_entry.get().strip()
            self.config.data["github_repo"] = repo_entry.get().strip() or "dofus-bots"
            self.config.save()
            
            # Rafraîchir l'updater
            self.updater = Updater(self.paths, self.config, self.update_log)
            
            messagebox.showinfo("Sauvegardé", "Paramètres sauvegardés!")
            dialog.destroy()
        
        tk.Button(btn_frame, text="Annuler", font=('Segoe UI', 10),
                 bg=THEME['bg3'], fg=THEME['text'],
                 command=dialog.destroy).pack(side='left')
        
        tk.Button(btn_frame, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                 bg=THEME['success'], fg='white',
                 command=save_settings).pack(side='right')


# ============================================================
#                    MAIN
# ============================================================
if __name__ == "__main__":
    app = HubGUI()
    app.run()
