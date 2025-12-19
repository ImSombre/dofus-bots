"""
🧰 Outils v1.0
Boîte à outils Dofus Retro
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import time
import os
import json
from datetime import datetime

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except:
    HAS_PYAUTOGUI = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except:
    HAS_PIL = False

# ============================================================
#                    THÈME
# ============================================================
THEME = {
    'bg': '#0a0a12',
    'bg2': '#12121c',
    'bg3': '#1a1a2e',
    'card': '#16213e',
    'accent': '#e94560',
    'success': '#00d26a',
    'warning': '#ff9f1c',
    'info': '#4cc9f0',
    'text': '#ffffff',
    'text2': '#8b8b9e'
}

# ============================================================
#                    CONFIG
# ============================================================
class Config:
    def __init__(self):
        try:
            self.dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.dir = os.getcwd()
        self.file = os.path.join(self.dir, "outils_config.json")
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"notes": "", "chat_msgs": [], "chat_interval": 300}
    
    def save(self):
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except:
            pass


# ============================================================
#                    AUTO-RECONNECT
# ============================================================
class AutoReconnect:
    def __init__(self, log):
        self.log = log
        self.running = False
    
    def start(self, interval):
        if not HAS_PIL:
            self.log("❌ PIL requis: pip install pillow")
            return
        self.running = True
        self.interval = interval
        threading.Thread(target=self._run, daemon=True).start()
        self.log(f"🔄 Auto-Reconnect ON ({interval}s)")
    
    def stop(self):
        self.running = False
        self.log("🔄 Auto-Reconnect OFF")
    
    def _run(self):
        while self.running:
            if self._check_disconnect():
                self._reconnect()
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_disconnect(self):
        try:
            img = ImageGrab.grab()
            w, h = img.size
            cx, cy = w//2, h//2
            
            # Check center pixels
            points = [(cx, cy), (cx-100, cy), (cx+100, cy)]
            gray = 0
            for x, y in points:
                r, g, b = img.getpixel((x, y))[:3]
                if r < 60 and g < 60 and b < 60:
                    gray += 1
            return gray >= 2
        except:
            return False
    
    def _reconnect(self):
        if not HAS_PYAUTOGUI:
            return
        self.log("⚠️ Déconnexion! Reconnexion...")
        try:
            img = ImageGrab.grab()
            cx, cy = img.size[0]//2, img.size[1]//2
            pyautogui.click(cx, cy)
            time.sleep(0.5)
            pyautogui.press('enter')
            self.log("✅ Reconnexion tentée")
        except:
            pass


# ============================================================
#                    AUTO-CLICKER
# ============================================================
class AutoClicker:
    def __init__(self, log):
        self.log = log
        self.running = False
        self.count = 0
    
    def start(self, ms, pos=None):
        if not HAS_PYAUTOGUI:
            self.log("❌ pyautogui requis")
            return
        self.running = True
        self.ms = ms
        self.pos = pos
        self.count = 0
        threading.Thread(target=self._run, daemon=True).start()
        self.log(f"🖱️ Auto-Clicker ON ({ms}ms)")
    
    def stop(self):
        self.running = False
        self.log(f"🖱️ Auto-Clicker OFF ({self.count} clics)")
    
    def _run(self):
        while self.running:
            try:
                if self.pos:
                    pyautogui.click(self.pos[0], self.pos[1])
                else:
                    pyautogui.click()
                self.count += 1
            except:
                pass
            time.sleep(self.ms / 1000)


# ============================================================
#                    AUTO-CHAT
# ============================================================
class AutoChat:
    def __init__(self, log):
        self.log = log
        self.running = False
    
    def start(self, msgs, interval, batch=1):
        if not HAS_PYAUTOGUI:
            self.log("❌ pyautogui requis")
            return
        if not msgs:
            self.log("❌ Aucun message")
            return
        self.running = True
        self.msgs = msgs
        self.interval = interval
        self.batch = min(batch, len(msgs))  # Pas plus que le nombre de messages
        self.idx = 0
        threading.Thread(target=self._run, daemon=True).start()
        self.log(f"💬 Auto-Chat ON ({interval}s, {batch} msg/fois)")
    
    def stop(self):
        self.running = False
        self.log("💬 Auto-Chat OFF")
    
    def _run(self):
        while self.running:
            # Envoyer plusieurs messages d'un coup
            for i in range(self.batch):
                if not self.running:
                    break
                msg = self.msgs[(self.idx + i) % len(self.msgs)]
                self._send(msg)
                if i < self.batch - 1:
                    time.sleep(1.5)  # Pause entre les messages du même batch
            
            self.idx = (self.idx + self.batch) % len(self.msgs)
            
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _send(self, msg):
        try:
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.typewrite(msg, interval=0.02)
            time.sleep(0.1)
            pyautogui.press('enter')
            self.log(f"💬 {msg[:25]}...")
        except:
            pass


# ============================================================
#                    GUI
# ============================================================
class App:
    def __init__(self):
        self.cfg = Config()
        self.reconnect = AutoReconnect(self.log)
        self.clicker = AutoClicker(self.log)
        self.chat_running = False
        self.pixel_running = False
        self.mp_running = False
        
        self.root = tk.Tk()
        self.root.title("🧰 Outils v1.0")
        self.root.geometry("750x600")
        self.root.configure(bg=THEME['bg'])
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        
        # Center
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 750) // 2
        y = (self.root.winfo_screenheight() - 600) // 2
        self.root.geometry(f"750x600+{x}+{y}")
        
        self.build()
    
    def run(self):
        self.root.mainloop()
    
    def build(self):
        # Header
        hdr = tk.Frame(self.root, bg=THEME['bg2'], height=50)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🧰 OUTILS", font=('Segoe UI', 16, 'bold'),
                bg=THEME['bg2'], fg=THEME['text']).pack(side='left', padx=15, pady=10)
        
        # Tabs
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=THEME['bg'])
        style.configure('TNotebook.Tab', background=THEME['bg3'], 
                       foreground=THEME['text'], padding=[12, 6])
        style.map('TNotebook.Tab', background=[('selected', THEME['card'])])
        
        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tab_reconnect(nb)
        self.tab_clicker(nb)
        self.tab_chat(nb)
        self.tab_pixel(nb)
        self.tab_mp_detector(nb)
        self.tab_notif(nb)
        self.tab_notes(nb)
        self.tab_calc(nb)
        
        # Log
        self.log_label = tk.Label(self.root, text="✅ Prêt", font=('Segoe UI', 9),
                                  bg=THEME['bg2'], fg=THEME['text2'])
        self.log_label.pack(fill='x', side='bottom', ipady=8)
    
    # === TAB: RECONNECT ===
    def tab_reconnect(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="🔄 Reconnect")
        
        tk.Label(tab, text="🔄 Auto-Reconnect", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=15)
        tk.Label(tab, text="Détecte les déconnexions et reconnecte auto",
                font=('Segoe UI', 10), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        f = tk.Frame(tab, bg=THEME['card'], padx=20, pady=15)
        f.pack(pady=20, padx=40, fill='x')
        
        r = tk.Frame(f, bg=THEME['card'])
        r.pack()
        tk.Label(r, text="Vérifier toutes les", bg=THEME['card'], 
                fg=THEME['text']).pack(side='left')
        self.reconnect_int = tk.Spinbox(r, from_=3, to=60, width=4)
        self.reconnect_int.delete(0, 'end')
        self.reconnect_int.insert(0, "5")
        self.reconnect_int.pack(side='left', padx=5)
        tk.Label(r, text="secondes", bg=THEME['card'], 
                fg=THEME['text']).pack(side='left')
        
        self.reconnect_btn = tk.Button(tab, text="▶️ DÉMARRER", font=('Segoe UI', 11, 'bold'),
                                       bg=THEME['success'], fg='white', width=18,
                                       command=self.toggle_reconnect)
        self.reconnect_btn.pack(pady=15)
    
    def toggle_reconnect(self):
        if self.reconnect.running:
            self.reconnect.stop()
            self.reconnect_btn.config(text="▶️ DÉMARRER", bg=THEME['success'])
        else:
            self.reconnect.start(int(self.reconnect_int.get()))
            self.reconnect_btn.config(text="⏹️ ARRÊTER", bg=THEME['accent'])
    
    # === TAB: CLICKER ===
    def tab_clicker(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="🖱️ Clicker")
        
        tk.Label(tab, text="🖱️ Auto-Clicker", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=15)
        
        f = tk.Frame(tab, bg=THEME['card'], padx=20, pady=15)
        f.pack(pady=15, padx=40, fill='x')
        
        # Interval
        r1 = tk.Frame(f, bg=THEME['card'])
        r1.pack(pady=5)
        tk.Label(r1, text="Intervalle:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.clicker_ms = tk.Spinbox(r1, from_=50, to=10000, width=7, increment=50)
        self.clicker_ms.delete(0, 'end')
        self.clicker_ms.insert(0, "1000")
        self.clicker_ms.pack(side='left', padx=5)
        tk.Label(r1, text="ms", bg=THEME['card'], fg=THEME['text2']).pack(side='left')
        
        # Position
        r2 = tk.Frame(f, bg=THEME['card'])
        r2.pack(pady=5)
        self.clicker_fixed = tk.BooleanVar()
        tk.Checkbutton(r2, text="Position fixe:", variable=self.clicker_fixed,
                      bg=THEME['card'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left')
        self.clicker_x = tk.Entry(r2, width=5, bg=THEME['bg3'], fg=THEME['text'])
        self.clicker_x.insert(0, "0")
        self.clicker_x.pack(side='left', padx=2)
        tk.Label(r2, text=",", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.clicker_y = tk.Entry(r2, width=5, bg=THEME['bg3'], fg=THEME['text'])
        self.clicker_y.insert(0, "0")
        self.clicker_y.pack(side='left', padx=2)
        tk.Button(r2, text="📍", bg=THEME['info'], fg='white',
                 command=self.capture_pos).pack(side='left', padx=5)
        
        # Count
        self.clicker_count = tk.Label(f, text="Clics: 0", bg=THEME['card'], fg=THEME['info'])
        self.clicker_count.pack(pady=5)
        
        self.clicker_btn = tk.Button(tab, text="▶️ DÉMARRER", font=('Segoe UI', 11, 'bold'),
                                     bg=THEME['success'], fg='white', width=18,
                                     command=self.toggle_clicker)
        self.clicker_btn.pack(pady=15)
    
    def capture_pos(self):
        if HAS_PYAUTOGUI:
            x, y = pyautogui.position()
            self.clicker_x.delete(0, 'end')
            self.clicker_x.insert(0, str(x))
            self.clicker_y.delete(0, 'end')
            self.clicker_y.insert(0, str(y))
            self.clicker_fixed.set(True)
            self.log(f"📍 ({x}, {y})")
    
    def toggle_clicker(self):
        if self.clicker.running:
            self.clicker.stop()
            self.clicker_btn.config(text="▶️ DÉMARRER", bg=THEME['success'])
        else:
            ms = int(self.clicker_ms.get())
            pos = None
            if self.clicker_fixed.get():
                pos = (int(self.clicker_x.get()), int(self.clicker_y.get()))
            self.clicker.start(ms, pos)
            self.clicker_btn.config(text="⏹️ ARRÊTER", bg=THEME['accent'])
            self.update_count()
    
    def update_count(self):
        if self.clicker.running:
            self.clicker_count.config(text=f"Clics: {self.clicker.count}")
            self.root.after(200, self.update_count)
    
    # === TAB: CHAT ===
    def tab_chat(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="💬 Chat")
        
        tk.Label(tab, text="💬 Auto-Chat Multi-Profils", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        # === LISTE DES PROFILS ===
        self.chat_profiles = self.cfg.data.get("chat_profiles", {
            "Défaut": {"msgs": ["Up métier!"], "interval": 300, "batch": 1, "active": False}
        })
        
        # Frame principale avec scroll
        main_frame = tk.Frame(tab, bg=THEME['bg'])
        main_frame.pack(fill='both', expand=True, padx=20)
        
        # Liste des profils (gauche)
        left = tk.Frame(main_frame, bg=THEME['card'], padx=10, pady=10)
        left.pack(side='left', fill='y', padx=(0,10))
        
        tk.Label(left, text="📁 Profils", font=('Segoe UI', 11, 'bold'),
                bg=THEME['card'], fg=THEME['text']).pack(pady=(0,10))
        
        self.profile_frame = tk.Frame(left, bg=THEME['card'])
        self.profile_frame.pack(fill='both', expand=True)
        
        self.profile_vars = {}  # {name: BooleanVar}
        self.profile_buttons = {}  # {name: button}
        self.refresh_profile_list()
        
        # Boutons ajouter/supprimer
        btn_f = tk.Frame(left, bg=THEME['card'])
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="➕", bg=THEME['success'], fg='white', width=4,
                 command=self.add_profile).pack(side='left', padx=2)
        tk.Button(btn_f, text="🗑️", bg=THEME['accent'], fg='white', width=4,
                 command=self.del_profile).pack(side='left', padx=2)
        
        # Éditeur de profil (droite)
        right = tk.Frame(main_frame, bg=THEME['card'], padx=15, pady=10)
        right.pack(side='left', fill='both', expand=True)
        
        self.edit_label = tk.Label(right, text="✏️ Éditer: (sélectionne un profil)", 
                                   font=('Segoe UI', 11, 'bold'),
                                   bg=THEME['card'], fg=THEME['text'])
        self.edit_label.pack(anchor='w')
        
        tk.Label(right, text="Messages (un par ligne):", bg=THEME['card'], 
                fg=THEME['text2']).pack(anchor='w', pady=(10,0))
        self.chat_text = tk.Text(right, height=6, bg=THEME['bg3'], fg=THEME['text'],
                                font=('Consolas', 10))
        self.chat_text.pack(fill='both', expand=True, pady=5)
        
        # Options
        opt = tk.Frame(right, bg=THEME['card'])
        opt.pack(fill='x', pady=5)
        
        tk.Label(opt, text="Intervalle:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.chat_int = tk.Spinbox(opt, from_=10, to=3600, width=5)
        self.chat_int.pack(side='left', padx=5)
        tk.Label(opt, text="sec", bg=THEME['card'], fg=THEME['text2']).pack(side='left')
        
        tk.Label(opt, text="  Envoyer", bg=THEME['card'], fg=THEME['text']).pack(side='left', padx=(15,0))
        self.chat_batch = tk.Spinbox(opt, from_=1, to=10, width=3)
        self.chat_batch.pack(side='left', padx=5)
        tk.Label(opt, text="msg/fois", bg=THEME['card'], fg=THEME['text2']).pack(side='left')
        
        tk.Button(opt, text="💾 Sauver", bg=THEME['info'], fg='white',
                 command=self.save_current_profile).pack(side='right', padx=5)
        
        self.current_edit = None  # Profil en cours d'édition
        
        # === BOUTONS START/STOP ===
        bf = tk.Frame(tab, bg=THEME['bg'])
        bf.pack(pady=10)
        
        self.chat_btn = tk.Button(bf, text="▶️ DÉMARRER TOUT", font=('Segoe UI', 11, 'bold'),
                                  bg=THEME['success'], fg='white', width=18,
                                  command=self.toggle_all_chat)
        self.chat_btn.pack(side='left', padx=5)
        
        self.chat_running = False
        self.chat_threads = []
    
    def refresh_profile_list(self):
        # Vider
        for w in self.profile_frame.winfo_children():
            w.destroy()
        
        self.profile_vars = {}
        self.profile_buttons = {}
        
        for name, data in self.chat_profiles.items():
            f = tk.Frame(self.profile_frame, bg=THEME['card'])
            f.pack(fill='x', pady=2)
            
            var = tk.BooleanVar(value=data.get("active", False))
            self.profile_vars[name] = var
            
            cb = tk.Checkbutton(f, variable=var, bg=THEME['card'], 
                               selectcolor=THEME['bg3'],
                               command=lambda n=name: self.on_profile_toggle(n))
            cb.pack(side='left')
            
            btn = tk.Button(f, text=name, bg=THEME['bg3'], fg=THEME['text'],
                           anchor='w', width=12,
                           command=lambda n=name: self.edit_profile(n))
            btn.pack(side='left', fill='x', expand=True)
            self.profile_buttons[name] = btn
    
    def on_profile_toggle(self, name):
        self.chat_profiles[name]["active"] = self.profile_vars[name].get()
        self.save_profiles()
    
    def edit_profile(self, name):
        self.current_edit = name
        self.edit_label.config(text=f"✏️ Éditer: {name}")
        
        # Highlight le bouton sélectionné
        for n, btn in self.profile_buttons.items():
            if n == name:
                btn.config(bg=THEME['info'])
            else:
                btn.config(bg=THEME['bg3'])
        
        # Charger les données
        p = self.chat_profiles[name]
        self.chat_text.delete('1.0', 'end')
        self.chat_text.insert('1.0', '\n'.join(p.get("msgs", [])))
        self.chat_int.delete(0, 'end')
        self.chat_int.insert(0, str(p.get("interval", 300)))
        self.chat_batch.delete(0, 'end')
        self.chat_batch.insert(0, str(p.get("batch", 1)))
    
    def save_current_profile(self):
        if not self.current_edit:
            self.log("❌ Sélectionne un profil d'abord")
            return
        
        name = self.current_edit
        msgs = [m.strip() for m in self.chat_text.get('1.0', 'end').strip().split('\n') if m.strip()]
        
        self.chat_profiles[name]["msgs"] = msgs
        self.chat_profiles[name]["interval"] = int(self.chat_int.get())
        self.chat_profiles[name]["batch"] = int(self.chat_batch.get())
        self.save_profiles()
        self.log(f"💾 Profil '{name}' sauvé")
    
    def save_profiles(self):
        self.cfg.data["chat_profiles"] = self.chat_profiles
        self.cfg.save()
    
    def add_profile(self):
        name = simpledialog.askstring("Nouveau profil", "Nom du profil:")
        if name and name.strip():
            name = name.strip()
            self.chat_profiles[name] = {"msgs": [], "interval": 300, "batch": 1, "active": False}
            self.save_profiles()
            self.refresh_profile_list()
            self.edit_profile(name)
            self.log(f"➕ Profil '{name}' créé")
    
    def del_profile(self):
        if not self.current_edit:
            self.log("❌ Sélectionne un profil d'abord")
            return
        if len(self.chat_profiles) <= 1:
            self.log("❌ Garde au moins 1 profil")
            return
        
        name = self.current_edit
        if messagebox.askyesno("Supprimer", f"Supprimer '{name}'?"):
            del self.chat_profiles[name]
            self.save_profiles()
            self.refresh_profile_list()
            self.current_edit = None
            self.edit_label.config(text="✏️ Éditer: (sélectionne un profil)")
            self.chat_text.delete('1.0', 'end')
            self.log(f"🗑️ Profil '{name}' supprimé")
    
    def toggle_all_chat(self):
        if self.chat_running:
            self.stop_all_chat()
        else:
            self.start_all_chat()
    
    def start_all_chat(self):
        # Trouver les profils actifs (cochés) dans l'ordre
        active = [n for n in self.chat_profiles.keys() if self.profile_vars.get(n, tk.BooleanVar()).get()]
        
        if not active:
            self.log("❌ Coche au moins 1 profil!")
            return
        
        self.chat_running = True
        self.active_profiles = active
        
        # Un seul thread qui fait tout dans l'ordre
        t = threading.Thread(target=self._chat_sequential_loop, daemon=True)
        t.start()
        
        self.chat_btn.config(text="⏹️ ARRÊTER TOUT", bg=THEME['accent'])
        self.log(f"💬 {len(active)} profil(s) en rotation")
    
    def stop_all_chat(self):
        self.chat_running = False
        self.chat_btn.config(text="▶️ DÉMARRER TOUT", bg=THEME['success'])
        self.log("💬 Auto-Chat arrêté")
    
    def _chat_sequential_loop(self):
        """Boucle séquentielle: profil 1, puis profil 2, etc."""
        while self.chat_running:
            for name in self.active_profiles:
                if not self.chat_running:
                    break
                
                profile = self.chat_profiles.get(name, {})
                msgs = profile.get("msgs", [])
                interval = profile.get("interval", 300)
                batch = profile.get("batch", 1)
                
                if not msgs:
                    continue
                
                # Envoyer les messages de ce profil
                self.log(f"💬 [{name}]")
                for i in range(min(batch, len(msgs))):
                    if not self.chat_running:
                        break
                    self._send_msg(msgs[i % len(msgs)])
                    if i < batch - 1:
                        time.sleep(1.5)
                
                # Attendre l'intervalle de ce profil avant le suivant
                for _ in range(interval):
                    if not self.chat_running:
                        break
                    time.sleep(1)
    
    def _send_msg(self, msg):
        if not HAS_PYAUTOGUI:
            return
        try:
            pyautogui.press('enter')
            time.sleep(0.2)
            pyautogui.typewrite(msg, interval=0.02)
            time.sleep(0.1)
            pyautogui.press('enter')
            self.log(f"💬 {msg[:20]}...")
        except:
            pass
    
    # === TAB: PIXEL BOT ===
    def tab_pixel(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="🎯 Pixel")
        
        tk.Label(tab, text="🎯 Pixel Bot", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        tk.Label(tab, text="Détecte une couleur et clique automatiquement",
                font=('Segoe UI', 9), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        f = tk.Frame(tab, bg=THEME['card'], padx=15, pady=15)
        f.pack(pady=15, padx=30, fill='x')
        
        # Position à surveiller
        r1 = tk.Frame(f, bg=THEME['card'])
        r1.pack(fill='x', pady=5)
        tk.Label(r1, text="Position à surveiller:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_x = tk.Entry(r1, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_x.insert(0, "0")
        self.pixel_x.pack(side='left', padx=5)
        tk.Label(r1, text=",", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_y = tk.Entry(r1, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_y.insert(0, "0")
        self.pixel_y.pack(side='left', padx=5)
        tk.Button(r1, text="📍 Capturer", bg=THEME['info'], fg='white',
                 command=self.capture_pixel_pos).pack(side='left', padx=10)
        
        # Couleur à détecter
        r2 = tk.Frame(f, bg=THEME['card'])
        r2.pack(fill='x', pady=5)
        tk.Label(r2, text="Couleur cible (R,G,B):", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_r = tk.Entry(r2, width=4, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_r.insert(0, "255")
        self.pixel_r.pack(side='left', padx=2)
        self.pixel_g = tk.Entry(r2, width=4, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_g.insert(0, "0")
        self.pixel_g.pack(side='left', padx=2)
        self.pixel_b = tk.Entry(r2, width=4, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_b.insert(0, "0")
        self.pixel_b.pack(side='left', padx=2)
        tk.Button(r2, text="🎨 Capturer", bg=THEME['warning'], fg='white',
                 command=self.capture_pixel_color).pack(side='left', padx=10)
        
        # Aperçu couleur
        self.pixel_preview = tk.Label(r2, text="   ", bg='#ff0000', width=3)
        self.pixel_preview.pack(side='left', padx=5)
        
        # Tolérance
        r3 = tk.Frame(f, bg=THEME['card'])
        r3.pack(fill='x', pady=5)
        tk.Label(r3, text="Tolérance:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_tol = tk.Spinbox(r3, from_=0, to=100, width=5)
        self.pixel_tol.delete(0, 'end')
        self.pixel_tol.insert(0, "20")
        self.pixel_tol.pack(side='left', padx=5)
        tk.Label(r3, text="(0 = exacte, 50 = approximatif)", bg=THEME['card'], fg=THEME['text2']).pack(side='left')
        
        # Position de clic
        r4 = tk.Frame(f, bg=THEME['card'])
        r4.pack(fill='x', pady=5)
        tk.Label(r4, text="Cliquer à:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_click_x = tk.Entry(r4, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_click_x.insert(0, "0")
        self.pixel_click_x.pack(side='left', padx=5)
        tk.Label(r4, text=",", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_click_y = tk.Entry(r4, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.pixel_click_y.insert(0, "0")
        self.pixel_click_y.pack(side='left', padx=5)
        self.pixel_same = tk.BooleanVar(value=True)
        tk.Checkbutton(r4, text="Même position", variable=self.pixel_same,
                      bg=THEME['card'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left', padx=10)
        
        # Intervalle
        r5 = tk.Frame(f, bg=THEME['card'])
        r5.pack(fill='x', pady=5)
        tk.Label(r5, text="Vérifier toutes les:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.pixel_int = tk.Spinbox(r5, from_=100, to=5000, width=6, increment=100)
        self.pixel_int.delete(0, 'end')
        self.pixel_int.insert(0, "500")
        self.pixel_int.pack(side='left', padx=5)
        tk.Label(r5, text="ms", bg=THEME['card'], fg=THEME['text2']).pack(side='left')
        
        # Status
        self.pixel_status = tk.Label(f, text="⏸️ En attente", bg=THEME['card'], fg=THEME['text2'])
        self.pixel_status.pack(pady=5)
        
        # Bouton
        self.pixel_btn = tk.Button(tab, text="▶️ DÉMARRER", font=('Segoe UI', 11, 'bold'),
                                   bg=THEME['success'], fg='white', width=18,
                                   command=self.toggle_pixel)
        self.pixel_btn.pack(pady=10)
        
        self.pixel_running = False
    
    def capture_pixel_pos(self):
        if HAS_PYAUTOGUI:
            x, y = pyautogui.position()
            self.pixel_x.delete(0, 'end')
            self.pixel_x.insert(0, str(x))
            self.pixel_y.delete(0, 'end')
            self.pixel_y.insert(0, str(y))
            if self.pixel_same.get():
                self.pixel_click_x.delete(0, 'end')
                self.pixel_click_x.insert(0, str(x))
                self.pixel_click_y.delete(0, 'end')
                self.pixel_click_y.insert(0, str(y))
            self.log(f"📍 Position: ({x}, {y})")
    
    def capture_pixel_color(self):
        if HAS_PIL:
            try:
                x = int(self.pixel_x.get())
                y = int(self.pixel_y.get())
                img = ImageGrab.grab()
                r, g, b = img.getpixel((x, y))[:3]
                self.pixel_r.delete(0, 'end')
                self.pixel_r.insert(0, str(r))
                self.pixel_g.delete(0, 'end')
                self.pixel_g.insert(0, str(g))
                self.pixel_b.delete(0, 'end')
                self.pixel_b.insert(0, str(b))
                self.pixel_preview.config(bg=f'#{r:02x}{g:02x}{b:02x}')
                self.log(f"🎨 Couleur: ({r}, {g}, {b})")
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
    
    def toggle_pixel(self):
        if self.pixel_running:
            self.pixel_running = False
            self.pixel_btn.config(text="▶️ DÉMARRER", bg=THEME['success'])
            self.pixel_status.config(text="⏸️ Arrêté")
        else:
            self.pixel_running = True
            self.pixel_btn.config(text="⏹️ ARRÊTER", bg=THEME['accent'])
            threading.Thread(target=self._pixel_loop, daemon=True).start()
    
    def _pixel_loop(self):
        x = int(self.pixel_x.get())
        y = int(self.pixel_y.get())
        target_r = int(self.pixel_r.get())
        target_g = int(self.pixel_g.get())
        target_b = int(self.pixel_b.get())
        tol = int(self.pixel_tol.get())
        interval = int(self.pixel_int.get()) / 1000
        
        click_x = x if self.pixel_same.get() else int(self.pixel_click_x.get())
        click_y = y if self.pixel_same.get() else int(self.pixel_click_y.get())
        
        clicks = 0
        while self.pixel_running:
            try:
                img = ImageGrab.grab()
                r, g, b = img.getpixel((x, y))[:3]
                
                # Vérifier si la couleur correspond
                if (abs(r - target_r) <= tol and 
                    abs(g - target_g) <= tol and 
                    abs(b - target_b) <= tol):
                    pyautogui.click(click_x, click_y)
                    clicks += 1
                    self.root.after(0, lambda c=clicks: self.pixel_status.config(
                        text=f"✅ Détecté! Clics: {c}", fg=THEME['success']))
                    self.send_notification(f"Pixel detecte! ({clicks} clics)")
                else:
                    self.root.after(0, lambda: self.pixel_status.config(
                        text=f"👁️ Surveillance... ({r},{g},{b})", fg=THEME['text2']))
            except:
                pass
            time.sleep(interval)
    
    # === TAB: MP DETECTOR ===
    def tab_mp_detector(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="📩 MP")
        
        tk.Label(tab, text="📩 Détecteur MP", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        tk.Label(tab, text="Alerte quand tu reçois un message privé",
                font=('Segoe UI', 9), bg=THEME['bg'], fg=THEME['text2']).pack()
        
        f = tk.Frame(tab, bg=THEME['card'], padx=15, pady=15)
        f.pack(pady=15, padx=30, fill='x')
        
        # Zone à surveiller (icône MP ou zone chat)
        tk.Label(f, text="Zone à surveiller (coin de l'icône MP):", 
                bg=THEME['card'], fg=THEME['text']).pack(anchor='w')
        
        r1 = tk.Frame(f, bg=THEME['card'])
        r1.pack(fill='x', pady=5)
        tk.Label(r1, text="Position:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.mp_x = tk.Entry(r1, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.mp_x.insert(0, "0")
        self.mp_x.pack(side='left', padx=5)
        tk.Label(r1, text=",", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.mp_y = tk.Entry(r1, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.mp_y.insert(0, "0")
        self.mp_y.pack(side='left', padx=5)
        tk.Button(r1, text="📍 Capturer", bg=THEME['info'], fg='white',
                 command=self.capture_mp_pos).pack(side='left', padx=10)
        
        # Couleur quand MP reçu
        r2 = tk.Frame(f, bg=THEME['card'])
        r2.pack(fill='x', pady=5)
        tk.Label(r2, text="Couleur alerte MP:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.mp_r = tk.Entry(r2, width=4, bg=THEME['bg3'], fg=THEME['text'])
        self.mp_r.insert(0, "255")
        self.mp_r.pack(side='left', padx=2)
        self.mp_g = tk.Entry(r2, width=4, bg=THEME['bg3'], fg=THEME['text'])
        self.mp_g.insert(0, "200")
        self.mp_g.pack(side='left', padx=2)
        self.mp_b = tk.Entry(r2, width=4, bg=THEME['bg3'], fg=THEME['text'])
        self.mp_b.insert(0, "0")
        self.mp_b.pack(side='left', padx=2)
        tk.Button(r2, text="🎨 Capturer", bg=THEME['warning'], fg='white',
                 command=self.capture_mp_color).pack(side='left', padx=10)
        self.mp_preview = tk.Label(r2, text="   ", bg='#ffc800', width=3)
        self.mp_preview.pack(side='left', padx=5)
        
        # Options
        r3 = tk.Frame(f, bg=THEME['card'])
        r3.pack(fill='x', pady=10)
        self.mp_sound = tk.BooleanVar(value=True)
        tk.Checkbutton(r3, text="🔊 Son", variable=self.mp_sound,
                      bg=THEME['card'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left')
        self.mp_notif = tk.BooleanVar(value=True)
        tk.Checkbutton(r3, text="📱 Notification", variable=self.mp_notif,
                      bg=THEME['card'], fg=THEME['text'], selectcolor=THEME['bg3']).pack(side='left', padx=10)
        
        # Status
        self.mp_status = tk.Label(f, text="⏸️ En attente", bg=THEME['card'], fg=THEME['text2'])
        self.mp_status.pack(pady=5)
        self.mp_count = 0
        
        # Bouton
        self.mp_btn = tk.Button(tab, text="▶️ DÉMARRER", font=('Segoe UI', 11, 'bold'),
                                bg=THEME['success'], fg='white', width=18,
                                command=self.toggle_mp)
        self.mp_btn.pack(pady=10)
        
        self.mp_running = False
        self.mp_last_state = False
    
    def capture_mp_pos(self):
        if HAS_PYAUTOGUI:
            x, y = pyautogui.position()
            self.mp_x.delete(0, 'end')
            self.mp_x.insert(0, str(x))
            self.mp_y.delete(0, 'end')
            self.mp_y.insert(0, str(y))
            self.log(f"📍 Position MP: ({x}, {y})")
    
    def capture_mp_color(self):
        if HAS_PIL:
            try:
                x = int(self.mp_x.get())
                y = int(self.mp_y.get())
                img = ImageGrab.grab()
                r, g, b = img.getpixel((x, y))[:3]
                self.mp_r.delete(0, 'end')
                self.mp_r.insert(0, str(r))
                self.mp_g.delete(0, 'end')
                self.mp_g.insert(0, str(g))
                self.mp_b.delete(0, 'end')
                self.mp_b.insert(0, str(b))
                self.mp_preview.config(bg=f'#{r:02x}{g:02x}{b:02x}')
                self.log(f"🎨 Couleur MP: ({r}, {g}, {b})")
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
    
    def toggle_mp(self):
        if self.mp_running:
            self.mp_running = False
            self.mp_btn.config(text="▶️ DÉMARRER", bg=THEME['success'])
            self.mp_status.config(text="⏸️ Arrêté")
        else:
            self.mp_running = True
            self.mp_btn.config(text="⏹️ ARRÊTER", bg=THEME['accent'])
            self.mp_last_state = False
            threading.Thread(target=self._mp_loop, daemon=True).start()
    
    def _mp_loop(self):
        x = int(self.mp_x.get())
        y = int(self.mp_y.get())
        target_r = int(self.mp_r.get())
        target_g = int(self.mp_g.get())
        target_b = int(self.mp_b.get())
        tol = 30
        
        while self.mp_running:
            try:
                img = ImageGrab.grab()
                r, g, b = img.getpixel((x, y))[:3]
                
                is_mp = (abs(r - target_r) <= tol and 
                        abs(g - target_g) <= tol and 
                        abs(b - target_b) <= tol)
                
                if is_mp and not self.mp_last_state:
                    # Nouveau MP!
                    self.mp_count += 1
                    self.root.after(0, lambda: self.mp_status.config(
                        text=f"📩 MP REÇU! (Total: {self.mp_count})", fg=THEME['warning']))
                    
                    if self.mp_sound.get():
                        self.play_sound()
                    if self.mp_notif.get():
                        self.send_notification("Tu as recu un MP sur Dofus!")
                    
                    self.log("📩 MP détecté!")
                elif not is_mp:
                    self.root.after(0, lambda: self.mp_status.config(
                        text=f"👁️ Surveillance... (MPs: {self.mp_count})", fg=THEME['text2']))
                
                self.mp_last_state = is_mp
            except:
                pass
            time.sleep(1)
    
    def play_sound(self):
        """Joue un son d'alerte"""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass
    
    # === TAB: NOTIFICATIONS ===
    def tab_notif(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="📱 Notif")
        
        tk.Label(tab, text="📱 Notifications Push", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        # === NTFY.SH ===
        f1 = tk.LabelFrame(tab, text="📲 Ntfy.sh (gratuit & recommandé)", font=('Segoe UI', 10, 'bold'),
                          bg=THEME['card'], fg=THEME['text'], padx=15, pady=10)
        f1.pack(pady=10, padx=20, fill='x')
        
        r1 = tk.Frame(f1, bg=THEME['card'])
        r1.pack(fill='x', pady=5)
        tk.Label(r1, text="Topic:", width=10, anchor='w',
                bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.ntfy_topic = tk.Entry(r1, width=30, bg=THEME['bg3'], fg=THEME['text'])
        self.ntfy_topic.pack(side='left', padx=5)
        self.ntfy_topic.insert(0, self.cfg.data.get("ntfy_topic", ""))
        
        instructions = """💡 Comment utiliser:
1. Installe l'app "ntfy" sur ton téléphone (Play Store / App Store)
2. Choisis un nom unique (ex: dofus-alerts-pseudo123)
3. Dans l'app, clique + et abonne-toi à ce même nom
4. C'est tout ! Les alertes arrivent sur ton tel 🎉"""
        
        tk.Label(f1, text=instructions, font=('Segoe UI', 9),
                bg=THEME['card'], fg=THEME['text2'], justify='left').pack(anchor='w', pady=5)
        
        # === DISCORD ===
        f2 = tk.LabelFrame(tab, text="🎮 Discord Webhook (gratuit)", font=('Segoe UI', 10, 'bold'),
                          bg=THEME['card'], fg=THEME['text'], padx=15, pady=10)
        f2.pack(pady=10, padx=20, fill='x')
        
        self.webhook_entry = tk.Entry(f2, width=55, bg=THEME['bg3'], fg=THEME['text'],
                                      font=('Consolas', 9))
        self.webhook_entry.pack(fill='x', pady=5)
        self.webhook_entry.insert(0, self.cfg.data.get("discord_webhook", ""))
        
        tk.Label(f2, text="💡 Serveur Discord → Salon → Modifier → Intégrations → Webhooks",
                font=('Segoe UI', 8), bg=THEME['card'], fg=THEME['text2']).pack(anchor='w')
        
        # === BOUTONS ===
        bf = tk.Frame(tab, bg=THEME['bg'])
        bf.pack(pady=15)
        
        tk.Button(bf, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 font=('Segoe UI', 10), command=self.save_notif).pack(side='left', padx=5)
        tk.Button(bf, text="🧪 Test Ntfy", bg=THEME['warning'], fg='white',
                 command=lambda: self.send_notification("Test notification depuis Dofus Bot!", ntfy=True, discord=False)).pack(side='left', padx=5)
        tk.Button(bf, text="🧪 Test Discord", bg=THEME['info'], fg='white',
                 command=lambda: self.send_notification("🧪 Test Discord depuis Dofus Bot!", ntfy=False, discord=True)).pack(side='left', padx=5)
        
        self.notif_status = tk.Label(tab, text="", bg=THEME['bg'], fg=THEME['text2'])
        self.notif_status.pack(pady=5)
    
    def save_notif(self):
        self.cfg.data["ntfy_topic"] = self.ntfy_topic.get().strip()
        self.cfg.data["discord_webhook"] = self.webhook_entry.get().strip()
        self.cfg.save()
        self.log("💾 Notifications sauvegardées")
        self.notif_status.config(text="✅ Sauvegardé!", fg=THEME['success'])
    
    def send_notification(self, message, ntfy=True, discord=True):
        """Envoie une notification via Ntfy.sh et/ou Discord"""
        sent = False
        
        # Ntfy.sh
        if ntfy:
            topic = self.cfg.data.get("ntfy_topic", "")
            if topic:
                try:
                    import urllib.request
                    
                    url = f"https://ntfy.sh/{topic}"
                    # Encoder le message en UTF-8
                    data = message.encode('utf-8')
                    req = urllib.request.Request(url, data=data)
                    # Titre sans emoji pour éviter erreur d'encodage
                    req.add_header('Title', 'Dofus Bot')
                    req.add_header('Tags', 'video_game')
                    urllib.request.urlopen(req, timeout=5)
                    sent = True
                    self.log("📲 Ntfy envoyé")
                except Exception as e:
                    self.log(f"❌ Ntfy: {e}")
        
        # Discord
        if discord:
            webhook_url = self.cfg.data.get("discord_webhook", "")
            if webhook_url:
                try:
                    import urllib.request
                    import json as json_lib
                    
                    data = json_lib.dumps({"content": message}).encode('utf-8')
                    req = urllib.request.Request(webhook_url, data=data,
                                                headers={'Content-Type': 'application/json'})
                    urllib.request.urlopen(req, timeout=5)
                    sent = True
                    self.log("🎮 Discord envoyé")
                except Exception as e:
                    self.log(f"❌ Discord: {e}")
        
        if sent:
            self.notif_status.config(text="✅ Notification envoyée!", fg=THEME['success'])
        else:
            self.notif_status.config(text="⚠️ Aucun service configuré", fg=THEME['warning'])

    # === TAB: NOTES ===
    def tab_notes(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="📝 Notes")
        
        tk.Label(tab, text="📝 Notes", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        self.notes = scrolledtext.ScrolledText(tab, font=('Consolas', 10),
                                               bg=THEME['bg3'], fg=THEME['text'],
                                               insertbackground=THEME['text'])
        self.notes.pack(fill='both', expand=True, padx=20, pady=10)
        self.notes.insert('1.0', self.cfg.data.get("notes", ""))
        
        tk.Button(tab, text="💾 Sauvegarder", bg=THEME['success'], fg='white',
                 command=self.save_notes).pack(pady=5)
    
    def save_notes(self):
        self.cfg.data["notes"] = self.notes.get('1.0', 'end').strip()
        self.cfg.save()
        self.log("📝 Notes sauvées")
    
    # === TAB: CALC ===
    def tab_calc(self, nb):
        tab = tk.Frame(nb, bg=THEME['bg'])
        nb.add(tab, text="💰 Calcul")
        
        tk.Label(tab, text="💰 Calculateur Kamas", font=('Segoe UI', 14, 'bold'),
                bg=THEME['bg'], fg=THEME['text']).pack(pady=10)
        
        # HDV
        f1 = tk.LabelFrame(tab, text="📊 Taxe HDV (2%)", bg=THEME['card'], 
                          fg=THEME['text'], padx=10, pady=8)
        f1.pack(fill='x', padx=30, pady=8)
        r1 = tk.Frame(f1, bg=THEME['card'])
        r1.pack()
        tk.Label(r1, text="Prix:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.hdv_in = tk.Entry(r1, width=12, bg=THEME['bg3'], fg=THEME['text'])
        self.hdv_in.pack(side='left', padx=5)
        tk.Button(r1, text="=", bg=THEME['info'], fg='white',
                 command=self.calc_hdv).pack(side='left', padx=5)
        self.hdv_out = tk.Label(f1, text="", bg=THEME['card'], fg=THEME['success'])
        self.hdv_out.pack()
        
        # Unit
        f2 = tk.LabelFrame(tab, text="📦 Prix/Unité", bg=THEME['card'],
                          fg=THEME['text'], padx=10, pady=8)
        f2.pack(fill='x', padx=30, pady=8)
        r2 = tk.Frame(f2, bg=THEME['card'])
        r2.pack()
        tk.Label(r2, text="Total:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.unit_total = tk.Entry(r2, width=10, bg=THEME['bg3'], fg=THEME['text'])
        self.unit_total.pack(side='left', padx=3)
        tk.Label(r2, text="Qté:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.unit_qty = tk.Entry(r2, width=6, bg=THEME['bg3'], fg=THEME['text'])
        self.unit_qty.pack(side='left', padx=3)
        tk.Button(r2, text="=", bg=THEME['info'], fg='white',
                 command=self.calc_unit).pack(side='left', padx=5)
        self.unit_out = tk.Label(f2, text="", bg=THEME['card'], fg=THEME['success'])
        self.unit_out.pack()
        
        # Craft
        f3 = tk.LabelFrame(tab, text="🔨 Rentabilité Craft", bg=THEME['card'],
                          fg=THEME['text'], padx=10, pady=8)
        f3.pack(fill='x', padx=30, pady=8)
        r3 = tk.Frame(f3, bg=THEME['card'])
        r3.pack()
        tk.Label(r3, text="Coût:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.craft_cost = tk.Entry(r3, width=10, bg=THEME['bg3'], fg=THEME['text'])
        self.craft_cost.pack(side='left', padx=3)
        tk.Label(r3, text="Vente:", bg=THEME['card'], fg=THEME['text']).pack(side='left')
        self.craft_sell = tk.Entry(r3, width=10, bg=THEME['bg3'], fg=THEME['text'])
        self.craft_sell.pack(side='left', padx=3)
        tk.Button(r3, text="=", bg=THEME['info'], fg='white',
                 command=self.calc_craft).pack(side='left', padx=5)
        self.craft_out = tk.Label(f3, text="", bg=THEME['card'], fg=THEME['success'])
        self.craft_out.pack()
    
    def calc_hdv(self):
        try:
            p = int(self.hdv_in.get().replace(' ', '').replace('k', '000'))
            tax = int(p * 0.02)
            self.hdv_out.config(text=f"Taxe: {tax:,} | Net: {p-tax:,}".replace(',', ' '))
        except:
            self.hdv_out.config(text="❌ Erreur")
    
    def calc_unit(self):
        try:
            t = int(self.unit_total.get().replace(' ', '').replace('k', '000'))
            q = int(self.unit_qty.get())
            self.unit_out.config(text=f"= {t//q:,} /unité".replace(',', ' '))
        except:
            self.unit_out.config(text="❌ Erreur")
    
    def calc_craft(self):
        try:
            c = int(self.craft_cost.get().replace(' ', '').replace('k', '000'))
            s = int(self.craft_sell.get().replace(' ', '').replace('k', '000'))
            tax = int(s * 0.02)
            profit = s - tax - c
            if profit > 0:
                self.craft_out.config(text=f"✅ +{profit:,} profit".replace(',', ' '), fg=THEME['success'])
            else:
                self.craft_out.config(text=f"❌ {profit:,} perte".replace(',', ' '), fg=THEME['accent'])
        except:
            self.craft_out.config(text="❌ Erreur")
    
    # === UTILS ===
    def log(self, msg):
        self.root.after(0, lambda: self.log_label.config(text=msg))
    
    def quit(self):
        self.reconnect.stop()
        self.clicker.stop()
        self.chat_running = False
        self.pixel_running = False
        self.mp_running = False
        self.cfg.data["notes"] = self.notes.get('1.0', 'end').strip()
        self.cfg.save()
        self.root.destroy()


if __name__ == "__main__":
    App().run()