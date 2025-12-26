@echo off
title 🎮 Installation Dofus Bot Hub
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║                                                       ║
echo  ║        🎮 DOFUS BOT HUB - INSTALLATION               ║
echo  ║                                                       ║
echo  ║        Installation automatique complete              ║
echo  ║                                                       ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.

:: ============================================
:: ETAPE 1: Verifier Python
:: ============================================
echo [1/3] Verification de Python...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo      [!] Python n'est pas installe!
    echo.
    echo      [*] Telechargement de Python 3.11...
    echo          Cela peut prendre quelques minutes...
    echo.
    
    curl -L -o python_installer.exe "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" 2>nul
    
    if not exist python_installer.exe (
        bitsadmin /transfer "Python" "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" "%CD%\python_installer.exe" >nul 2>&1
    )
    
    if exist python_installer.exe (
        echo      [*] Installation de Python...
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1
        del python_installer.exe 2>nul
        
        set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts"
        set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
        
        echo      [OK] Python installe!
        echo.
        echo      [!] Ferme cette fenetre et relance Installer.bat
        echo.
        pause
        exit
    ) else (
        echo      [ERREUR] Telecharge Python manuellement:
        echo      https://www.python.org/downloads/
        echo      IMPORTANT: Coche "Add Python to PATH" !
        echo.
        pause
        exit
    )
) else (
    echo      [OK] Python est installe!
    python --version
    echo.
)

:: ============================================
:: ETAPE 2: Mettre a jour pip
:: ============================================
echo [2/3] Mise a jour de pip...
python -m pip install --upgrade pip >nul 2>&1
echo      [OK] pip mis a jour!
echo.

:: ============================================
:: ETAPE 3: Installer les dependances Python
:: ============================================
echo [3/3] Installation des dependances...
echo.

echo      [*] opencv-python...
pip install opencv-python --quiet 2>nul
echo          [OK]

echo      [*] numpy...
pip install numpy --quiet 2>nul
echo          [OK]

echo      [*] pyautogui...
pip install pyautogui --quiet 2>nul
echo          [OK]

echo      [*] Pillow...
pip install Pillow --quiet 2>nul
echo          [OK]

echo      [*] keyboard...
pip install keyboard --quiet 2>nul
echo          [OK]

echo      [*] requests...
pip install requests --quiet 2>nul
echo          [OK]

echo      [*] pynput...
pip install pynput --quiet 2>nul
echo          [OK]

echo      [*] websockets...
pip install websockets --quiet 2>nul
echo          [OK]

echo      [*] mss (capture ecran rapide)...
pip install mss --quiet 2>nul
echo          [OK]

echo      [*] PyTurboJPEG (encodage rapide)...
pip install PyTurboJPEG --quiet 2>nul
echo          [OK] (optionnel)

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║                                                       ║
echo  ║        ✅ INSTALLATION TERMINEE !                    ║
echo  ║                                                       ║
echo  ║        Pour lancer le Hub:                           ║
echo  ║        → Double-clic sur "Lancer_Hub.vbs"            ║
echo  ║                                                       ║
echo  ║        📺 Partage d'ecran: ACTIVE                    ║
echo  ║                                                       ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.
pause
