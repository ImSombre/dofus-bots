"""
🎮 Client Dofus - Contrôle à distance avec VISUALISATION D'ÉCRAN
Version avec partage d'écran en temps réel et interaction
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import asyncio
from datetime import datetime
import base64
import io

# WebSocket
try:
    import websockets
    HAS_WEBSOCKETS = True
except:
    HAS_WEBSOCKETS = False

# PIL pour afficher les images
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except:
    HAS_PIL = False


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
        
        # Screen state
        self.screen_watching = False
        self.screen_available = False
        self.server_screen_width = 1920
        self.server_screen_height = 1080
        self.current_frame = None
        self.screen_scale = 1.0  # Échelle pour conversion coordonnées
        
        # Drag state
        self.is_dragging = False
        self.drag_button = None
        
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
        self.root.geometry("900x900")
        self.root.configure(bg=self.c['bg'])
        self.root.resizable(True, True)
        self.root.minsize(700, 800)
        
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
        
        # Tab 1: Écran (NOUVEAU!)
        self.create_screen_tab()
        
        # Tab 2: Chat
        self.create_chat_tab()
        
        # Tab 3: Macros
        self.create_macros_tab()
        
        # Tab 4: Séquences
        self.create_sequences_tab()
        
        # ===== FOOTER LOG =====
        log_frame = tk.Frame(self.root, bg=self.c['card'], height=80)
        log_frame.pack(fill='x', padx=15, pady=10)
        log_frame.pack_propagate(False)
        
        self.log_text = tk.Text(log_frame, bg=self.c['card'], fg=self.c['text2'],
                                font=('Consolas', 9), wrap='word', height=4,
                                relief='flat', state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=5)
    
    def create_screen_tab(self):
        """Onglet de visualisation d'écran"""
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="📺 Écran")
        
        # Contrôles en haut
        controls = tk.Frame(tab, bg=self.c['card'], padx=10, pady=10)
        controls.pack(fill='x', padx=5, pady=5)
        
        self.screen_btn = tk.Button(controls, text="▶️ Voir l'écran", 
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=self.c['green'], fg='white', relief='flat',
                                    command=self.toggle_screen, cursor='hand2')
        self.screen_btn.pack(side='left', padx=5, ipadx=10, ipady=3)
        
        # Bouton plein écran
        self.fullscreen_btn = tk.Button(controls, text="⛶ Plein écran", 
                                        font=('Segoe UI', 10, 'bold'),
                                        bg=self.c['blue'], fg='white', relief='flat',
                                        command=self.toggle_fullscreen, cursor='hand2')
        self.fullscreen_btn.pack(side='left', padx=5, ipadx=10, ipady=3)
        
        self.screen_status = tk.Label(controls, text="⚪ Arrêté", 
                                      font=('Segoe UI', 10),
                                      bg=self.c['card'], fg=self.c['text2'])
        self.screen_status.pack(side='left', padx=15)
        
        # Checkbox pour interaction
        self.interact_var = tk.BooleanVar(value=True)
        self.interact_check = tk.Checkbutton(controls, text="🖱️ Permettre interaction",
                                              variable=self.interact_var,
                                              bg=self.c['card'], fg=self.c['text'],
                                              selectcolor=self.c['input'],
                                              activebackground=self.c['card'],
                                              font=('Segoe UI', 9))
        self.interact_check.pack(side='left', padx=10)
        
        self.fps_label = tk.Label(controls, text="", font=('Segoe UI', 9),
                                  bg=self.c['card'], fg=self.c['blue'])
        self.fps_label.pack(side='right', padx=10)
        
        # Zone d'affichage de l'écran
        self.screen_frame = tk.Frame(tab, bg=self.c['input'])
        self.screen_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Canvas pour l'image
        self.screen_canvas = tk.Canvas(self.screen_frame, bg='#000000', 
                                        highlightthickness=0, cursor='crosshair')
        self.screen_canvas.pack(fill='both', expand=True)
        
        # Message initial
        self.screen_canvas.create_text(400, 200, text="📺 Clique sur 'Voir l'écran' pour commencer\n\n[F11] pour plein écran • [Échap] pour quitter",
                                       fill=self.c['text2'], font=('Segoe UI', 14),
                                       tags='placeholder')
        
        # Bindings pour l'interaction
        self.screen_canvas.bind('<ButtonPress-1>', lambda e: self.on_mouse_down(e, 'left'))
        self.screen_canvas.bind('<ButtonRelease-1>', lambda e: self.on_mouse_up(e, 'left'))
        self.screen_canvas.bind('<ButtonPress-3>', lambda e: self.on_mouse_down(e, 'right'))
        self.screen_canvas.bind('<ButtonRelease-3>', lambda e: self.on_mouse_up(e, 'right'))
        self.screen_canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.screen_canvas.bind('<B3-Motion>', self.on_mouse_drag)
        self.screen_canvas.bind('<Double-Button-1>', lambda e: self.on_double_click(e))
        self.screen_canvas.bind('<MouseWheel>', self.on_screen_scroll)
        
        # Binding clavier
        self.screen_canvas.bind('<Key>', self.on_screen_key)
        self.screen_canvas.bind('<Enter>', lambda e: self.screen_canvas.focus_set())
        
        # Bindings plein écran
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Escape>', lambda e: self.exit_fullscreen())
        
        # Variables pour le FPS
        self.frame_count = 0
        self.last_fps_time = datetime.now()
        
        # État plein écran
        self.is_fullscreen = False
        self.fullscreen_window = None
    
    def create_chat_tab(self):
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="💬 Chat")
        
        main = tk.Frame(tab, bg=self.c['card'], padx=20, pady=20)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
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
        
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=20)
        
        # Clic
        tk.Label(main, text="🖱️ Clic à une position", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w', pady=(0,10))
        
        click_row = tk.Frame(main, bg=self.c['card'])
        click_row.pack(fill='x', pady=5)
        
        tk.Label(click_row, text="X:", bg=self.c['card'], fg=self.c['text']).pack(side='left')
        self.click_x = tk.Entry(click_row, width=6, bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.click_x.insert(0, "960")
        self.click_x.pack(side='left', padx=5, ipady=3)
        
        tk.Label(click_row, text="Y:", bg=self.c['card'], fg=self.c['text']).pack(side='left', padx=(10,0))
        self.click_y = tk.Entry(click_row, width=6, bg=self.c['input'], fg=self.c['text'], relief='flat')
        self.click_y.insert(0, "540")
        self.click_y.pack(side='left', padx=5, ipady=3)
        
        tk.Button(click_row, text="Gauche", bg=self.c['accent'], fg='white', relief='flat',
                 command=lambda: self.send_click('left')).pack(side='left', padx=10)
        tk.Button(click_row, text="Droit", bg=self.c['orange'], fg='black', relief='flat',
                 command=lambda: self.send_click('right')).pack(side='left')
        
        # Commandes rapides
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=20)
        
        tk.Label(main, text="⚡ Commandes rapides", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w', pady=(0,10))
        
        quick_row = tk.Frame(main, bg=self.c['card'])
        quick_row.pack(fill='x')
        
        for cmd in ["/w ami ", "/g ", "/b "]:
            tk.Button(quick_row, text=cmd, bg=self.c['input'], fg=self.c['text'], relief='flat',
                     command=lambda c=cmd: self.quick_chat(c)).pack(side='left', padx=3)
    
    def create_macros_tab(self):
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="⚡ Macros")
        
        main = tk.Frame(tab, bg=self.c['card'], padx=20, pady=20)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(main, text="➕ Nouvelle macro", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w', pady=(0,10))
        
        add_row = tk.Frame(main, bg=self.c['card'])
        add_row.pack(fill='x', pady=5)
        
        self.macro_name = tk.Entry(add_row, width=10, bg=self.c['input'], 
                                   fg=self.c['text'], relief='flat')
        self.macro_name.insert(0, "nom")
        self.macro_name.pack(side='left', ipady=5, padx=2)
        
        self.macro_cmd = tk.Entry(add_row, width=25, bg=self.c['input'],
                                  fg=self.c['text'], relief='flat')
        self.macro_cmd.insert(0, "/commande")
        self.macro_cmd.pack(side='left', ipady=5, padx=2)
        
        tk.Button(add_row, text="➕", bg=self.c['green'], fg='white', relief='flat',
                 command=self.add_macro).pack(side='left', padx=5)
        
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=15)
        
        self.macros_frame = tk.Frame(main, bg=self.c['card'])
        self.macros_frame.pack(fill='both', expand=True)
        self.refresh_macros()
    
    def create_sequences_tab(self):
        tab = tk.Frame(self.notebook, bg=self.c['bg'])
        self.notebook.add(tab, text="🎬 Séquences")
        
        main = tk.Frame(tab, bg=self.c['card'], padx=20, pady=20)
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(main, text="➕ Nouvelle séquence", font=('Segoe UI', 11, 'bold'),
                bg=self.c['card'], fg=self.c['text']).pack(anchor='w')
        
        tk.Label(main, text="Format: wait=2; click=100,200; chat=/salut; key=enter",
                font=('Segoe UI', 9), bg=self.c['card'], fg=self.c['text2']).pack(anchor='w', pady=(0,10))
        
        add_row = tk.Frame(main, bg=self.c['card'])
        add_row.pack(fill='x', pady=5)
        
        self.seq_name = tk.Entry(add_row, width=10, bg=self.c['input'],
                                 fg=self.c['text'], relief='flat')
        self.seq_name.insert(0, "nom")
        self.seq_name.pack(side='left', ipady=5, padx=2)
        
        self.seq_actions = tk.Entry(add_row, width=35, bg=self.c['input'],
                                    fg=self.c['text'], relief='flat')
        self.seq_actions.pack(side='left', ipady=5, padx=2)
        
        tk.Button(add_row, text="➕", bg=self.c['green'], fg='white', relief='flat',
                 command=self.add_sequence).pack(side='left', padx=5)
        
        tk.Frame(main, bg=self.c['input'], height=2).pack(fill='x', pady=15)
        
        self.sequences_frame = tk.Frame(main, bg=self.c['card'])
        self.sequences_frame.pack(fill='both', expand=True)
        self.refresh_sequences()
    
    # ===== SCREEN METHODS =====
    
    def toggle_screen(self):
        """Active/désactive le partage d'écran"""
        if not self.connected:
            self.log("❌ Non connecté!")
            return
        
        if not self.screen_available:
            self.log("❌ Partage d'écran non disponible sur le serveur")
            return
        
        if self.screen_watching:
            self.stop_screen()
        else:
            self.start_screen()
    
    def start_screen(self):
        """Démarre la visualisation d'écran"""
        self.screen_watching = True
        self.screen_btn.config(text="⏹️ Arrêter", bg=self.c['red'])
        self.screen_status.config(text="🟢 En cours...", fg=self.c['green'])
        self.screen_canvas.delete('placeholder')
        self.send_command({'type': 'start_screen'})
        self.log("📺 Visualisation démarrée")
    
    def stop_screen(self):
        """Arrête la visualisation d'écran"""
        self.screen_watching = False
        self.screen_btn.config(text="▶️ Voir l'écran", bg=self.c['green'])
        self.screen_status.config(text="⚪ Arrêté", fg=self.c['text2'])
        self.send_command({'type': 'stop_screen'})
        self.log("📺 Visualisation arrêtée")
    
    def toggle_fullscreen(self):
        """Bascule en mode plein écran"""
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()
    
    def enter_fullscreen(self):
        """Entre en mode plein écran"""
        if self.is_fullscreen:
            return
        
        self.is_fullscreen = True
        
        # Créer une fenêtre plein écran
        self.fullscreen_window = tk.Toplevel(self.root)
        self.fullscreen_window.title("📺 Écran distant - Plein écran")
        self.fullscreen_window.configure(bg='black')
        self.fullscreen_window.attributes('-fullscreen', True)
        self.fullscreen_window.attributes('-topmost', True)
        
        # Canvas plein écran
        self.fullscreen_canvas = tk.Canvas(self.fullscreen_window, bg='#000000', 
                                            highlightthickness=0, cursor='crosshair')
        self.fullscreen_canvas.pack(fill='both', expand=True)
        
        # Label FPS
        self.fullscreen_fps = tk.Label(self.fullscreen_window, text="", 
                                       font=('Segoe UI', 10, 'bold'),
                                       bg='black', fg='#00ff00')
        self.fullscreen_fps.place(x=10, y=10)
        
        # Label aide
        help_text = "[Échap] ou [F11] pour quitter"
        self.fullscreen_help = tk.Label(self.fullscreen_window, text=help_text,
                                        font=('Segoe UI', 9),
                                        bg='black', fg='#666666')
        self.fullscreen_help.place(relx=0.5, y=10, anchor='n')
        
        # Bindings - même que le canvas normal
        self.fullscreen_window.bind('<Escape>', lambda e: self.exit_fullscreen())
        self.fullscreen_window.bind('<F11>', lambda e: self.exit_fullscreen())
        self.fullscreen_canvas.bind('<ButtonPress-1>', lambda e: self.on_mouse_down(e, 'left'))
        self.fullscreen_canvas.bind('<ButtonRelease-1>', lambda e: self.on_mouse_up(e, 'left'))
        self.fullscreen_canvas.bind('<ButtonPress-3>', lambda e: self.on_mouse_down(e, 'right'))
        self.fullscreen_canvas.bind('<ButtonRelease-3>', lambda e: self.on_mouse_up(e, 'right'))
        self.fullscreen_canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.fullscreen_canvas.bind('<B3-Motion>', self.on_mouse_drag)
        self.fullscreen_canvas.bind('<Double-Button-1>', lambda e: self.on_double_click(e))
        self.fullscreen_canvas.bind('<MouseWheel>', self.on_screen_scroll)
        self.fullscreen_canvas.bind('<Key>', self.on_screen_key)
        self.fullscreen_canvas.bind('<Enter>', lambda e: self.fullscreen_canvas.focus_set())
        
        self.fullscreen_btn.config(text="⛶ Quitter plein écran", bg=self.c['orange'])
        self.log("📺 Mode plein écran activé")
    
    def exit_fullscreen(self):
        """Quitte le mode plein écran"""
        if not self.is_fullscreen:
            return
        
        self.is_fullscreen = False
        
        if self.fullscreen_window:
            self.fullscreen_window.destroy()
            self.fullscreen_window = None
            self.fullscreen_canvas = None
        
        self.fullscreen_btn.config(text="⛶ Plein écran", bg=self.c['blue'])
        # Réinitialiser le cache de taille pour forcer le recalcul
        if hasattr(self, '_last_canvas_size'):
            delattr(self, '_last_canvas_size')
        self.log("📺 Mode plein écran désactivé")
    
    def on_double_click(self, event):
        """Double-clic distant (envoie un vrai double-clic)"""
        if not self.screen_watching or not self.interact_var.get():
            return
        
        try:
            coords = self._get_real_coords(event)
            if coords:
                real_x, real_y = coords
                self.send_command({
                    'type': 'remote_dblclick',
                    'x': real_x,
                    'y': real_y
                })
        except:
            pass
    
    def on_mouse_down(self, event, button):
        """Clic enfoncé - début du drag potentiel"""
        if not self.screen_watching or not self.interact_var.get():
            return
        
        try:
            coords = self._get_real_coords(event)
            if coords:
                real_x, real_y = coords
                self.is_dragging = True
                self.drag_button = button
                
                # Envoyer mouse down
                self.send_command({
                    'type': 'remote_mousedown',
                    'x': real_x,
                    'y': real_y,
                    'button': button
                })
        except:
            pass
    
    def on_mouse_up(self, event, button):
        """Clic relâché - fin du drag"""
        if not self.screen_watching or not self.interact_var.get():
            return
        
        try:
            coords = self._get_real_coords(event)
            if coords:
                real_x, real_y = coords
                
                # Envoyer mouse up
                self.send_command({
                    'type': 'remote_mouseup',
                    'x': real_x,
                    'y': real_y,
                    'button': button
                })
                
            self.is_dragging = False
            self.drag_button = None
        except:
            pass
    
    def on_mouse_drag(self, event):
        """Mouvement de souris pendant le drag"""
        if not self.screen_watching or not self.interact_var.get():
            return
        if not self.is_dragging:
            return
        
        try:
            coords = self._get_real_coords(event)
            if coords:
                real_x, real_y = coords
                
                # Envoyer position de la souris
                self.send_command({
                    'type': 'remote_mousemove',
                    'x': real_x,
                    'y': real_y
                })
        except:
            pass
    
    def _get_real_coords(self, event):
        """Convertit les coordonnées canvas en coordonnées écran réelles"""
        try:
            if not hasattr(self, 'display_offset_x'):
                return None
                
            rel_x = event.x - self.display_offset_x
            rel_y = event.y - self.display_offset_y
            
            # Vérifier si on est dans l'image
            if rel_x < 0 or rel_y < 0 or rel_x > self.display_width or rel_y > self.display_height:
                return None
            
            real_x = int(rel_x * self.screen_scale)
            real_y = int(rel_y * self.screen_scale)
            
            return (real_x, real_y)
        except:
            return None
    
    # Garder pour compatibilité
    def on_screen_double_click(self, event):
        self.on_double_click(event)
    
    def update_screen(self, frame_data):
        """Met à jour l'affichage de l'écran - VERSION 30+ FPS"""
        if not HAS_PIL or not self.screen_watching:
            return
        
        try:
            # Nouveaux noms courts ou anciens noms (compatibilité)
            data = frame_data.get('d') or frame_data.get('data')
            orig_w = frame_data.get('ow') or frame_data.get('original_width', 1920)
            orig_h = frame_data.get('oh') or frame_data.get('original_height', 1080)
            
            # Décoder l'image base64
            img_data = base64.b64decode(data)
            img = Image.open(io.BytesIO(img_data))
            
            # Choisir le canvas actif (plein écran ou normal)
            if self.is_fullscreen and self.fullscreen_canvas:
                canvas = self.fullscreen_canvas
            else:
                canvas = self.screen_canvas
            
            # Obtenir la taille du canvas
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            if canvas_width < 50 or canvas_height < 50:
                return
            
            # Calculer la taille - cache par canvas
            cache_key = (canvas_width, canvas_height, id(canvas))
            if not hasattr(self, '_size_cache') or self._size_cache.get('key') != cache_key:
                img_ratio = img.width / img.height
                canvas_ratio = canvas_width / canvas_height
                
                if img_ratio > canvas_ratio:
                    tw = canvas_width
                    th = int(canvas_width / img_ratio)
                else:
                    th = canvas_height
                    tw = int(canvas_height * img_ratio)
                
                self._size_cache = {
                    'key': cache_key,
                    'tw': tw, 'th': th,
                    'ox': (canvas_width - tw) // 2,
                    'oy': (canvas_height - th) // 2
                }
            
            sc = self._size_cache
            self.display_offset_x = sc['ox']
            self.display_offset_y = sc['oy']
            self.display_width = sc['tw']
            self.display_height = sc['th']
            self.screen_scale = orig_w / sc['tw']
            
            # Redimensionner seulement si nécessaire
            if img.size != (sc['tw'], sc['th']):
                img = img.resize((sc['tw'], sc['th']), Image.NEAREST)
            
            # Convertir et afficher
            self.current_frame = ImageTk.PhotoImage(img)
            canvas.delete('screen_img')
            canvas.create_image(canvas_width // 2, canvas_height // 2,
                               image=self.current_frame, anchor='center', tags='screen_img')
            
            # FPS counter
            self.frame_count += 1
            now = datetime.now()
            elapsed = (now - self.last_fps_time).total_seconds()
            if elapsed >= 1.0:
                fps = self.frame_count / elapsed
                fps_text = f"{fps:.1f} FPS"
                self.fps_label.config(text=fps_text)
                if self.is_fullscreen and hasattr(self, 'fullscreen_fps'):
                    self.fullscreen_fps.config(text=fps_text)
                self.frame_count = 0
                self.last_fps_time = now
                
        except:
            pass
    
    def on_screen_click(self, event, button):
        """Ancien handler - redirige vers on_mouse_down/up"""
        self.on_mouse_down(event, button)
        self.root.after(50, lambda: self.on_mouse_up(event, button))
    
    def on_screen_scroll(self, event):
        """Gère le scroll sur l'écran distant"""
        if not self.screen_watching or not self.interact_var.get():
            return
        
        delta = event.delta // 120  # Normaliser le delta
        self.send_command({
            'type': 'remote_scroll',
            'delta': delta
        })
    
    def on_screen_key(self, event):
        """Gère les touches clavier sur l'écran distant"""
        if not self.screen_watching or not self.interact_var.get():
            return
        
        # Mapping des touches spéciales
        key_map = {
            'Return': 'enter',
            'Escape': 'escape',
            'BackSpace': 'backspace',
            'Tab': 'tab',
            'space': 'space',
            'Up': 'up',
            'Down': 'down',
            'Left': 'left',
            'Right': 'right',
            'Delete': 'delete',
            'Home': 'home',
            'End': 'end',
        }
        
        key = event.keysym
        if key in key_map:
            self.send_command({
                'type': 'remote_key',
                'key': key_map[key]
            })
        elif len(key) == 1:  # Caractère simple
            self.send_command({
                'type': 'remote_type',
                'text': event.char
            })
    
    # ===== LOG =====
    
    def log(self, msg):
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')
    
    # ===== CONNECTION =====
    
    def toggle_connection(self):
        if self.running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        self.server_host = self.host_entry.get().strip()
        self.server_port = int(self.port_entry.get().strip())
        self.auth_key = self.key_entry.get().strip()
        self.save_config()
        
        if not self.server_host:
            messagebox.showwarning("Attention", "Entre l'adresse du serveur!")
            return
        
        self.running = True
        self.connect_btn.config(text="🔌 DÉCONNECTER", bg=self.c['red'])
        self.log(f"Connexion à {self.server_host}:{self.server_port}...")
        
        def run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.send_queue = asyncio.Queue()
            self.loop.run_until_complete(self.connection_loop())
        
        threading.Thread(target=run, daemon=True).start()
    
    def disconnect(self):
        self.running = False
        self.connected = False
        self.screen_watching = False
        
        # Quitter le plein écran si actif
        if self.is_fullscreen:
            self.exit_fullscreen()
        
        self.connect_btn.config(text="🔌 SE CONNECTER", bg=self.c['green'])
        self.status_dot.config(fg=self.c['red'])
        self.screen_btn.config(text="▶️ Voir l'écran", bg=self.c['green'])
        self.screen_status.config(text="⚪ Arrêté", fg=self.c['text2'])
        self.log("Déconnecté")
    
    async def connection_loop(self):
        while self.running:
            try:
                uri = f"ws://{self.server_host}:{self.server_port}"
                
                async with websockets.connect(
                    uri,
                    ping_interval=20,
                    ping_timeout=60,
                    max_size=10 * 1024 * 1024  # 10MB max pour les frames
                ) as ws:
                    self.websocket = ws
                    self.root.after(0, lambda: self.log("Connecté, authentification..."))
                    
                    await ws.send(json.dumps({
                        'type': 'auth',
                        'key': self.auth_key,
                        'name': 'Client'
                    }))
                    
                    response = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if data.get('type') == 'auth_ok':
                        self.connected = True
                        self.screen_available = data.get('screen_available', False)
                        self.server_screen_width = data.get('screen_width', 1920)
                        self.server_screen_height = data.get('screen_height', 1080)
                        
                        self.root.after(0, lambda: self.log("✅ Connecté!"))
                        self.root.after(0, lambda: self.status_dot.config(fg=self.c['green']))
                        
                        if self.screen_available:
                            self.root.after(0, lambda: self.log(f"📺 Partage d'écran disponible ({self.server_screen_width}x{self.server_screen_height})"))
                        
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
                self.root.after(0, lambda: self.log(f"❌ Erreur: {e}"))
            
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
                    
                try:
                    data = json.loads(msg)
                    
                    # Nouveau format compact ou ancien format
                    msg_type = data.get('t') or data.get('type')
                    
                    # Frame d'écran (priorité haute)
                    if msg_type in ('sf', 'screen_frame'):
                        frame = data.get('f') or data.get('frame')
                        if frame and self.screen_watching:
                            self.root.after_idle(lambda f=frame: self.update_screen(f))
                    elif msg_type == 'result':
                        if data.get('success'):
                            self.root.after(0, lambda: self.log("✅ OK"))
                except:
                    pass
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
    missing = []
    if not HAS_WEBSOCKETS:
        missing.append("websockets")
    
    warnings = []
    if not HAS_PIL:
        warnings.append("Pillow (pour visualiser l'écran)")
    
    if missing:
        import tkinter.messagebox
        tkinter.messagebox.showerror("Erreur", f"Modules manquants:\n\npip install {' '.join(missing)}")
    else:
        if warnings:
            print(f"⚠️ Modules optionnels manquants: {', '.join(warnings)}")
            print(f"   pip install Pillow")
        app = DofusClient()
        app.run()
