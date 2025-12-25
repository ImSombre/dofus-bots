"""
🤖 Dofus Autonomous Agent v1.0
Agent autonome intelligent pour Dofus avec:
- Navigation entre maps (graphe)
- Détection et engagement de monstres
- Système de combat intelligent (sorts, cooldowns, priorités)
- Apprentissage par démonstration
"""

import cv2
import numpy as np
import pyautogui
import time
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageGrab, Image, ImageTk
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import heapq
import random

# Configuration pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

# ============================================================
#                    STRUCTURES DE DONNÉES
# ============================================================

class ActionType(Enum):
    MOVE = "move"
    SPELL = "spell"
    PASS_TURN = "pass"
    USE_ITEM = "item"
    FLEE = "flee"

class CombatPhase(Enum):
    PLACEMENT = "placement"
    PLAYER_TURN = "player_turn"
    ENEMY_TURN = "enemy_turn"
    VICTORY = "victory"
    DEFEAT = "defeat"

@dataclass
class Position:
    x: int
    y: int
    
    def distance_to(self, other: 'Position') -> int:
        """Distance de Manhattan (Dofus utilise une grille)"""
        return abs(self.x - other.x) + abs(self.y - other.y)
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

@dataclass
class Spell:
    id: int
    name: str
    key: str  # Touche clavier
    min_range: int = 1
    max_range: int = 1
    cost_pa: int = 3
    cooldown: int = 0
    priority: int = 5  # 1-10, 10 = haute priorité
    damage: int = 0
    is_heal: bool = False
    is_buff: bool = False
    is_aoe: bool = False
    current_cooldown: int = 0
    
    def is_available(self, pa_remaining: int) -> bool:
        return self.current_cooldown == 0 and pa_remaining >= self.cost_pa
    
    def in_range(self, distance: int) -> bool:
        return self.min_range <= distance <= self.max_range

@dataclass
class Entity:
    name: str
    position: Position
    hp: int = 100
    max_hp: int = 100
    pa: int = 6
    pm: int = 3
    is_enemy: bool = True
    threat_level: int = 5  # 1-10
    
    @property
    def hp_percent(self) -> float:
        return (self.hp / self.max_hp) * 100 if self.max_hp > 0 else 0

@dataclass
class MapNode:
    id: str
    name: str
    position: Tuple[int, int]  # Position monde
    connections: Dict[str, str] = field(default_factory=dict)  # direction -> map_id
    has_monsters: bool = False
    monster_level_range: Tuple[int, int] = (1, 50)
    is_safe_zone: bool = False
    visit_count: int = 0
    last_visit: float = 0

@dataclass 
class CombatState:
    phase: CombatPhase = CombatPhase.PLACEMENT
    turn: int = 0
    player: Optional[Entity] = None
    enemies: List[Entity] = field(default_factory=list)
    pa_remaining: int = 6
    pm_remaining: int = 3

@dataclass
class DemonstrationAction:
    """Action enregistrée pendant une démonstration"""
    timestamp: float
    action_type: ActionType
    target_position: Optional[Position] = None
    spell_id: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)


# ============================================================
#                    SYSTÈME DE NAVIGATION
# ============================================================

class MapGraph:
    """Graphe de navigation entre les maps"""
    
    def __init__(self):
        self.nodes: Dict[str, MapNode] = {}
        self.current_map: Optional[str] = None
        
    def add_map(self, map_node: MapNode):
        self.nodes[map_node.id] = map_node
    
    def connect_maps(self, map1_id: str, direction: str, map2_id: str):
        """Connecte deux maps dans une direction"""
        opposite = {"north": "south", "south": "north", 
                    "east": "west", "west": "east"}
        
        if map1_id in self.nodes:
            self.nodes[map1_id].connections[direction] = map2_id
        if map2_id in self.nodes:
            self.nodes[map2_id].connections[opposite[direction]] = map1_id
    
    def find_path(self, start_id: str, goal_id: str) -> List[str]:
        """Trouve le chemin le plus court (A*)"""
        if start_id not in self.nodes or goal_id not in self.nodes:
            return []
        
        frontier = [(0, start_id, [start_id])]
        visited = set()
        
        while frontier:
            cost, current, path = heapq.heappop(frontier)
            
            if current == goal_id:
                return path
            
            if current in visited:
                continue
            visited.add(current)
            
            for direction, next_map in self.nodes[current].connections.items():
                if next_map not in visited:
                    new_path = path + [next_map]
                    heapq.heappush(frontier, (len(new_path), next_map, new_path))
        
        return []
    
    def find_nearest_monster_map(self, from_id: str, level_range: Tuple[int, int] = (1, 200)) -> Optional[str]:
        """Trouve la map avec monstres la plus proche"""
        for node in sorted(self.nodes.values(), 
                          key=lambda n: len(self.find_path(from_id, n.id))):
            if node.has_monsters and not node.is_safe_zone:
                if level_range[0] <= node.monster_level_range[0] <= level_range[1]:
                    return node.id
        return None


