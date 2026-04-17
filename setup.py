"""
Setup script for building QR Code Steganography Generator as .exe
Using cx_Freeze - alternative to PyInstaller
"""

import sys
from pathlib import Path
from cx_Freeze import setup, Executable

# Get PyQt6 plugins path
try:
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication([])
    qt_plugins_path = str(Path(app.pluginsPath()))
except ImportError:
    qt_plugins_path = None

# Build options
build_options = {
    "packages": [
        "qrcode",
        "PIL",
        "numpy",
        "PyQt6",
    ],
    "excludes": [
        "tkinter",
        "unittest",
    ],
    "optimize": 2,  # Optimize bytecode
}

# Include Qt plugins if found
if qt_plugins_path:
    build_options["include_files"] = [
        (f"{qt_plugins_path}/platforms", "PyQt6/plugins/platforms"),
        (f"{qt_plugins_path}/imageformats", "PyQt6/plugins/imageformats"),
    ]

# Define the executable
executables = [Executable(
    "qr_steganography_fixed.py",
    target_name="QRCodeSteganography.exe",
    base="Win32GUI",  # Use Win32GUI for no console window (Windows only)
    icon=None,         # Add path to .ico file if you have one
)]

setup(
    name="QR Code Steganography Generator",
    version="1.0.0",
    description="Creates QR codes hidden within images",
    author="Your Name",
    executables=executables,
    options={"build_exe": build_options}
)
