#!/usr/bin/env python3
"""
RetroFlow Game Organizer
Automatically organizes ROM files by system and creates metadata
"""

import os
import shutil
import json
from pathlib import Path

# System mappings based on file extensions
SYSTEM_MAPPINGS = {
    '.nes': 'Nintendo/NES',
    '.smc': 'Nintendo/SNES', 
    '.sfc': 'Nintendo/SNES',
    '.gb': 'Nintendo/GameBoy',
    '.gbc': 'Nintendo/GameBoy',
    '.gba': 'Nintendo/GameBoy',
    '.md': 'Sega/Genesis',
    '.gen': 'Sega/Genesis',
    '.sms': 'Sega/MasterSystem',
    '.gg': 'Sega/GameGear',
    '.pce': 'NEC/PCEngine',
    '.ngp': 'SNK/NeoGeoPocket',
    '.ws': 'Bandai/WonderSwan',
    '.exe': 'PC/DOS',
    '.com': 'PC/DOS',
    '.bat': 'PC/DOS'
}

def organize_games(source_dir="Games", organized_dir="Games_Organized"):
    """Organize games by system"""
    print(f"Organizing games from {source_dir} to {organized_dir}")
    
    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} not found!")
        return
    
    os.makedirs(organized_dir, exist_ok=True)
    
    for filename in os.listdir(source_dir):
        if os.path.isfile(os.path.join(source_dir, filename)):
            ext = Path(filename).suffix.lower()
            
            if ext in SYSTEM_MAPPINGS:
                system_dir = os.path.join(organized_dir, SYSTEM_MAPPINGS[ext])
                os.makedirs(system_dir, exist_ok=True)
                
                source_path = os.path.join(source_dir, filename)
                dest_path = os.path.join(system_dir, filename)
                
                try:
                    shutil.copy2(source_path, dest_path)
                    print(f"✓ Moved {filename} to {SYSTEM_MAPPINGS[ext]}")
                    
                    # Create metadata
                    create_game_metadata(dest_path)
                    
                except Exception as e:
                    print(f"✗ Failed to move {filename}: {e}")

def create_game_metadata(game_path):
    """Create metadata file for a game"""
    filename = os.path.basename(game_path)
    name_without_ext = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    
    # Clean up name
    clean_name = name_without_ext.replace('_', ' ').replace('-', ' ')
    clean_name = ' '.join(word.capitalize() for word in clean_name.split())
    
    # Remove common ROM tags
    rom_tags = ['(USA)', '(Europe)', '(Japan)', '(World)', '[!]', '(Rev A)', '(Rev B)']
    for tag in rom_tags:
        clean_name = clean_name.replace(tag, '').strip()
    
    metadata = {
        "game_name": clean_name,
        "filename": filename,
        "system": SYSTEM_MAPPINGS.get(ext, "Unknown"),
        "file_size": os.path.getsize(game_path),
        "auto_generated": True,
        "created_date": "2024-01-01"
    }
    
    metadata_path = os.path.splitext(game_path)[0] + "_metadata.json"
    
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ Created metadata for {clean_name}")
    except Exception as e:
        print(f"  ✗ Failed to create metadata: {e}")

def main():
    """Main organizer function"""
    print("🗂️  RetroFlow Game Organizer 🗂️")
    print("=" * 40)
    
    organize_games()
    
    print("\n" + "=" * 40)
    print("✅ Game organization complete!")
    print("Games have been sorted by system in Games_Organized/")

if __name__ == "__main__":
    main()
