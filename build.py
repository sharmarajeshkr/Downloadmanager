import os
import sys
import subprocess
import shutil
from pathlib import Path

def ensure_pyinstaller():
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build():
    ensure_pyinstaller()
    
    project_dir = Path(__file__).parent.absolute()
    os.chdir(project_dir)
    
    # Define OS specific outputs
    if sys.platform == "win32":
        sep = ";"
        os_name = "Windows"
    else:
        sep = ":"
        os_name = "macOS/Linux"
        
    print(f"--- Starting Build for {os_name} ---")

    # PyInstaller Arguments
    args = [
        "pyinstaller",
        "--noconfirm",         # Overwrite output directory without asking
        "--onefile",           # Create a single executable
        "--windowed",          # Don't open a console window (GUI mode)
        "--name", "WITTGrp",   # Output filename
        
        # Include custom UI assets Folder
        f"--add-data=ui/assets{sep}ui/assets",
        
        # Include browser extensions folders (so users can extract them later if needed)
        f"--add-data=browser_extension/chrome{sep}browser_extension/chrome",
        f"--add-data=browser_extension/edge{sep}browser_extension/edge",
        f"--add-data=browser_extension/opera{sep}browser_extension/opera",
        
        # Explicit hidden imports to prevent runtime "ModuleNotFoundError"
        "--hidden-import=PyQt6",
        "--hidden-import=requests",
        "--hidden-import=sqlite3",
        
        # Specify the icon if available (Windows=ico, Mac=icns)
        # "--icon=ui/assets/icon.ico",  # Uncomment if an .ico file exists
        
        "main.py"
    ]
    
    print("Running command:", " ".join(args))
    subprocess.check_call([sys.executable, "-m", "PyInstaller"] + args[1:])
    
    print(f"\n[SUCCESS] Build complete! You can find the executable for {os_name} in the 'dist' folder.")

if __name__ == "__main__":
    build()
