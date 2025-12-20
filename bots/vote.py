#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Python pour lire et recopier du texte à une position calibrée manuellement
"""

import pyautogui
import time
import sys

class TextCopyBot:
    def __init__(self):
        self.target_position = None
        # Sécurité pyautogui: déplacer la souris dans un coin arrête le script
        pyautogui.FAILSAFE = True
        
    def calibrer_position(self):
        """
        Permet à l'utilisateur de calibrer la position où le texte sera copié.
        L'utilisateur a 5 secondes pour placer la souris à l'endroit souhaité.
        """
        print("\n" + "="*60)
        print("CALIBRATION DE LA POSITION")
        print("="*60)
        print("Placez votre souris à l'endroit où vous voulez que le texte")
        print("soit copié (par exemple, dans un champ de texte).")
        print("\nVous avez 5 secondes...")
        
        for i in range(5, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            time.sleep(1)
        
        self.target_position = pyautogui.position()
        print(f"\n\n✓ Position enregistrée: X={self.target_position.x}, Y={self.target_position.y}")
        print("="*60 + "\n")
        
    def lire_texte_fichier(self, chemin_fichier):
        """
        Lit le texte depuis un fichier.
        """
        try:
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                texte = f.read()
            print(f"✓ Texte lu depuis '{chemin_fichier}'")
            print(f"  Longueur: {len(texte)} caractères\n")
            return texte
        except FileNotFoundError:
            print(f"❌ Erreur: Le fichier '{chemin_fichier}' n'existe pas.")
            return None
        except Exception as e:
            print(f"❌ Erreur lors de la lecture: {e}")
            return None
    
    def copier_texte(self, texte, delai=3, vitesse=0.05):
        """
        Copie le texte à la position calibrée.
        
        Args:
            texte: Le texte à copier
            delai: Délai avant de commencer (secondes)
            vitesse: Intervalle entre chaque caractère (secondes)
        """
        if not self.target_position:
            print("❌ Erreur: Position non calibrée. Utilisez calibrer_position() d'abord.")
            return
        
        print(f"Le texte sera copié dans {delai} secondes...")
        print("Préparez la fenêtre cible!\n")
        
        time.sleep(delai)
        
        # Cliquer à la position calibrée
        pyautogui.click(self.target_position.x, self.target_position.y)
        time.sleep(0.5)
        
        # Taper le texte
        print("⌨️  Copie en cours...")
        pyautogui.write(texte, interval=vitesse)
        
        print("✓ Texte copié avec succès!\n")
    
    def mode_interactif(self):
        """
        Mode interactif pour utiliser le bot.
        """
        print("\n" + "="*60)
        print("BOT DE COPIE DE TEXTE")
        print("="*60)
        print("\nOptions:")
        print("1. Calibrer la position")
        print("2. Entrer du texte manuellement")
        print("3. Lire depuis un fichier")
        print("4. Quitter")
        print("="*60)
        
        while True:
            choix = input("\nVotre choix (1-4): ").strip()
            
            if choix == "1":
                self.calibrer_position()
                
            elif choix == "2":
                if not self.target_position:
                    print("⚠️  Calibrez d'abord la position (option 1)")
                    continue
                    
                print("\nEntrez votre texte (tapez 'FIN' sur une nouvelle ligne pour terminer):")
                lignes = []
                while True:
                    ligne = input()
                    if ligne == "FIN":
                        break
                    lignes.append(ligne)
                
                texte = "\n".join(lignes)
                if texte:
                    self.copier_texte(texte)
                    
            elif choix == "3":
                if not self.target_position:
                    print("⚠️  Calibrez d'abord la position (option 1)")
                    continue
                    
                chemin = input("\nChemin du fichier: ").strip()
                texte = self.lire_texte_fichier(chemin)
                if texte:
                    self.copier_texte(texte)
                    
            elif choix == "4":
                print("\n👋 Au revoir!")
                break
                
            else:
                print("❌ Choix invalide. Choisissez 1, 2, 3 ou 4.")


def main():
    """
    Point d'entrée principal du script.
    """
    bot = TextCopyBot()
    
    # Si un argument est fourni, l'utiliser comme fichier à lire
    if len(sys.argv) > 1:
        print("Mode fichier direct\n")
        bot.calibrer_position()
        texte = bot.lire_texte_fichier(sys.argv[1])
        if texte:
            bot.copier_texte(texte)
    else:
        # Sinon, mode interactif
        bot.mode_interactif()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Arrêt du programme (Ctrl+C)")
        sys.exit(0)