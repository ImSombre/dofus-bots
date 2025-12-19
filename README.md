# 🎮 Dofus Bot Hub v1.0

Hub central pour tous les bots Dofus avec **mise à jour automatique** !

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)

---

## ✨ Fonctionnalités

- ✅ **Hub central** - Lance tous tes bots depuis une seule interface
- ✅ **Installation automatique** - Python + dépendances installés automatiquement
- ✅ **Mise à jour automatique** - Via GitHub, tous les utilisateurs sont mis à jour
- ✅ **Interface moderne** - Design propre et professionnel
- ✅ **Sans CMD** - Pas de fenêtre console visible

---

## 📦 Bots inclus

### 🌾 Farming Bot v6.0
- Récolte automatique de ressources
- Détection de MP + Discord
- Gestion des combats automatique
- Fermeture des popups

### 🗡️ Combat Bot v2.0
- Farm de mobs automatique
- Système Record & Replay
- Clic droit pour attaquer
- Détection MP + Discord

---

## 🚀 Installation (Utilisateurs)

### C'est tout automatique !

1. **Extraire** le dossier `DofusHub`
2. **Double-clic** sur `Installer.bat`
   - ☕ Attendre (installe Python si besoin)
   - ✅ Installe toutes les dépendances
3. **Double-clic** sur `Lancer_Hub.vbs`
4. **Terminé !** 🎉

---

## 📁 Structure des fichiers

```
DofusHub/
├── hub.py                    # Interface du Hub
├── version.json              # Version actuelle
├── Installer.bat             # Installation automatique
├── Lancer_Hub.vbs            # Lancer le Hub (sans CMD)
├── requirements.txt          # Dépendances Python
├── README.md                 # Ce fichier
└── bots/
    ├── farming/
    │   ├── bot.py            # Farming Bot
    │   └── resources/        # Templates ressources
    └── combat/
        ├── bot_combat.py     # Combat Bot
        └── mobs/             # Templates mobs
```

---

## 🔄 Mise à jour automatique (Pour les développeurs)

### Comment ça marche ?

1. Tu crées un repo GitHub public
2. Tu mets les fichiers du Hub sur GitHub
3. Quand tu fais une modification, tu mets à jour `version.json`
4. Les utilisateurs reçoivent la mise à jour automatiquement au démarrage !

### Configurer GitHub

#### 1. Créer un repo GitHub

1. Va sur [github.com](https://github.com) et connecte-toi
2. Clique sur **"New repository"**
3. Nom : `dofus-bots` (ou ce que tu veux)
4. **Public** (important !)
5. Clique sur **"Create repository"**

#### 2. Upload les fichiers

Tu peux utiliser GitHub Desktop ou le site web :

**Via le site :**
1. Va sur ton repo
2. Clique sur **"Add file"** → **"Upload files"**
3. Glisse tous les fichiers du dossier DofusHub
4. Clique sur **"Commit changes"**

#### 3. Configurer le Hub

Dans `hub.py`, modifie ces lignes (vers le début du fichier) :

```python
# 🔧 CONFIGURE TON GITHUB ICI
GITHUB_USER = "ton-username"    # Ton nom d'utilisateur GitHub
GITHUB_REPO = "dofus-bots"       # Nom de ton repo
GITHUB_BRANCH = "main"           # Branche (main ou master)
```

#### 4. Publier une mise à jour

1. Modifie les fichiers que tu veux (bot.py, hub.py, etc.)

2. Mets à jour `version.json` :
```json
{
    "version": "1.1.0",
    "changelog": "Correction du bug de popup",
    "files": [
        {"path": "hub.py"},
        {"path": "bots/farming/bot.py"},
        {"path": "bots/combat/bot_combat.py"}
    ]
}
```

3. Upload les fichiers modifiés sur GitHub

4. **C'est tout !** Les utilisateurs recevront la mise à jour au prochain démarrage du Hub

---

## 📋 Format de version.json

```json
{
    "version": "1.2.0",
    "changelog": "Description des changements",
    "files": [
        {"path": "chemin/vers/fichier1.py"},
        {"path": "chemin/vers/fichier2.py"}
    ]
}
```

| Champ | Description |
|-------|-------------|
| `version` | Numéro de version (ex: 1.0.0, 1.1.0, 2.0.0) |
| `changelog` | Description des changements (affiché à l'utilisateur) |
| `files` | Liste des fichiers à télécharger lors de la mise à jour |

---

## 🛠️ Ajouter un nouveau bot

1. Crée un dossier dans `bots/` : `bots/monbot/`
2. Mets ton script dedans : `bots/monbot/bot.py`
3. Modifie `hub.py` pour ajouter le bot dans la liste `BOTS` :

```python
BOTS = [
    # ... bots existants ...
    {
        "id": "monbot",
        "name": "🤖 Mon Nouveau Bot",
        "description": "Description de mon bot",
        "version": "1.0",
        "script": "bots/monbot/bot.py",
        "color": "#00ff00",
        "icon": "🤖"
    }
]
```

4. Mets à jour `version.json` et publie sur GitHub !

---

## ⚠️ Notes importantes

### Pour les utilisateurs
- **Première fois ?** Lance `Installer.bat` d'abord
- **Pas de CMD** - Utilise `Lancer_Hub.vbs`
- **Mise à jour** - Le Hub vérifie automatiquement au démarrage

### Pour le développeur
- **Repo public** - Obligatoire pour que les mises à jour fonctionnent
- **version.json** - Toujours mettre à jour ce fichier !
- **Tester** - Vérifie que les fichiers sont accessibles sur GitHub

---

## 🔧 Dépannage

### "Python n'est pas reconnu"
→ Relance `Installer.bat` après avoir fermé toutes les fenêtres CMD

### "Le Hub ne se lance pas"
→ Vérifie que Python est installé : `python --version`
→ Relance `Installer.bat`

### "Les mises à jour ne fonctionnent pas"
→ Vérifie que le repo GitHub est **public**
→ Vérifie les URL dans les paramètres du Hub
→ Vérifie que `version.json` est correct sur GitHub

### "Un bot ne se lance pas"
→ Vérifie que le fichier existe dans `bots/xxxx/`
→ Lance le bot directement avec Python pour voir l'erreur

---

## 📝 Changelog

### v1.0.0
- 🎉 Version initiale
- ✨ Hub central
- ✨ Farming Bot v6.0
- ✨ Combat Bot v2.0
- ✨ Système de mise à jour automatique

---

## 📜 Licence

Projet éducatif - Utilisation à vos risques.

---

**Bon farm ! 🎮**
