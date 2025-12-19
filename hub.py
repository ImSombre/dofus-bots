"""
🎮 Dofus Bot Hub v2.0
Hub central pour tous les bots Dofus
- Détection automatique des bots (.py)
- Design original
- Mise à jour GitHub
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

try:
    import requests
    HAS_REQUESTS = True
except:
    HAS_REQUESTS = False

# ============================================================
#                    SYSTÈME DE MISE À JOUR
# ============================================================
class Updater:
    def __init__(self, config, callback=None):
        self.config = config
        self.callback = callback
        self.current_version = self.get_local_version()
    
    def log(self, msg):
        if self.callback:
            self.callback(msg)
    
    def get_local_version(self):
        version_file = os.path.join(self.config.base_dir, "version.json")
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return json.load(f).get("version", "1.0.0")
            except:
                pass
        return "1.0.0"
    
    def save_local_version(self, version):
        version_file = os.path.join(self.config.base_dir, "version.json")
        try:
            with open(version_file, 'w') as f:
                json.dump({"version": version, "updated": datetime.now().isoformat()}, f)
        except:
            pass
    
    def get_github_url(self):
        user = self.config.data.get("github_user", "")
        repo = self.config.data.get("github_repo", "dofus-bots")
        if not user:
            return None
        return f"https://raw.githubusercontent.com/{user}/{repo}/main"
    
    def check_for_updates(self):
        if not HAS_REQUESTS:
            return None
        
        github_url = self.get_github_url()
        if not github_url:
            return None
        
        try:
            self.log("🔍 Vérification...")
            url = f"{github_url}/version.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                remote_data = response.json()
                remote_version = remote_data.get("version", "0.0.0")
                
                if self.compare_versions(remote_version, self.current_version) > 0:
                    self.log(f"✨ v{remote_version} disponible!")
                    return remote_data
                else:
                    self.log("✅ À jour")
                    return None
            else:
                self.log("⚠️ GitHub non accessible")
                return None
        except Exception as e:
            self.log(f"⚠️ Erreur: {e}")
            return None
    
    def compare_versions(self, v1, v2):
        try:
            p1 = [int(x) for x in v1.split('.')]
            p2 = [int(x) for x in v2.split('.')]
            for i in range(max(len(p1), len(p2))):
                a = p1[i] if i < len(p1) else 0
                b = p2[i] if i < len(p2) else 0
                if a > b: return 1
                if a < b: return -1
            return 0
        except:
            return 0
    
    def download_update(self, update_info):
        if not HAS_REQUESTS:
            return False
        
        github_url = self.get_github_url()
        if not github_url:
            return False
        
        try:
            files = update_info.get("files", [])
            delete_files = update_info.get("delete", [])
            new_version = update_info.get("version", self.current_version)
            
            # 1. Supprimer les fichiers marqués pour suppression
            for file_path in delete_files:
                try:
                    local_path = os.path.join(self.config.base_dir, file_path)
                    if os.path.exists(local_path):
                        os.remove(local_path)
                        self.log(f"🗑️ Supprimé: {file_path}")
                except Exception as e:
                    self.log(f"⚠️ Impossible de supprimer: {file_path}")
            
            # 2. Télécharger les nouveaux fichiers
            self.log(f"📥 Téléchargement...")
            
            for file_info in files:
                file_path = file_info.get("path", "")
                file_url = f"{github_url}/{file_path}"
                
                try:
                    response = requests.get(file_url, timeout=30)
                    if response.status_code == 200:
                        local_path = os.path.join(self.config.base_dir, file_path)
                        os.makedirs(os.path.dirname(local_path) if os.path.dirname(local_path) else ".", exist_ok=True)
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        self.log(f"✅ {file_path}")
                except:
                    self.log(f"❌ {file_path}")
            
            self.save_local_version(new_version)
            self.current_version = new_version
            self.log(f"✅ Mise à jour v{new_version} installée!")
            return True
        except Exception as e:
            self.log(f"❌ Erreur: {e}")
            return False


# ============================================================
#                    THÈME (ORIGINAL)
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
    'text2': '#8b8b9e'
}

# Couleurs pour les bots
BOT_COLORS = ['#00d26a', '#e94560', '#4cc9f0', '#ff9f1c', '#9b59b6', '#1abc9c', '#e74c3c', '#3498db']

# ============================================================
#                    CONFIGURATION
# ============================================================
class Config:
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
        return {"github_user": "", "github_repo": "dofus-bots"}
    
    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except:
            pass


# ============================================================
#                    DÉTECTION DES BOTS
# ============================================================
class BotScanner:
    # Icônes basées sur le nom du fichier
    ICONS = {
        'anti': '😴',
        'afk': '😴',
        'podcast': '🎵',
        'audio': '🎵',
        'music': '🎵',
        'farm': '🌾',
        'combat': '⚔️',
        'travel': '🗺️',
        'chat': '💬',
        'alert': '🔔',
        'fish': '🎣',
        'craft': '🔨',
        'bot': '🤖'
    }
    
    @classmethod
    def scan_directory(cls, base_dir):
        """Scanne le dossier pour trouver les fichiers .py (bots)"""
        bots = []
        color_index = 0
        
        # Fichiers à ignorer
        ignore = ['hub.py', '__init__.py', 'setup.py', 'config.py', 'updater.py']
        
        # Scanner le dossier principal
        for filename in os.listdir(base_dir):
            if filename.endswith('.py') and filename.lower() not in ignore:
                filepath = os.path.join(base_dir, filename)
                bot = cls.create_bot_info(filename, filepath, color_index)
                if bot:
                    bots.append(bot)
                    color_index = (color_index + 1) % len(BOT_COLORS)
        
        # Scanner le sous-dossier "bots" s'il existe
        bots_dir = os.path.join(base_dir, "bots")
        if os.path.exists(bots_dir):
            for root, dirs, files in os.walk(bots_dir):
                for filename in files:
                    if filename.endswith('.py') and filename.lower() not in ignore:
                        filepath = os.path.join(root, filename)
                        bot = cls.create_bot_info(filename, filepath, color_index)
                        if bot:
                            bots.append(bot)
                            color_index = (color_index + 1) % len(BOT_COLORS)
        
        return bots
    
    @classmethod
    def create_bot_info(cls, filename, filepath, color_index):
        """Crée les infos d'un bot à partir du fichier"""
        name = filename.replace('.py', '').replace('_', ' ').replace('-', ' ').title()
        name_lower = filename.lower()
        
        # Trouver l'icône
        icon = '🤖'
        for key, ico in cls.ICONS.items():
            if key in name_lower:
                icon = ico
                break
        
        # Lire la description depuis le fichier (première docstring)
        description = "Bot Dofus"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(500)
                if '"""' in content:
                    start = content.find('"""') + 3
                    end = content.find('"""', start)
                    if end > start:
                        doc = content[start:end].strip()
                        # Prendre juste les 2 premières lignes
                        lines = [l.strip() for l in doc.split('\n') if l.strip()]
                        description = '\n'.join(lines[:2]) if lines else "Bot Dofus"
        except:
            pass
        
        return {
            "name": f"{icon} {name}",
            "description": description,
            "script": filepath,
            "color": BOT_COLORS[color_index],
            "icon": icon
        }


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================
class HubGUI:
    VERSION = "2.0.0"
    
    def __init__(self):
        self.config = Config()
        self.bots = BotScanner.scan_directory(self.config.base_dir)
        self.updater = Updater(self.config, self.update_status)
        self.update_available = None
        
        self.setup_window()
        self.create_widgets()
        
        # Vérifier les mises à jour au démarrage
        threading.Thread(target=self.check_updates_async, daemon=True).start()
    
    def update_status(self, msg):
        try:
            self.root.after(0, lambda: self.status_label.config(text=msg))
        except:
            pass
    
    def check_updates_async(self):
        time.sleep(1)
        update_info = self.updater.check_for_updates()
        if update_info:
            self.update_available = update_info
            self.root.after(0, self.show_update_button)
    
    def show_update_button(self):
        version = self.update_available.get("version", "?")
        self.update_btn = tk.Button(self.header_right, text=f"⬆️ v{version}", 
                                    font=('Segoe UI', 9, 'bold'),
                                    bg=THEME['warning'], fg='black',
                                    command=self.do_update, cursor='hand2')
        self.update_btn.pack(side='left', padx=5)
    
    def do_update(self):
        if not self.update_available:
            return
        
        changelog = self.update_available.get("changelog", "Améliorations diverses")
        version = self.update_available.get("version", "?")
        
        result = messagebox.askyesno("Mise à jour",
            f"Nouvelle version disponible: v{version}\n\n"
            f"Changelog:\n{changelog}\n\n"
            "Mettre à jour maintenant?")
        
        if result:
            self.update_btn.config(state='disabled', text="⏳...")
            threading.Thread(target=self._update_thread, daemon=True).start()
    
    def _update_thread(self):
        success = self.updater.download_update(self.update_available)
        if success:
            self.root.after(0, lambda: self.update_btn.pack_forget())
            self.root.after(0, lambda: messagebox.showinfo("✅ Mise à jour",
                "Mise à jour installée!\n\nRedémarre le Hub pour appliquer."))
        else:
            self.root.after(0, lambda: self.update_btn.config(state='normal', text="⬆️ Réessayer"))
        
        self.setup_window()
        self.create_widgets()
    
    def run(self):
        self.root.mainloop()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title(f"🎮 Dofus Bot Hub v{self.VERSION}")
        self.root.geometry("800x600")
        self.root.configure(bg=THEME['bg'])
        
        # Centrer
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 800) // 2
        y = (self.root.winfo_screenheight() - 600) // 2
        self.root.geometry(f"800x600+{x}+{y}")
    
    def create_widgets(self):
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=THEME['bg2'], height=100)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # Titre
        title_frame = tk.Frame(header, bg=THEME['bg2'])
        title_frame.pack(side='left', padx=30, pady=15)
        
        tk.Label(title_frame, text="🎮 DOFUS BOT HUB", font=('Segoe UI', 24, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(anchor='w')
        tk.Label(title_frame, text=f"v{self.VERSION}", font=('Segoe UI', 10),
                bg=THEME['bg2'], fg=THEME['text2']).pack(anchor='w')
        
        # Boutons droite
        self.header_right = tk.Frame(header, bg=THEME['bg2'])
        self.header_right.pack(side='right', padx=30)
        
        tk.Button(self.header_right, text="🔄 Actualiser", font=('Segoe UI', 9),
                 bg=THEME['bg3'], fg=THEME['text'],
                 command=self.refresh_bots).pack(side='left', padx=5)
        
        tk.Button(self.header_right, text="⚙️ Paramètres", font=('Segoe UI', 9),
                 bg=THEME['bg3'], fg=THEME['text'],
                 command=self.open_settings).pack(side='left', padx=5)
        
        # ===== CONTENU =====
        main = tk.Frame(self.root, bg=THEME['bg'])
        main.pack(fill='both', expand=True, padx=30, pady=20)
        
        # Info
        info_text = f"📂 {len(self.bots)} bot(s) trouvé(s) • Clique sur LANCER pour démarrer"
        self.info_label = tk.Label(main, text=info_text, font=('Segoe UI', 11),
                                   bg=THEME['bg'], fg=THEME['text2'])
        self.info_label.pack(anchor='w', pady=(0, 15))
        
        # Zone scrollable pour les bots
        canvas = tk.Canvas(main, bg=THEME['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
        self.bots_frame = tk.Frame(canvas, bg=THEME['bg'])
        
        self.bots_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.bots_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Scroll avec molette
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Créer les cartes
        self.create_bot_cards()
        
        # ===== FOOTER =====
        footer = tk.Frame(self.root, bg=THEME['bg2'], height=50)
        footer.pack(fill='x', side='bottom')
        footer.pack_propagate(False)
        
        self.status_label = tk.Label(footer, text="✅ Prêt", font=('Segoe UI', 9),
                                     bg=THEME['bg2'], fg=THEME['text2'])
        self.status_label.pack(side='left', padx=20, pady=15)
        
        tk.Label(footer, text="📁 " + self.config.base_dir, font=('Segoe UI', 8),
                bg=THEME['bg2'], fg=THEME['text2']).pack(side='right', padx=20, pady=15)
    
    def create_bot_cards(self):
        """Crée les cartes des bots"""
        # Vider
        for widget in self.bots_frame.winfo_children():
            widget.destroy()
        
        if not self.bots:
            tk.Label(self.bots_frame, 
                    text="❌ Aucun bot trouvé!\n\nMets tes fichiers .py dans ce dossier:\n" + self.config.base_dir,
                    font=('Segoe UI', 12), bg=THEME['bg'], fg=THEME['warning'],
                    justify='center').pack(pady=50)
            return
        
        for bot in self.bots:
            self.create_bot_card(bot)
    
    def create_bot_card(self, bot):
        """Crée une carte pour un bot"""
        card = tk.Frame(self.bots_frame, bg=THEME['card'], padx=20, pady=15)
        card.pack(fill='x', pady=8, padx=5)
        
        # Gauche: infos
        left = tk.Frame(card, bg=THEME['card'])
        left.pack(side='left', fill='both', expand=True)
        
        name_label = tk.Label(left, text=bot['name'], font=('Segoe UI', 14, 'bold'),
                             bg=THEME['card'], fg=THEME['text'])
        name_label.pack(anchor='w')
        
        desc_label = tk.Label(left, text=bot['description'], font=('Segoe UI', 9),
                             bg=THEME['card'], fg=THEME['text2'], justify='left',
                             wraplength=400)
        desc_label.pack(anchor='w', pady=3)
        
        # Droite: bouton (ne pas inclure dans le hover)
        btn = tk.Button(card, text="▶️ LANCER", font=('Segoe UI', 11, 'bold'),
                       bg=bot['color'], fg='white', width=12,
                       command=lambda b=bot: self.launch_bot(b),
                       cursor='hand2')
        btn.pack(side='right', padx=10)
        
        # Effet hover (seulement sur card, left, et labels)
        hover_widgets = [card, left, name_label, desc_label]
        
        def on_enter(e):
            for w in hover_widgets:
                w.config(bg=THEME['accent2'])
        
        def on_leave(e):
            for w in hover_widgets:
                w.config(bg=THEME['card'])
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
    
    def launch_bot(self, bot):
        """Lance un bot"""
        script = bot['script']
        
        if not os.path.exists(script):
            messagebox.showerror("Erreur", f"Fichier non trouvé:\n{script}")
            return
        
        self.status_label.config(text=f"🚀 Lancement de {bot['name']}...")
        
        try:
            if sys.platform == 'win32':
                # Essayer pythonw d'abord, sinon python
                try:
                    subprocess.Popen(['pythonw', script],
                                   cwd=os.path.dirname(script),
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                except:
                    subprocess.Popen(['python', script],
                                   cwd=os.path.dirname(script),
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(['python3', script],
                               cwd=os.path.dirname(script))
            
            self.status_label.config(text=f"✅ {bot['name']} lancé!")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer:\n{e}")
            self.status_label.config(text=f"❌ Erreur")
    
    def refresh_bots(self):
        """Actualise la liste des bots"""
        self.bots = BotScanner.scan_directory(self.config.base_dir)
        self.info_label.config(text=f"📂 {len(self.bots)} bot(s) trouvé(s) • Clique sur LANCER pour démarrer")
        self.create_bot_cards()
        self.status_label.config(text="🔄 Liste actualisée!")
    
    def open_settings(self):
        """Ouvre les paramètres"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Paramètres")
        dialog.geometry("500x350")
        dialog.configure(bg=THEME['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrer
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 350) // 2
        dialog.geometry(f"500x350+{x}+{y}")
        
        tk.Label(dialog, text="⚙️ Paramètres", font=('Segoe UI', 18, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=15)
        
        content = tk.Frame(dialog, bg=THEME['bg2'], padx=20, pady=15)
        content.pack(fill='both', expand=True, padx=20, pady=10)
        
        # GitHub
        tk.Label(content, text="🔄 Mise à jour GitHub (optionnel)", font=('Segoe UI', 11, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(anchor='w', pady=(0, 10))
        
        row = tk.Frame(content, bg=THEME['bg2'])
        row.pack(fill='x', pady=5)
        tk.Label(row, text="Username:", width=12, anchor='w',
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        user_entry = tk.Entry(row, width=25, bg=THEME['bg3'], fg=THEME['text'])
        user_entry.insert(0, self.config.data.get("github_user", ""))
        user_entry.pack(side='left', padx=10)
        
        row = tk.Frame(content, bg=THEME['bg2'])
        row.pack(fill='x', pady=5)
        tk.Label(row, text="Repository:", width=12, anchor='w',
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left')
        repo_entry = tk.Entry(row, width=25, bg=THEME['bg3'], fg=THEME['text'])
        repo_entry.insert(0, self.config.data.get("github_repo", "dofus-bots"))
        repo_entry.pack(side='left', padx=10)
        
        # Info
        tk.Label(content, text=f"\n📂 Dossier des bots:\n{self.config.base_dir}\n\n"
                              f"💡 Mets tes fichiers .py dans ce dossier\n"
                              f"   et clique 🔄 Actualiser",
                font=('Segoe UI', 9), bg=THEME['bg2'], fg=THEME['text2'],
                justify='left').pack(anchor='w', pady=10)
        
        # Boutons
        btn_frame = tk.Frame(dialog, bg=THEME['bg'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        def save():
            self.config.data["github_user"] = user_entry.get().strip()
            self.config.data["github_repo"] = repo_entry.get().strip()
            self.config.save()
            dialog.destroy()
            messagebox.showinfo("✅", "Paramètres sauvegardés!")
        
        tk.Button(btn_frame, text="Fermer", bg=THEME['bg3'], fg=THEME['text'],
                 command=dialog.destroy).pack(side='left')
        tk.Button(btn_frame, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 command=save).pack(side='right')
        
        def open_folder():
            if sys.platform == 'win32':
                os.startfile(self.config.base_dir)
            else:
                subprocess.run(['xdg-open', self.config.base_dir])
        
        tk.Button(btn_frame, text="📁 Ouvrir dossier", bg=THEME['info'], fg='white',
                 command=open_folder).pack(side='right', padx=10)


# ============================================================
#                    MAIN
# ============================================================
if __name__ == "__main__":
    app = HubGUI()
    app.run()