# ============================================================
#                    SYSTÈME DE VISION
# ============================================================

class VisionSystem:
    """Système de détection visuelle"""
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.mob_templates: List[Tuple[str, np.ndarray]] = []
        self.ui_templates: Dict[str, np.ndarray] = {}
        self.load_templates()
    
    def load_templates(self):
        """Charge les templates de mobs et UI"""
        mob_dir = os.path.join(self.config_dir, "mobs")
        if os.path.exists(mob_dir):
            for f in os.listdir(mob_dir):
                if f.endswith('.png'):
                    path = os.path.join(mob_dir, f)
                    template = cv2.imread(path)
                    if template is not None:
                        self.mob_templates.append((f, template))
        
        ui_dir = os.path.join(self.config_dir, "ui")
        if os.path.exists(ui_dir):
            for f in os.listdir(ui_dir):
                if f.endswith('.png'):
                    name = f.replace('.png', '')
                    path = os.path.join(ui_dir, f)
                    template = cv2.imread(path)
                    if template is not None:
                        self.ui_templates[name] = template
    
    def capture_screen(self) -> np.ndarray:
        """Capture l'écran"""
        screenshot = ImageGrab.grab()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    def find_template(self, screen: np.ndarray, template: np.ndarray, 
                      threshold: float = 0.7) -> List[Tuple[int, int, float]]:
        """Trouve toutes les occurrences d'un template"""
        if template is None or screen is None:
            return []
        
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        matches = []
        h, w = template.shape[:2]
        
        for pt in zip(*locations[::-1]):
            cx = pt[0] + w // 2
            cy = pt[1] + h // 2
            confidence = result[pt[1], pt[0]]
            matches.append((cx, cy, confidence))
        
        # NMS simple
        return self._non_max_suppression(matches, 30)
    
    def _non_max_suppression(self, matches: List[Tuple[int, int, float]], 
                              min_distance: int) -> List[Tuple[int, int, float]]:
        """Supprime les détections trop proches"""
        if not matches:
            return []
        
        sorted_matches = sorted(matches, key=lambda x: x[2], reverse=True)
        kept = []
        
        for m in sorted_matches:
            too_close = False
            for k in kept:
                dist = abs(m[0] - k[0]) + abs(m[1] - k[1])
                if dist < min_distance:
                    too_close = True
                    break
            if not too_close:
                kept.append(m)
        
        return kept
    
    def detect_mobs(self) -> List[Tuple[str, int, int, float]]:
        """Détecte tous les mobs à l'écran"""
        screen = self.capture_screen()
        all_mobs = []
        
        for name, template in self.mob_templates:
            matches = self.find_template(screen, template, 0.65)
            for x, y, conf in matches:
                all_mobs.append((name, x, y, conf))
        
        return all_mobs
    
    def detect_ui_element(self, element_name: str) -> Optional[Tuple[int, int]]:
        """Détecte un élément d'UI"""
        if element_name not in self.ui_templates:
            return None
        
        screen = self.capture_screen()
        matches = self.find_template(screen, self.ui_templates[element_name], 0.8)
        
        if matches:
            return (matches[0][0], matches[0][1])
        return None
    
    def is_in_combat(self) -> bool:
        """Détecte si on est en combat"""
        # Cherche la timeline ou les PA/PM
        screen = self.capture_screen()
        
        # Méthode simple: chercher des pixels caractéristiques du combat
        # À adapter selon l'interface Dofus
        if 'combat_indicator' in self.ui_templates:
            matches = self.find_template(screen, self.ui_templates['combat_indicator'], 0.8)
            return len(matches) > 0
        
        return False


# ============================================================
#                    SYSTÈME DE COMBAT IA
# ============================================================

