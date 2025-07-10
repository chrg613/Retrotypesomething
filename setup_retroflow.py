#!/usr/bin/env python3
"""
RetroFlow Setup Script
Automatically sets up the RetroFlow gaming environment
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import json
from pathlib import Path

def create_directory_structure():
    """Create necessary directories for RetroFlow"""
    directories = [
        "Games",
        "Sounds", 
        "Emulators",
        "Cores",
        "Config",
        "Saves"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def download_sample_sounds():
    """Download sample retro sound effects"""
    sounds = {
        "startup.mp3": "https://example.com/startup.mp3",
        "menu_select.mp3": "https://example.com/menu.mp3", 
        "launch_game.mp3": "https://example.com/launch.mp3",
        "error.mp3": "https://example.com/error.mp3"
    }
    
    print("Downloading sample sounds...")
    for filename, url in sounds.items():
        try:
            # In a real implementation, you'd download actual sound files
            # For now, create placeholder files
            with open(f"Sounds/{filename}", "w") as f:
                f.write("# Placeholder sound file")
            print(f"✓ Created placeholder: {filename}")
        except Exception as e:
            print(f"✗ Failed to create {filename}: {e}")

def install_dependencies():
    """Install required Python packages"""
    packages = [
        "prompt-toolkit",
        "psutil", 
        "google-generativeai",
        "playsound"
    ]
    
    print("Installing Python dependencies...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ Installed: {package}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")

def create_sample_config():
    """Create sample configuration files"""
    config = {
        "version": "2.0",
        "max_storage_mb": 16,
        "auto_scan_cartridges": True,
        "sound_enabled": True,
        "ai_enabled": True,
        "theme": "retro_green"
    }
    
    with open("Config/retroflow.json", "w") as f:
        json.dump(config, f, indent=2)
    print("✓ Created configuration file")

def main():
    """Main setup function"""
    print("🎮 RetroFlow Setup Script 🎮")
    print("=" * 40)
    
    create_directory_structure()
    download_sample_sounds()
    install_dependencies()
    create_sample_config()
    
    print("\n" + "=" * 40)
    print("✅ RetroFlow setup complete!")
    print("\nNext steps:")
    print("1. Add your ROM files to the 'Games' directory")
    print("2. Set your GOOGLE_API_KEY environment variable for AI features")
    print("3. Install RetroArch or other emulators")
    print("4. Run: python retroflow_enhanced.py")
    print("\nHave fun gaming! 🕹️")

if __name__ == "__main__":
    main()
