"""
🎮 Client Dofus - Contrôle à distance
Version simple et claire
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import asyncio
from datetime import datetime

# WebSocket
try:
    import websockets
    HAS_WEBSOCKETS = True
except:
    HAS_WEBSOCKETS = False


class DofusClient:
    def __init__(self):
        # Config
        self.config_file = "client_config.json"
        self.server_host = ""
        self.server_port = 8765
        self.auth_key = ""
        self.macros = {}
        self.sequences = {}
        
        self.load_config()
        
        # État
        self.running = False
        self.connected = False
        self.websocket = None
        self.loop = None
        self.send_queue = None
        
        # Couleurs
        self.c = {
            'bg': '#0f0f1a',
            'card': '#1a1a2e',
            'input': '#252540',
            'accent': '#6c5ce7',
            'red': '#e74c3c',
            'green': '#00b894',
            'orange': '#fdcb6e',
            'blue': '#74b9ff',
            'text': '#ffffff',
            'text2': '#a0a0b0'
        }
        
        self.setup_ui()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.server_host = data.get('server_host', '')
                self.server_port = data.get('server_port', 8765)
                self.auth_key = data.get('auth_key', '')
                self.macros = data.get('macros', {})
                self.sequences = data.get('sequences', {})
            except:
                pass
    
    def save_config(self):
        data = {
            'server_host': self.server_host,
            'server_port': self.server_port,
            'auth_key': self.auth_key,
            'macros': self.macros,
            'sequences': self.sequences,
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("🎮 Client Dofus")
        self.root.geometry("600x850")
        self.root.configure(bg=self.c['bg'])
        self.root.resizable(True, True)
        self.root.minsize(600, 800)
        
        # ===== HEADER =====
        header = tk.Frame(self.root, bg=self.c['card'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="🎮 Client Dofus", font=('Segoe UI', 14, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(side='left', padx=15, pady=10)
        
        self.status_dot = tk.Label(header, text="●", font=('Segoe UI', 16),
                                   bg=self.c['card'], fg=self.c['red'])
        self.status_dot.pack(side='right', padx=15)
        
        # ===== CONNEXION =====
        conn_frame = tk.Frame(self.root, bg=self.c['card'], padx=20, pady=15)
        conn_frame.pack(fill='x', padx=15, pady=15)
        
        # Ligne 1: Serveur
        row1 = tk.Frame(conn_frame, bg=self.c['card'])
        row1.pack(fill='x', pady=5)
        
        tk.Label(row1, text="🌐 Serveur", font=('Segoe UI', 10), width=10, anchor='w',
                bg=self.c['card'], fg=self.c['text2']).pack(side='left')
        
        self.host_entry = tk.Entry(row1, font=('Segoe UI', 11), width=22,
                                   bg=self.c['input'], fg=self.c['text'],
                                   insertbackground=self.c['text'], relief='flat')
        self.host_entry.insert(0, self.server_host)
        self.host_entry.pack(side='left', padx=5, ipady=5)
        
        tk.Label(row1, text=":", bg=self.c['card'], fg=self.c['text2']).pack(side='left')
        
        self.port_entry = tk.Entry(row1, font=('Segoe UI', 11), width=6,
                                   bg=self.c['input'], fg=self.c['text'],
                                   insertbackground=self.c['text'], relief='flat')
        self.port_entry.insert(0, str(self.server_port))
        self.port_entry.pack(side='left', padx=5, ipady=5)
        
        # Ligne 2: Clé
        row2 = tk.Frame(conn_frame, bg=self.c['card'])
        row2.pack(fill='x', pady=5)
        
        tk.Label(row2, text="🔑 Clé", font=('Segoe UI', 10), width=10, anchor='w',
                bg=self.c['card'], fg=self.c['text2']).pack(side='left')
        
        self.key_entry = tk.Entry(row2, font=('Segoe UI', 11), width=32, show='●',
                                  bg=self.c['input'], fg=self.c['text'],
                                  insertbackground=self.c['text'], relief='flat')
        self.key_entry.insert(0, self.auth_key)
        self.key_entry.pack(side='left', padx=5, ipady=5)
        
        # Bouton connexion
        self.connect_btn = tk.Button(conn_frame, text="🔌 SE CONNECTER", 
                                     font=('Segoe UI', 11, 'bold'),
                                     bg=self.c['green'], fg='white', 
                                     relief='flat', cursor='hand2',
                                     command=self.toggle_connection)
        self.connect_btn.pack(pady=15, ipadx=20, ipady=8)
        
        # ===== ONGLETS =====
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=self.c['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.c['card'], 
                       foreground=self.c['text'], padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', self.c['accent'])])
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=15, pady=5)
        
        # Tab 1: Chat
        self.create_chat_tab()
        
        # Tab 2: Macros
        self.create_macros_tab()
        
        # Tab 3: Séquences
        self.create_sequences_tab()
        
        # ===== FOOTER LOG =====
        log_frame = tk.Frame(self.root, bg=self.c['card'], height=100)
        log_frame.pack(fill='x', padx=15, pady=10)
        log_frame.pack_propagate(False)
        
        self.log_text = tk.Text(log_frame, bg=self.c['card'], fg=self.c['text2'],
                                font=('Consolas', 9), wrap='word', height=5,
                                relief='flat', state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=5)
    
    def create_chat_tab(self):
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="💬 Chat")
        
        # Zone principale
        main = tk.Frame(tab, bg=self.c['card'], padx=20, pady=20)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Envoyer message
        tk.Label(main, text="📤 Envoyer un message dans le jeu", 
                font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w', pady=(0,10))
        
        chat_row = tk.Frame(main, bg=self.c['card'])
        chat_row.pack(fill='x', pady=5)
        
        self.chat_entry = tk.Entry(chat_row, font=('Segoe UI', 12), width=30,
                                   bg=self.c['input'], fg=self.c['text'],
                                   insertbackground=self.c['text'], relief='flat')
        self.chat_entry.pack(side='left', ipady=8, padx=(0,10))
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        
        tk.Button(chat_row, text="Envoyer", font=('Segoe UI', 10, 'bold'),
                 bg=self.c['green'], fg='white', relief='flat',
                 command=self.send_chat).pack(side='left', ipadx=15, ipady=5)
        
        # Séparateur
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=20)
        
        # Commandes rapides
        tk.Label(main, text="⚡ Commandes rapides", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w', pady=(0,10))
        
        quick_frame = tk.Frame(main, bg=self.c['card'])
        quick_frame.pack(fill='x')
        
        quick_cmds = [
            (".tpgroupeall", "🏠 TP Groupe"),
            (".movemobs", "👹 Move Mobs"),
            ("/wave", "👋 Wave"),
        ]
        
        for cmd, label in quick_cmds:
            btn = tk.Button(quick_frame, text=label, font=('Segoe UI', 9),
                           bg=self.c['input'], fg=self.c['text'], relief='flat',
                           cursor='hand2', command=lambda c=cmd: self.quick_chat(c))
            btn.pack(side='left', padx=5, ipadx=10, ipady=5)
        
        # Séparateur
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=20)
        
        # Clics
        tk.Label(main, text="🖱️ Clic souris", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w', pady=(0,10))
        
        click_row = tk.Frame(main, bg=self.c['card'])
        click_row.pack(fill='x')
        
        tk.Label(click_row, text="X", bg=self.c['card'], fg=self.c['text2']).pack(side='left')
        self.click_x = tk.Entry(click_row, font=('Segoe UI', 11), width=6,
                                bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.click_x.insert(0, "960")
        self.click_x.pack(side='left', padx=5, ipady=5)
        
        tk.Label(click_row, text="Y", bg=self.c['card'], fg=self.c['text2']).pack(side='left', padx=(10,0))
        self.click_y = tk.Entry(click_row, font=('Segoe UI', 11), width=6,
                                bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.click_y.insert(0, "540")
        self.click_y.pack(side='left', padx=5, ipady=5)
        
        tk.Button(click_row, text="Clic gauche", font=('Segoe UI', 9),
                 bg=self.c['blue'], fg='white', relief='flat',
                 command=lambda: self.send_click('left')).pack(side='left', padx=10, ipadx=10, ipady=3)
        
        tk.Button(click_row, text="Clic droit", font=('Segoe UI', 9),
                 bg=self.c['orange'], fg='black', relief='flat',
                 command=lambda: self.send_click('right')).pack(side='left', ipadx=10, ipady=3)
    
    def create_macros_tab(self):
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="📝 Macros")
        
        main = tk.Frame(tab, bg=self.c['card'], padx=20, pady=15)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Ajouter macro
        tk.Label(main, text="➕ Nouvelle macro", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w')
        
        add_row = tk.Frame(main, bg=self.c['card'])
        add_row.pack(fill='x', pady=10)
        
        self.macro_name = tk.Entry(add_row, font=('Segoe UI', 10), width=12,
                                   bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.macro_name.insert(0, "nom")
        self.macro_name.pack(side='left', ipady=5, padx=(0,5))
        
        self.macro_cmd = tk.Entry(add_row, font=('Segoe UI', 10), width=20,
                                  bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.macro_cmd.insert(0, ".commande")
        self.macro_cmd.pack(side='left', ipady=5, padx=5)
        
        tk.Button(add_row, text="+ Ajouter", font=('Segoe UI', 9, 'bold'),
                 bg=self.c['green'], fg='white', relief='flat',
                 command=self.add_macro).pack(side='left', padx=10, ipadx=10, ipady=3)
        
        # Liste
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=15)
        
        tk.Label(main, text="📋 Mes macros (clic pour exécuter)", font=('Segoe UI', 10),
                bg=self.c['card'], fg=self.c['text2']).pack(anchor='w')
        
        # Scrollable frame
        canvas = tk.Canvas(main, bg=self.c['card'], highlightthickness=0, height=180)
        self.macros_frame = tk.Frame(canvas, bg=self.c['card'])
        canvas.create_window((0, 0), window=self.macros_frame, anchor="nw")
        canvas.pack(fill='both', expand=True, pady=10)
        
        self.macros_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self.refresh_macros()
    
    def create_sequences_tab(self):
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="🎬 Séquences")
        
        main = tk.Frame(tab, bg=self.c['card'], padx=20, pady=15)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Info
        tk.Label(main, text="🎬 Séquences d'actions automatiques", 
                font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w')
        
        tk.Label(main, text="Format: wait=2;chat=.tp;click=500,300", 
                font=('Segoe UI', 9),
                bg=self.c['card'], fg=self.c['text2']).pack(anchor='w', pady=(0,10))
        
        # Ajouter
        add_row1 = tk.Frame(main, bg=self.c['card'])
        add_row1.pack(fill='x', pady=5)
        
        tk.Label(add_row1, text="Nom:", bg=self.c['card'], fg=self.c['text2']).pack(side='left')
        self.seq_name = tk.Entry(add_row1, font=('Segoe UI', 10), width=15,
                                 bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.seq_name.pack(side='left', ipady=5, padx=5)
        
        add_row2 = tk.Frame(main, bg=self.c['card'])
        add_row2.pack(fill='x', pady=5)
        
        tk.Label(add_row2, text="Actions:", bg=self.c['card'], fg=self.c['text2']).pack(side='left')
        self.seq_actions = tk.Entry(add_row2, font=('Segoe UI', 10), width=35,
                                    bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.seq_actions.insert(0, "wait=2;chat=.tpgroupeall")
        self.seq_actions.pack(side='left', ipady=5, padx=5)
        
        tk.Button(main, text="+ Ajouter séquence", font=('Segoe UI', 9, 'bold'),
                 bg=self.c['green'], fg='white', relief='flat',
                 command=self.add_sequence).pack(anchor='w', pady=10, ipadx=10, ipady=3)
        
        # Liste
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=10)
        
        canvas = tk.Canvas(main, bg=self.c['card'], highlightthickness=0, height=150)
        self.sequences_frame = tk.Frame(canvas, bg=self.c['card'])
        canvas.create_window((0, 0), window=self.sequences_frame, anchor="nw")
        canvas.pack(fill='both', expand=True)
        
        self.sequences_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self.refresh_sequences()
    
    # ===== FONCTIONS =====
    
    def log(self, msg):
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')
    
    def toggle_connection(self):
        if self.running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        if not HAS_WEBSOCKETS:
            messagebox.showerror("Erreur", "pip install websockets")
            return
        
        host = self.host_entry.get().strip()
        if not host:
            messagebox.showwarning("Attention", "Entre l'adresse du serveur!")
            return
        
        self.server_host = host
        self.server_port = int(self.port_entry.get())
        self.auth_key = self.key_entry.get()
        self.save_config()
        
        self.running = True
        self.connect_btn.config(text="⏹️ DÉCONNECTER", bg=self.c['red'])
        
        def run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.send_queue = asyncio.Queue()
            self.loop.run_until_complete(self.run_client())
            self.root.after(0, self.on_disconnected)
        
        threading.Thread(target=run, daemon=True).start()
    
    def disconnect(self):
        self.running = False
        self.connected = False
    
    def on_disconnected(self):
        self.connect_btn.config(text="🔌 SE CONNECTER", bg=self.c['green'])
        self.status_dot.config(fg=self.c['red'])
    
    async def run_client(self):
        uri = f"ws://{self.server_host}:{self.server_port}"
        
        while self.running:
            try:
                self.root.after(0, lambda: self.log("Connexion..."))
                self.root.after(0, lambda: self.status_dot.config(fg=self.c['orange']))
                
                async with websockets.connect(uri) as ws:
                    self.websocket = ws
                    
                    await ws.send(json.dumps({
                        'type': 'auth',
                        'key': self.auth_key,
                        'name': 'Client'
                    }))
                    
                    response = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if data.get('type') == 'auth_ok':
                        self.connected = True
                        self.root.after(0, lambda: self.log("✅ Connecté!"))
                        self.root.after(0, lambda: self.status_dot.config(fg=self.c['green']))
                        
                        recv_task = asyncio.create_task(self.receive_loop(ws))
                        send_task = asyncio.create_task(self.send_loop(ws))
                        await asyncio.gather(recv_task, send_task)
                    else:
                        self.root.after(0, lambda: self.log("❌ Clé invalide!"))
                        self.root.after(0, lambda: self.status_dot.config(fg=self.c['red']))
                        break
            
            except ConnectionRefusedError:
                self.root.after(0, lambda: self.log("❌ Serveur indisponible"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Erreur"))
            
            self.connected = False
            self.root.after(0, lambda: self.status_dot.config(fg=self.c['red']))
            
            if self.running:
                self.root.after(0, lambda: self.log("Reconnexion dans 5s..."))
                await asyncio.sleep(5)
    
    async def receive_loop(self, ws):
        try:
            async for msg in ws:
                if not self.running:
                    break
                data = json.loads(msg)
                if data.get('success'):
                    self.root.after(0, lambda: self.log("✅ OK"))
        except:
            pass
    
    async def send_loop(self, ws):
        while self.running and self.connected:
            try:
                cmd = await asyncio.wait_for(self.send_queue.get(), timeout=1)
                await ws.send(json.dumps(cmd))
            except asyncio.TimeoutError:
                continue
            except:
                break
    
    def send_command(self, cmd):
        if not self.connected:
            self.log("❌ Non connecté!")
            return
        if self.loop and self.send_queue:
            asyncio.run_coroutine_threadsafe(self.send_queue.put(cmd), self.loop)
    
    # Chat
    def send_chat(self):
        text = self.chat_entry.get().strip()
        if text:
            self.log(f"📤 {text}")
            self.send_command({'type': 'chat', 'text': text})
            self.chat_entry.delete(0, 'end')
    
    def quick_chat(self, cmd):
        self.log(f"📤 {cmd}")
        self.send_command({'type': 'chat', 'text': cmd})
    
    # Clic
    def send_click(self, button):
        try:
            x = int(self.click_x.get())
            y = int(self.click_y.get())
            self.log(f"🖱️ Clic {button} ({x},{y})")
            self.send_command({'type': 'click', 'x': x, 'y': y, 'button': button})
        except:
            pass
    
    # Macros
    def add_macro(self):
        name = self.macro_name.get().strip().lower()
        cmd = self.macro_cmd.get().strip()
        if name and cmd and name != "nom":
            self.macros[name] = cmd
            self.save_config()
            self.refresh_macros()
            self.macro_name.delete(0, 'end')
            self.macro_cmd.delete(0, 'end')
            self.log(f"✅ Macro '{name}' ajoutée")
    
    def refresh_macros(self):
        for w in self.macros_frame.winfo_children():
            w.destroy()
        
        if not self.macros:
            tk.Label(self.macros_frame, text="Aucune macro", 
                    bg=self.c['card'], fg=self.c['text2']).pack()
            return
        
        for name, cmd in self.macros.items():
            row = tk.Frame(self.macros_frame, bg=self.c['input'], padx=10, pady=8)
            row.pack(fill='x', pady=3)
            
            btn = tk.Button(row, text=f"▶ {name}", font=('Segoe UI', 10, 'bold'),
                           bg=self.c['accent'], fg='white', relief='flat', cursor='hand2',
                           command=lambda c=cmd: self.run_macro(c))
            btn.pack(side='left')
            
            tk.Label(row, text=cmd, font=('Segoe UI', 9),
                    bg=self.c['input'], fg=self.c['text2']).pack(side='left', padx=15)
            
            tk.Button(row, text="✕", font=('Segoe UI', 9),
                     bg=self.c['red'], fg='white', relief='flat',
                     command=lambda n=name: self.delete_macro(n)).pack(side='right')
    
    def run_macro(self, cmd):
        self.log(f"📤 {cmd}")
        self.send_command({'type': 'chat', 'text': cmd})
    
    def delete_macro(self, name):
        if name in self.macros:
            del self.macros[name]
            self.save_config()
            self.refresh_macros()
    
    # Séquences
    def add_sequence(self):
        name = self.seq_name.get().strip().lower()
        actions = self.seq_actions.get().strip()
        if name and actions:
            self.sequences[name] = actions
            self.save_config()
            self.refresh_sequences()
            self.seq_name.delete(0, 'end')
            self.log(f"✅ Séquence '{name}' ajoutée")
    
    def refresh_sequences(self):
        for w in self.sequences_frame.winfo_children():
            w.destroy()
        
        if not self.sequences:
            tk.Label(self.sequences_frame, text="Aucune séquence",
                    bg=self.c['card'], fg=self.c['text2']).pack()
            return
        
        for name, script in self.sequences.items():
            row = tk.Frame(self.sequences_frame, bg=self.c['input'], padx=10, pady=8)
            row.pack(fill='x', pady=3)
            
            btn = tk.Button(row, text=f"▶ {name}", font=('Segoe UI', 10, 'bold'),
                           bg=self.c['orange'], fg='black', relief='flat', cursor='hand2',
                           command=lambda s=script, n=name: self.run_sequence(n, s))
            btn.pack(side='left')
            
            tk.Button(row, text="✕", font=('Segoe UI', 9),
                     bg=self.c['red'], fg='white', relief='flat',
                     command=lambda n=name: self.delete_sequence(n)).pack(side='right')
    
    def run_sequence(self, name, script):
        actions = self.parse_sequence(script)
        self.log(f"🎬 Séquence '{name}'")
        self.send_command({'type': 'sequence', 'name': name, 'actions': actions})
    
    def parse_sequence(self, script):
        actions = []
        for part in script.split(';'):
            if '=' not in part:
                continue
            t, v = part.split('=', 1)
            t = t.strip().lower()
            v = v.strip()
            
            if t == 'wait':
                actions.append({'type': 'wait', 'duration': float(v)})
            elif t == 'click':
                c = v.split(',')
                if len(c) >= 2:
                    actions.append({'type': 'click', 'x': int(c[0]), 'y': int(c[1]),
                                   'button': c[2] if len(c) > 2 else 'left'})
            elif t == 'chat':
                actions.append({'type': 'chat', 'text': v})
            elif t == 'key':
                actions.append({'type': 'key', 'key': v})
        return actions
    
    def delete_sequence(self, name):
        if name in self.sequences:
            del self.sequences[name]
            self.save_config()
            self.refresh_sequences()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not HAS_WEBSOCKETS:
        import tkinter.messagebox
        tkinter.messagebox.showerror("Erreur", "pip install websockets")
    else:
        app = DofusClient()
        app.run()
