#!/usr/bin/env python3
"""
RetroFlow Emulator Setup Script
Downloads and sets up popular emulators automatically
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import json
import platform
from pathlib import Path

def create_emulator_structure():
    """Create emulator directory structure"""
    directories = [
        "Emulators",
        "Emulators/RetroArch",
        "Emulators/Standalone",
        "Cores",
        "Config/Emulators"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_emulator_configs():
    """Create configuration files for emulators"""
    
    # RetroArch configuration
    retroarch_config = {
        "name": "RetroArch",
        "executable": "retroarch.exe" if platform.system() == "Windows" else "retroarch",
        "cores_directory": "Cores",
        "supported_systems": [
            "Nintendo Entertainment System",
            "Super Nintendo",
            "Game Boy",
            "Game Boy Color", 
            "Game Boy Advance",
            "Sega Genesis",
            "Sega Master System"
        ]
    }
    
    with open("Config/Emulators/retroarch.json", "w") as f:
        json.dump(retroarch_config, f, indent=2)
    
    # Standalone emulator configs
    standalone_configs = {
        "fceux": {
            "name": "FCEUX",
            "executable": "fceux.exe",
            "systems": ["Nintendo Entertainment System"],
            "extensions": [".nes"]
        },
        "snes9x": {
            "name": "Snes9x", 
            "executable": "snes9x.exe",
            "systems": ["Super Nintendo"],
            "extensions": [".smc", ".sfc"]
        },
        "visualboyadvance": {
            "name": "VisualBoyAdvance",
            "executable": "VisualBoyAdvance.exe",
            "systems": ["Game Boy", "Game Boy Color", "Game Boy Advance"],
            "extensions": [".gb", ".gbc", ".gba"]
        },
        "gens": {
            "name": "Gens",
            "executable": "gens.exe", 
            "systems": ["Sega Genesis"],
            "extensions": [".md", ".gen"]
        },
        "dosbox": {
            "name": "DOSBox",
            "executable": "dosbox.exe",
            "systems": ["MS-DOS"],
            "extensions": [".exe", ".com", ".bat"]
        }
    }
    
    for emu_name, config in standalone_configs.items():
        with open(f"Config/Emulators/{emu_name}.json", "w") as f:
            json.dump(config, f, indent=2)
    
    print("✓ Created emulator configuration files")

def create_sample_emulator_batch_files():
    """Create sample batch files for emulator launching"""
    
    # Windows batch files
    if platform.system() == "Windows":
        batch_files = {
            "launch_retroarch.bat": '''@echo off
echo Launching RetroArch...
cd /d "Emulators\\RetroArch"
if exist "retroarch.exe" (
    retroarch.exe %1
) else (
    echo RetroArch not found! Please install RetroArch in Emulators\\RetroArch\\
    pause
)
''',
            "launch_fceux.bat": '''@echo off
echo Launching FCEUX...
cd /d "Emulators\\Standalone"
if exist "fceux.exe" (
    fceux.exe %1
) else (
    echo FCEUX not found! Please install FCEUX in Emulators\\Standalone\\
    pause
)
''',
            "launch_snes9x.bat": '''@echo off
echo Launching Snes9x...
cd /d "Emulators\\Standalone"
if exist "snes9x.exe" (
    snes9x.exe %1
) else (
    echo Snes9x not found! Please install Snes9x in Emulators\\Standalone\\
    pause
)
'''
        }
        
        for filename, content in batch_files.items():
            with open(f"Emulators/{filename}", "w") as f:
                f.write(content)
            print(f"✓ Created batch file: {filename}")

def create_emulator_readme():
    """Create README file with emulator installation instructions"""
    
    readme_content = """# RetroFlow Emulator Setup Guide

## Directory Structure

(Provide your directory structure and instructions here.)

"""