class CombatAI:
    """IA de combat intelligente"""
    
    def __init__(self, spells: List[Spell]):
        self.spells = {s.id: s for s in spells}
        self.state = CombatState()
        self.learned_patterns: List[Dict] = []
        self.strategy = "balanced"  # aggressive, defensive, balanced
    
    def set_strategy(self, strategy: str):
        self.strategy = strategy
    
    def update_state(self, player: Entity, enemies: List[Entity], 
                     pa: int, pm: int, phase: CombatPhase):
        """Met à jour l'état du combat"""
        self.state.player = player
        self.state.enemies = enemies
        self.state.pa_remaining = pa
        self.state.pm_remaining = pm
        self.state.phase = phase
    
    def select_target(self) -> Optional[Entity]:
        """Sélectionne la meilleure cible"""
        if not self.state.enemies:
            return None
        
        # Scoring des cibles
        scored = []
        for enemy in self.state.enemies:
            score = 0
            
            # Distance (plus proche = mieux)
            if self.state.player:
                dist = self.state.player.position.distance_to(enemy.position)
                score += (20 - dist) * 2
            
            # HP bas = priorité haute
            score += (100 - enemy.hp_percent) * 1.5
            
            # Threat level
            score += enemy.threat_level * 3
            
            # Stratégie
            if self.strategy == "aggressive":
                score += enemy.threat_level * 2
            elif self.strategy == "defensive":
                score += (100 - enemy.hp_percent)
            
            scored.append((enemy, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None
    
    def select_spell(self, target: Entity) -> Optional[Spell]:
        """Sélectionne le meilleur sort pour la cible"""
        if not self.state.player:
            return None
        
        distance = self.state.player.position.distance_to(target.position)
        available_spells = []
        
        for spell in self.spells.values():
            if spell.is_available(self.state.pa_remaining) and spell.in_range(distance):
                # Score le sort
                score = spell.priority * 10
                
                # Bonus dégâts si stratégie aggressive
                if self.strategy == "aggressive":
                    score += spell.damage * 0.5
                
                # Bonus heal si HP bas
                if spell.is_heal and self.state.player.hp_percent < 50:
                    score += 50
                
                # Bonus AOE si plusieurs ennemis proches
                if spell.is_aoe:
                    nearby = sum(1 for e in self.state.enemies 
                                if e.position.distance_to(target.position) <= 2)
                    score += nearby * 20
                
                available_spells.append((spell, score))
        
        if not available_spells:
            return None
        
        available_spells.sort(key=lambda x: x[1], reverse=True)
        return available_spells[0][0]
    
    def calculate_best_position(self) -> Optional[Position]:
        """Calcule la meilleure position où se déplacer"""
        if not self.state.player or not self.state.enemies:
            return None
        
        target = self.select_target()
        if not target:
            return None
        
        # Trouver les sorts avec les meilleures portées
        best_range = 1
        for spell in self.spells.values():
            if spell.damage > 0 and spell.max_range > best_range:
                best_range = spell.max_range
        
        # Position idéale: à portée du meilleur sort
        player_pos = self.state.player.position
        target_pos = target.position
        
        # Calculer la direction vers la cible
        dx = 1 if target_pos.x > player_pos.x else (-1 if target_pos.x < player_pos.x else 0)
        dy = 1 if target_pos.y > player_pos.y else (-1 if target_pos.y < player_pos.y else 0)
        
        # Se rapprocher jusqu'à être à portée
        current_dist = player_pos.distance_to(target_pos)
        
        if current_dist > best_range:
            # Se rapprocher
            new_x = player_pos.x + dx * min(self.state.pm_remaining, current_dist - best_range)
            new_y = player_pos.y + dy * min(self.state.pm_remaining, current_dist - best_range)
            return Position(int(new_x), int(new_y))
        elif current_dist < 2 and self.strategy == "defensive":
            # S'éloigner si trop proche en mode défensif
            new_x = player_pos.x - dx * min(self.state.pm_remaining, 2)
            new_y = player_pos.y - dy * min(self.state.pm_remaining, 2)
            return Position(int(new_x), int(new_y))
        
        return None
    
    def decide_action(self) -> Tuple[ActionType, Dict]:
        """Décide de la prochaine action"""
        if not self.state.player:
            return (ActionType.PASS_TURN, {})
        
        # 1. Sélectionner une cible
        target = self.select_target()
        
        if not target:
            return (ActionType.PASS_TURN, {})
        
        # 2. Vérifier si on peut attaquer
        distance = self.state.player.position.distance_to(target.position)
        spell = self.select_spell(target)
        
        if spell:
            return (ActionType.SPELL, {"spell": spell, "target": target})
        
        # 3. Si pas de sort disponible, se déplacer
        if self.state.pm_remaining > 0:
            new_pos = self.calculate_best_position()
            if new_pos:
                return (ActionType.MOVE, {"position": new_pos})
        
        # 4. Passer le tour
        return (ActionType.PASS_TURN, {})
    
    def end_turn(self):
        """Fin du tour - reset cooldowns"""
        for spell in self.spells.values():
            if spell.current_cooldown > 0:
                spell.current_cooldown -= 1
        self.state.turn += 1
    
    def learn_from_demonstration(self, actions: List[DemonstrationAction]):
        """Apprend d'une démonstration"""
        pattern = {
            "actions": [],
            "context": {}
        }
        
        for action in actions:
            pattern["actions"].append({
                "type": action.action_type.value,
                "spell_id": action.spell_id,
                "relative_target": None  # Calculer la position relative
            })
            pattern["context"].update(action.context)
        
        self.learned_patterns.append(pattern)
        print(f"📚 Pattern appris avec {len(actions)} actions")


# ============================================================
#                    CONTRÔLEUR D'ACTIONS
# ============================================================

class ActionController:
    """Exécute les actions dans le jeu"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.chat_key = config.get("chat_key", "enter")
        self.action_delay = config.get("action_delay", 0.3)
    
    def click(self, x: int, y: int, button: str = "left"):
        """Clique à une position"""
        pyautogui.click(x, y, button=button)
        time.sleep(self.action_delay)
    
    def press_key(self, key: str):
        """Appuie sur une touche"""
        pyautogui.press(key)
        time.sleep(0.1)
    
    def type_chat(self, message: str):
        """Envoie un message dans le chat"""
        self.press_key(self.chat_key)
        time.sleep(0.1)
        pyautogui.typewrite(message, interval=0.02)
        self.press_key("enter")
    
    def cast_spell(self, spell: Spell, target_x: int, target_y: int):
        """Lance un sort sur une cible"""
        # Appuyer sur la touche du sort
        self.press_key(spell.key)
        time.sleep(0.2)
        
        # Cliquer sur la cible
        self.click(target_x, target_y)
        
        # Mettre à jour le cooldown
        spell.current_cooldown = spell.cooldown
    
    def move_to(self, x: int, y: int):
        """Déplace le personnage"""
        self.click(x, y)
    
    def pass_turn(self):
        """Passe le tour"""
        self.press_key("space")  # ou le raccourci configuré
    
    def change_map(self, direction: str):
        """Change de map dans une direction"""
        screen_w, screen_h = pyautogui.size()
        
        positions = {
            "north": (screen_w // 2, 50),
            "south": (screen_w // 2, screen_h - 50),
            "east": (screen_w - 50, screen_h // 2),
            "west": (50, screen_h // 2)
        }
        
        if direction in positions:
            x, y = positions[direction]
            self.click(x, y)
            time.sleep(1.5)  # Attendre le chargement


# ============================================================
#                    AGENT AUTONOME
# ============================================================

class AutonomousAgent:
    """Agent autonome principal"""
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.config = self.load_config()
        
        # Sous-systèmes
        self.vision = VisionSystem(config_dir)
        self.map_graph = MapGraph()
        self.combat_ai = CombatAI(self.load_spells())
        self.controller = ActionController(self.config)
        
        # État
        self.running = False
        self.paused = False
        self.current_map = None
        self.mode = "farming"  # farming, exploration, quest
        
        # Stats
        self.stats = {
            "combats_won": 0,
            "combats_lost": 0,
            "maps_explored": 0,
            "start_time": None
        }
        
        # Démonstration
        self.is_recording = False
        self.recorded_actions: List[DemonstrationAction] = []
        self.record_start_time = 0
        
        # Callback pour l'UI
        self.callback = None
    
    def load_config(self) -> Dict:
        """Charge la configuration"""
        config_file = os.path.join(self.config_dir, "agent_config.json")
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        return {
            "chat_key": "enter",
            "action_delay": 0.3,
            "combat_delay": 2.0,
            "search_delay": 1.5,
            "strategy": "balanced",
            "target_level_range": [1, 50],
            "auto_heal_threshold": 30,
            "use_movemobs": False
        }
    
    def save_config(self):
        """Sauvegarde la configuration"""
        config_file = os.path.join(self.config_dir, "agent_config.json")
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_spells(self) -> List[Spell]:
        """Charge les sorts depuis la config"""
        spells_file = os.path.join(self.config_dir, "spells.json")
        
        if os.path.exists(spells_file):
            with open(spells_file, 'r') as f:
                data = json.load(f)
                return [Spell(**s) for s in data]
        
        # Sorts par défaut (exemple)
        return [
            Spell(id=1, name="Sort 1", key="1", min_range=1, max_range=6, 
                  cost_pa=3, damage=30, priority=8),
            Spell(id=2, name="Sort 2", key="2", min_range=1, max_range=4,
                  cost_pa=4, damage=45, priority=7),
            Spell(id=3, name="Soin", key="3", min_range=0, max_range=0,
                  cost_pa=2, is_heal=True, priority=9),
        ]
    
    def save_spells(self, spells: List[Spell]):
        """Sauvegarde les sorts"""
        spells_file = os.path.join(self.config_dir, "spells.json")
        data = [{"id": s.id, "name": s.name, "key": s.key, 
                 "min_range": s.min_range, "max_range": s.max_range,
                 "cost_pa": s.cost_pa, "cooldown": s.cooldown,
                 "priority": s.priority, "damage": s.damage,
                 "is_heal": s.is_heal, "is_buff": s.is_buff,
                 "is_aoe": s.is_aoe} for s in spells]
        
        with open(spells_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def log(self, msg: str):
        """Log un message"""
        print(f"[AGENT] {msg}")
        if self.callback:
            self.callback("log", msg)
    
    def set_callback(self, callback):
        """Définit le callback pour l'UI"""
        self.callback = callback
    
    # ===== ENREGISTREMENT / DÉMONSTRATION =====
    
    def start_recording(self):
        """Démarre l'enregistrement d'une démonstration"""
        self.is_recording = True
        self.recorded_actions = []
        self.record_start_time = time.time()
        self.log("🔴 Enregistrement démarré - Fais ton combat!")
    
    def stop_recording(self) -> List[DemonstrationAction]:
        """Arrête l'enregistrement"""
        self.is_recording = False
        self.log(f"⏹️ Enregistrement terminé - {len(self.recorded_actions)} actions")
        
        # Apprendre du pattern
        if self.recorded_actions:
            self.combat_ai.learn_from_demonstration(self.recorded_actions)
        
        return self.recorded_actions
    
    def record_action(self, action_type: ActionType, **kwargs):
        """Enregistre une action pendant la démonstration"""
        if not self.is_recording:
            return
        
        action = DemonstrationAction(
            timestamp=time.time() - self.record_start_time,
            action_type=action_type,
            target_position=kwargs.get("position"),
            spell_id=kwargs.get("spell_id"),
            context=kwargs.get("context", {})
        )
        self.recorded_actions.append(action)
    
    # ===== BOUCLE PRINCIPALE =====
    
    def run(self):
        """Boucle principale de l'agent"""
        self.running = True
        self.stats["start_time"] = datetime.now()
        self.log("🚀 Agent démarré!")
        
        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue
            
            try:
                # Vérifier si on est en combat
                if self.vision.is_in_combat():
                    self.handle_combat()
                else:
                    self.handle_exploration()
                
            except Exception as e:
                self.log(f"❌ Erreur: {e}")
                time.sleep(1)
        
        self.log("⏹️ Agent arrêté")
    
    def handle_exploration(self):
        """Gère l'exploration / farming"""
        self.log("🔍 Recherche de mobs...")
        
        # Détecter les mobs
        mobs = self.vision.detect_mobs()
        
        if mobs:
            # Cliquer sur le premier mob trouvé
            name, x, y, conf = mobs[0]
            self.log(f"👹 Mob détecté: {name} ({conf:.0%})")
            
            # Option: envoyer .movemobs d'abord
            if self.config.get("use_movemobs", False):
                self.controller.type_chat(".movemobs")
                time.sleep(0.5)
            
            # Cliquer sur le mob pour engager
            self.controller.click(x, y)
            
            # Attendre le chargement du combat
            time.sleep(self.config.get("combat_delay", 2.0))
        else:
            # Pas de mob, attendre ou changer de map
            time.sleep(self.config.get("search_delay", 1.5))
    
    def handle_combat(self):
        """Gère un combat"""
        self.log("⚔️ Combat détecté!")
        
        while self.vision.is_in_combat() and self.running:
            if self.paused:
                time.sleep(0.5)
                continue
            
            # Décider de l'action
            action_type, params = self.combat_ai.decide_action()
            
            if action_type == ActionType.SPELL:
                spell = params["spell"]
                target = params["target"]
                self.log(f"🎯 {spell.name} sur {target.name}")
                
                # Convertir position grille en pixels (à adapter)
                # Pour l'instant on utilise les coordonnées détectées
                self.controller.cast_spell(spell, target.position.x, target.position.y)
                
            elif action_type == ActionType.MOVE:
                pos = params["position"]
                self.log(f"🚶 Déplacement vers ({pos.x}, {pos.y})")
                # Convertir position grille en pixels
                self.controller.move_to(pos.x * 50 + 400, pos.y * 50 + 300)  # Exemple
                
            elif action_type == ActionType.PASS_TURN:
                self.log("⏭️ Passe le tour")
                self.controller.pass_turn()
                self.combat_ai.end_turn()
            
            time.sleep(0.5)
        
        # Combat terminé
        self.stats["combats_won"] += 1
        self.log(f"✅ Combat terminé! Total: {self.stats['combats_won']}")
    
    def start(self):
        """Démarre l'agent dans un thread"""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def pause(self):
        """Pause/reprend l'agent"""
        self.paused = not self.paused
        self.log("⏸️ Pause" if self.paused else "▶️ Reprise")
    
    def stop(self):
        """Arrête l'agent"""
        self.running = False


# ============================================================
#                    INTERFACE GRAPHIQUE
# ============================================================

class AgentGUI:
    """Interface graphique pour l'agent"""
    
    def __init__(self):
        self.colors = {
            'bg': '#0f0f1a',
            'bg2': '#1a1a2e',
            'bg3': '#16213e',
            'accent': '#e94560',
            'success': '#00d26a',
            'warning': '#ff9f1c',
            'info': '#4cc9f0',
            'text': '#ffffff',
            'text2': '#8b8b9e'
        }
        
        # Dossier de config
        try:
            self.config_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            self.config_dir = os.getcwd()
        
        # Agent
        self.agent = AutonomousAgent(self.config_dir)
        self.agent.set_callback(self.agent_callback)
        
        self.setup_window()
        self.create_widgets()
    
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("🤖 Dofus Autonomous Agent v1.0")
        self.root.geometry("900x700")
        self.root.configure(bg=self.colors['bg'])
    
    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.colors['bg2'], height=80)
        header.pack(fill='x', padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="🤖 Dofus Autonomous Agent", font=('Segoe UI', 18, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['accent']).pack(side='left', padx=20, pady=15)
        
        self.status_label = tk.Label(header, text="⚪ Arrêté", font=('Segoe UI', 11),
                                     bg=self.colors['bg2'], fg=self.colors['text2'])
        self.status_label.pack(side='left', padx=20)
        
        # Boutons
        btn_frame = tk.Frame(header, bg=self.colors['bg2'])
        btn_frame.pack(side='right', padx=20)
        
        self.start_btn = tk.Button(btn_frame, text="▶️ DÉMARRER", font=('Segoe UI', 10, 'bold'),
                                   bg=self.colors['success'], fg='white', width=12,
                                   command=self.start_agent)
        self.start_btn.pack(side='left', padx=5)
        
        self.pause_btn = tk.Button(btn_frame, text="⏸️ PAUSE", font=('Segoe UI', 10),
                                   bg=self.colors['warning'], fg='black', width=10,
                                   command=self.pause_agent, state='disabled')
        self.pause_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹️ STOP", font=('Segoe UI', 10),
                                  bg=self.colors['accent'], fg='white', width=8,
                                  command=self.stop_agent, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        # Main content
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel - Configuration
        left = tk.Frame(main, bg=self.colors['bg2'], width=350)
        left.pack(side='left', fill='y', padx=(0,5), pady=5)
        left.pack_propagate(False)
        
        self.create_config_panel(left)
        
        # Right panel - Log
        right = tk.Frame(main, bg=self.colors['bg2'])
        right.pack(side='right', fill='both', expand=True, pady=5)
        
        self.create_log_panel(right)
    
    def create_config_panel(self, parent):
        """Crée le panneau de configuration"""
        tk.Label(parent, text="⚙️ Configuration", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=10)
        
        # Stratégie
        frame = tk.Frame(parent, bg=self.colors['bg2'], padx=15)
        frame.pack(fill='x', pady=5)
        
        tk.Label(frame, text="🎯 Stratégie:", font=('Segoe UI', 10),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(anchor='w')
        
        self.strategy_var = tk.StringVar(value=self.agent.config.get("strategy", "balanced"))
        for strat, label in [("aggressive", "⚔️ Aggressive"), 
                            ("balanced", "⚖️ Équilibrée"),
                            ("defensive", "🛡️ Défensive")]:
            tk.Radiobutton(frame, text=label, variable=self.strategy_var, value=strat,
                          bg=self.colors['bg2'], fg=self.colors['text'],
                          selectcolor=self.colors['bg3'],
                          activebackground=self.colors['bg2']).pack(anchor='w')
        
        # Sorts
        tk.Frame(parent, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(parent, text="🔮 Sorts", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        tk.Button(parent, text="⚙️ Configurer les sorts", font=('Segoe UI', 10),
                 bg=self.colors['info'], fg='white',
                 command=self.open_spells_config).pack(pady=5)
        
        # Mobs
        tk.Frame(parent, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(parent, text="👾 Mobs", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        self.mob_count_label = tk.Label(parent, text=f"📸 {len(self.agent.vision.mob_templates)} template(s)",
                                        font=('Segoe UI', 10),
                                        bg=self.colors['bg2'], fg=self.colors['success'])
        self.mob_count_label.pack()
        
        tk.Button(parent, text="📸 Capturer mob", font=('Segoe UI', 10),
                 bg=self.colors['accent'], fg='white',
                 command=self.capture_mob).pack(pady=5)
        
        # Démonstration
        tk.Frame(parent, bg=self.colors['bg3'], height=2).pack(fill='x', padx=10, pady=10)
        
        tk.Label(parent, text="🎓 Apprentissage", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        self.record_btn = tk.Button(parent, text="🔴 Enregistrer combat", font=('Segoe UI', 10),
                                    bg='#ff0000', fg='white',
                                    command=self.toggle_recording)
        self.record_btn.pack(pady=5)
        
        self.patterns_label = tk.Label(parent, 
                                       text=f"📚 {len(self.agent.combat_ai.learned_patterns)} pattern(s) appris",
                                       font=('Segoe UI', 10),
                                       bg=self.colors['bg2'], fg=self.colors['info'])
        self.patterns_label.pack()
    
    def create_log_panel(self, parent):
        """Crée le panneau de log"""
        # Stats
        stats_frame = tk.Frame(parent, bg=self.colors['bg3'], height=80)
        stats_frame.pack(fill='x', padx=10, pady=10)
        stats_frame.pack_propagate(False)
        
        stats_inner = tk.Frame(stats_frame, bg=self.colors['bg3'])
        stats_inner.pack(expand=True)
        
        tk.Label(stats_inner, text="⚔️ Combats", font=('Segoe UI', 10),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(side='left', padx=20)
        self.combats_label = tk.Label(stats_inner, text="0", font=('Segoe UI', 24, 'bold'),
                                      bg=self.colors['bg3'], fg=self.colors['success'])
        self.combats_label.pack(side='left', padx=10)
        
        tk.Label(stats_inner, text="⏱️ Temps", font=('Segoe UI', 10),
                bg=self.colors['bg3'], fg=self.colors['text2']).pack(side='left', padx=20)
        self.time_label = tk.Label(stats_inner, text="00:00:00", font=('Segoe UI', 24, 'bold'),
                                   bg=self.colors['bg3'], fg=self.colors['warning'])
        self.time_label.pack(side='left', padx=10)
        
        # Log
        tk.Label(parent, text="📝 Journal", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg2'], fg=self.colors['text']).pack(pady=5)
        
        self.log_text = tk.Text(parent, bg=self.colors['bg'], fg=self.colors['text'],
                                font=('Consolas', 10), height=20, wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=5)
    
    def agent_callback(self, event: str, data: Any):
        """Callback de l'agent"""
        if event == "log":
            self.root.after(0, lambda: self.log(data))
        elif event == "combat":
            self.root.after(0, lambda: self.combats_label.config(text=str(data)))
    
    def log(self, msg: str):
        """Ajoute un message au log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
    
    def start_agent(self):
        """Démarre l'agent"""
        self.agent.combat_ai.set_strategy(self.strategy_var.get())
        self.agent.start()
        
        self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
        self.start_btn.config(state='disabled')
        self.pause_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        
        self.update_time()
    
    def pause_agent(self):
        """Pause l'agent"""
        self.agent.pause()
        if self.agent.paused:
            self.status_label.config(text="⏸️ Pause", fg=self.colors['warning'])
            self.pause_btn.config(text="▶️ REPRENDRE")
        else:
            self.status_label.config(text="🟢 En cours", fg=self.colors['success'])
            self.pause_btn.config(text="⏸️ PAUSE")
    
    def stop_agent(self):
        """Arrête l'agent"""
        self.agent.stop()
        
        self.status_label.config(text="⚪ Arrêté", fg=self.colors['text2'])
        self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️ PAUSE")
        self.stop_btn.config(state='disabled')
    
    def toggle_recording(self):
        """Active/désactive l'enregistrement"""
        if self.agent.is_recording:
            self.agent.stop_recording()
            self.record_btn.config(text="🔴 Enregistrer combat", bg='#ff0000')
            self.patterns_label.config(text=f"📚 {len(self.agent.combat_ai.learned_patterns)} pattern(s) appris")
        else:
            self.agent.start_recording()
            self.record_btn.config(text="⏹️ Arrêter", bg=self.colors['warning'])
    
    def capture_mob(self):
        """Capture un template de mob"""
        self.log("📸 Place ta souris sur le mob dans 3 secondes...")
        self.root.after(3000, self._do_capture_mob)
    
    def _do_capture_mob(self):
        """Effectue la capture du mob"""
        x, y = pyautogui.position()
        screenshot = ImageGrab.grab()
        screen = np.array(screenshot)
        
        # Capturer une zone 50x50 autour du curseur
        size = 50
        x1, y1 = max(0, x - size//2), max(0, y - size//2)
        x2, y2 = x1 + size, y1 + size
        
        template = screen[y1:y2, x1:x2]
        
        if template.size > 0:
            mob_dir = os.path.join(self.config_dir, "mobs")
            os.makedirs(mob_dir, exist_ok=True)
            
            filename = f"mob_{datetime.now().strftime('%H%M%S')}.png"
            filepath = os.path.join(mob_dir, filename)
            
            cv2.imwrite(filepath, cv2.cvtColor(template, cv2.COLOR_RGB2BGR))
            
            self.agent.vision.load_templates()
            self.mob_count_label.config(text=f"📸 {len(self.agent.vision.mob_templates)} template(s)")
            self.log(f"✅ Mob capturé: {filename}")
    
    def open_spells_config(self):
        """Ouvre la configuration des sorts"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🔮 Configuration des sorts")
        dialog.geometry("600x500")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="🔮 Sorts configurés", font=('Segoe UI', 14, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack(pady=10)
        
        # Liste des sorts
        list_frame = tk.Frame(dialog, bg=self.colors['bg2'], padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        for spell in self.agent.combat_ai.spells.values():
            row = tk.Frame(list_frame, bg=self.colors['bg3'], padx=10, pady=5)
            row.pack(fill='x', pady=2)
            
            tk.Label(row, text=f"[{spell.key}] {spell.name}", font=('Segoe UI', 10, 'bold'),
                    bg=self.colors['bg3'], fg=self.colors['text']).pack(side='left')
            
            tk.Label(row, text=f"PA: {spell.cost_pa} | Range: {spell.min_range}-{spell.max_range} | Prio: {spell.priority}",
                    font=('Segoe UI', 9),
                    bg=self.colors['bg3'], fg=self.colors['text2']).pack(side='right')
        
        tk.Button(dialog, text="➕ Ajouter sort", font=('Segoe UI', 10),
                 bg=self.colors['success'], fg='white',
                 command=lambda: self.add_spell_dialog(dialog)).pack(pady=10)
    
    def add_spell_dialog(self, parent):
        """Dialog pour ajouter un sort"""
        dialog = tk.Toplevel(parent)
        dialog.title("➕ Nouveau sort")
        dialog.geometry("400x400")
        dialog.configure(bg=self.colors['bg'])
        
        entries = {}
        
        for label, key, default in [
            ("Nom:", "name", "Sort"),
            ("Touche:", "key", "1"),
            ("PA:", "cost_pa", "3"),
            ("Portée min:", "min_range", "1"),
            ("Portée max:", "max_range", "6"),
            ("Cooldown:", "cooldown", "0"),
            ("Dégâts:", "damage", "30"),
            ("Priorité (1-10):", "priority", "5")
        ]:
            row = tk.Frame(dialog, bg=self.colors['bg'])
            row.pack(fill='x', padx=20, pady=3)
            tk.Label(row, text=label, width=15, anchor='w',
                    bg=self.colors['bg'], fg=self.colors['text']).pack(side='left')
            entry = tk.Entry(row, width=15, bg=self.colors['bg2'], fg=self.colors['text'])
            entry.insert(0, default)
            entry.pack(side='left')
            entries[key] = entry
        
        def save_spell():
            spell = Spell(
                id=len(self.agent.combat_ai.spells) + 1,
                name=entries["name"].get(),
                key=entries["key"].get(),
                cost_pa=int(entries["cost_pa"].get()),
                min_range=int(entries["min_range"].get()),
                max_range=int(entries["max_range"].get()),
                cooldown=int(entries["cooldown"].get()),
                damage=int(entries["damage"].get()),
                priority=int(entries["priority"].get())
            )
            self.agent.combat_ai.spells[spell.id] = spell
            self.agent.save_spells(list(self.agent.combat_ai.spells.values()))
            self.log(f"✅ Sort ajouté: {spell.name}")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Sauvegarder", font=('Segoe UI', 11, 'bold'),
                 bg=self.colors['success'], fg='white',
                 command=save_spell).pack(pady=20)
    
    def update_time(self):
        """Met à jour le temps"""
        if self.agent.running and self.agent.stats["start_time"]:
            elapsed = datetime.now() - self.agent.stats["start_time"]
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.combats_label.config(text=str(self.agent.stats["combats_won"]))
        
        self.root.after(1000, self.update_time)
    
    def run(self):
        self.root.mainloop()


# ============================================================
#                    MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Dofus Autonomous Agent v1.0")
    print("=" * 50)
    
    app = AgentGUI()
    app.run()