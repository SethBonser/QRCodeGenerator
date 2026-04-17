"""
Build script to create standalone .exe for QR Code Steganography Generator
Uses PyInstaller with proper Qt plugin handling.
"""

import os
import sys
import shutil
from pathlib import Path

def get_qt_plugins():
    """
    Find PyQt6 plugin directories.
    Returns list of plugin paths to include.
    """
    from PyQt6.QtCore import QCoreApplication
    
    app = QCoreApplication(sys.argv)
    plugin_paths = []
    
    # Get Qt plugins directory
    qt_plugins_dir = app.pluginsPath()
    print(f"Qt Plugins Directory: {qt_plugins_dir}")
    
    if os.path.exists(qt_plugins_dir):
        plugin_types = [
            'platforms',      # Essential for GUI
            'imageformats',   # For image loading/saving
            'styles',         # For styling
            'iconthemes',     # For icons
            'platformthemes', # Platform-specific themes
            'sqldrivers',     # Database drivers (optional)
        ]
        
        for plugin_type in plugin_types:
            plugin_path = os.path.join(qt_plugins_dir, plugin_type)
            if os.path.exists(plugin_path):
                plugin_paths.append(f"{plugin_path};{plugin_type}")
                print(f"  Found: {plugin_type} plugins")
    
    return plugin_paths

def build_exe():
    """
    Build the standalone executable using PyInstaller.
    """
    import subprocess
    
    # Source file to package
    source_file = "qr_steganography_fixed.py"
    
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found!")
        return False
    
    # Get Qt plugin paths for --collect-data
    qt_plugins = get_qt_plugins()
    
    # Build PyInstaller command arguments
    pyinstaller_args = [
        sys.executable,
        "-m", "PyInstaller",
        source_file,
        "--name", "QRCodeSteganography",
        "--onefile",           # Single .exe file (or use --onedir for folder)
        "--windowed",          # No console window
        "--icon=qr_icon.ico",  # Optional: add your icon
        "--add-data", f"README.md;.",
    ]
    
    # Add Qt plugin collections
    for plugin_spec in qt_plugins:
        pyinstaller_args.extend(["--collect-data", plugin_spec])
    
    # Additional hidden imports that PyQt6 may need
    extra_hidden = [
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "qrcode",
        "PIL",
        "numpy",
    ]
    
    for hidden_import in extra_hidden:
        pyinstaller_args.extend(["--hidden-import", hidden_import])
    
    print(f"\nRunning PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_args)}")
    print()
    
    # Run PyInstaller
    try:
        result = subprocess.run(
            pyinstaller_args,
            check=True,
            capture_output=False  # Show output in real-time
        )
        
        if result.returncode == 0:
            print("\n✅ Build successful!")
            print(f"Executable created: dist/QRCodeSteganography.exe")
            return True
        else:
            print(f"\n❌ Build failed with exit code {result.returncode}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ PyInstaller not found. Run: pip install pyinstaller")
        return False

def build_exe_onedir():
    """
    Build as a folder with all dependencies (more reliable, larger size).
    Better for complex apps with many plugins.
    """
    import subprocess
    
    source_file = "qr_steganography_fixed.py"
    
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found!")
        return False
    
    qt_plugins = get_qt_plugins()
    
    pyinstaller_args = [
        sys.executable,
        "-m", "PyInstaller",
        source_file,
        "--name", "QRCodeSteganography",
        "--onedir",            # Creates a folder with .exe and dependencies
        "--windowed",
    ]
    
    for plugin_spec in qt_plugins:
        pyinstaller_args.extend(["--collect-data", plugin_spec])
    
    print(f"\nRunning PyInstaller (--onedir mode)...")
    print(f"Command: {' '.join(pyinstaller_args)}")
    print()
    
    try:
        result = subprocess.run(
            pyinstaller_args,
            check=True,
            capture_output=False
        )
        
        if result.returncode == 0:
            print("\n✅ Build successful!")
            print(f"Executable folder: dist/QRCodeSteganography/")
            print(f"Run: dist/QRCodeSteganography/QRCodeSteganography.exe")
            return True
        else:
            print(f"\n❌ Build failed with exit code {result.returncode}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ PyInstaller not found. Run: pip install pyinstaller")
        return False

if __name__ == "__main__":
    print("="*60)
    print("QR Code Steganography Generator - Build Script")
    print("="*60)
    
    choice = input("\nBuild type [1=Single .exe, 2=Folder]: ").strip()
    
    if choice == "1":
        build_exe()
    elif choice == "2":
        build_exe_onedir()
    else:
        print("Invalid choice. Use 1 or 2.")
