import subprocess
import sys
import os
import json
import psutil
import time
import random
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text, HTML
import google.generativeai as genai
import google.generativeai.types as glm
from playsound import playsound, PlaysoundException
import html
from datetime import datetime
import platform
import glob
import threading
from pathlib import Path

# --- Enhanced Configuration with Dynamic Detection ---
GAMES_DIRECTORY = os.path.join(os.path.dirname(__file__), "Games")
EMULATORS_DIRECTORY = os.path.join(os.path.dirname(__file__), "Emulators")
CORES_DIRECTORY = os.path.join(os.path.dirname(__file__), "Cores")

# Enhanced emulator configuration with better Game Boy/GBA support
EMULATOR_CONFIGS = {
    '.nes': {
        'emulator_exe': 'fceux.exe',
        'emulator_name': 'FCEUX',
        'system': 'Nintendo Entertainment System',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'fceumm_libretro.dll'
    },
    '.smc': {
        'emulator_exe': 'snes9x.exe',
        'emulator_name': 'Snes9x',
        'system': 'Super Nintendo',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'snes9x_libretro.dll'
    },
    '.sfc': {
        'emulator_exe': 'snes9x.exe',
        'emulator_name': 'Snes9x',
        'system': 'Super Nintendo',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'snes9x_libretro.dll'
    },
    '.gb': {
        'emulator_exe': 'mgba.app',
        'emulator_name': 'mGBA',
        'system': 'Game Boy',
        'launch_template': 'open -a "{emulator_path}" "{game_path}"',
        'retroarch_core': 'gambatte_libretro.dll'
    },
    '.gbc': {
        'emulator_exe': 'mgba.app',
        'emulator_name': 'mGBA',
        'system': 'Game Boy Color',
        'launch_template': 'open -a "{emulator_path}" "{game_path}"',
        'retroarch_core': 'gambatte_libretro.dll'
    },
    '.gba': {
        'emulator_exe': 'mgba.app',
        'emulator_name': 'mGBA',
        'system': 'Game Boy Advance',
        'launch_template': 'open -a "{emulator_path}" "{game_path}"',
        'retroarch_core': 'mgba_libretro.dll'
    },
    '.md': {
        'emulator_exe': 'gens.exe',
        'emulator_name': 'Gens',
        'system': 'Sega Genesis',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'genesis_plus_gx_libretro.dll'
    },
    '.gen': {
        'emulator_exe': 'gens.exe',
        'emulator_name': 'Gens',
        'system': 'Sega Genesis',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'genesis_plus_gx_libretro.dll'
    },
    '.rom': {
        'emulator_exe': 'auto-detect',
        'emulator_name': 'Auto-Detect',
        'system': 'Unknown ROM',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'auto'
    },
    '.zip': {
        'emulator_exe': 'auto-detect',
        'emulator_name': 'Auto-Detect',
        'system': 'Compressed ROM',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'auto'
    },
    '.exe': {
        'emulator_exe': 'dosbox.exe',
        'emulator_name': 'DOSBox',
        'system': 'MS-DOS',
        'launch_template': '"{emulator_path}" "{game_path}" -exit',
        'retroarch_core': 'dosbox_libretro.dll'
    },
    '.com': {
        'emulator_exe': 'dosbox.exe',
        'emulator_name': 'DOSBox',
        'system': 'MS-DOS',
        'launch_template': '"{emulator_path}" "{game_path}" -exit',
        'retroarch_core': 'dosbox_libretro.dll'
    }
}

# Game-specific enhancements for better recognition
GAME_DATABASE = {
    'pokemon crystal': {
        'full_name': 'Pokémon Crystal Version',
        'series': 'Pokémon',
        'generation': 'Gen II',
        'system': 'Game Boy Color',
        'year': '2000'
    },
    'pokemon sapphire': {
        'full_name': 'Pokémon Sapphire Version',
        'series': 'Pokémon',
        'generation': 'Gen III',
        'system': 'Game Boy Advance',
        'year': '2002'
    },
    'pokemon ruby': {
        'full_name': 'Pokémon Ruby Version',
        'series': 'Pokémon',
        'generation': 'Gen III',
        'system': 'Game Boy Advance',
        'year': '2002'
    },
    'pokemon emerald': {
        'full_name': 'Pokémon Emerald Version',
        'series': 'Pokémon',
        'generation': 'Gen III',
        'system': 'Game Boy Advance',
        'year': '2004'
    },
    'zelda': {
        'full_name': 'The Legend of Zelda',
        'series': 'The Legend of Zelda',
        'system': 'Game Boy',
        'year': '1989'
    },
    'link\'s awakening': {
        'full_name': 'The Legend of Zelda: Link\'s Awakening',
        'series': 'The Legend of Zelda',
        'system': 'Game Boy',
        'year': '1993'
    }
}

MAX_STORAGE_MB = 256  # Maximum storage limit in MB
MAX_STORAGE_BYTES = MAX_STORAGE_MB * 1024 * 1024

# Global variables for dynamic detection
DETECTED_CARTRIDGES = []
CARTRIDGE_GAMES_MAP = {}
BOOT_TIME = datetime.now()
AVAILABLE_EMULATORS = {}
CURRENT_GAMES_LIST = []
CURRENT_GAME_MAP = {}
LAST_GAMES_SCAN = 0
LAST_EMULATORS_SCAN = 0
SCAN_INTERVAL = 2  # seconds

# File system monitoring
GAMES_LAST_MODIFIED = {}
EMULATORS_LAST_MODIFIED = {}

# Determine paths
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    SOUNDS_DIRECTORY = os.path.join(sys._MEIPASS, "Sounds")
else:
    SOUNDS_DIRECTORY = os.path.join(os.path.dirname(__file__), "Sounds")

SOUND_FILES = {
    "startup": os.path.join(SOUNDS_DIRECTORY, "retro-wave-style-track-59892.mp3"),
    "launch_game": os.path.join(SOUNDS_DIRECTORY, "retro-game-jingleaif-14638.mp3"),
    "error": os.path.join(SOUNDS_DIRECTORY, "retro-blip-2-236668.mp3"),
    "menu_select": os.path.join(SOUNDS_DIRECTORY, "retro-fart-104576.mp3"),
    "flowey_chat_enter": os.path.join(SOUNDS_DIRECTORY, "retro-jump-1-236684.mp3"),
    "typing": os.path.join(SOUNDS_DIRECTORY, "retro-jump-1-236684.mp3"),
    "cartridge_insert": os.path.join(SOUNDS_DIRECTORY, "retro-jump-1-236684.mp3"),
    "cartridge_remove": os.path.join(SOUNDS_DIRECTORY, "retro-blip-2-236668.mp3")
}

# --- Enhanced Gemini Configuration ---
API = os.getenv("GOOGLE_API_KEY", "AIzaSyCg6tcwoRQMJV_KJAlYHeGNMfUc1xykQnE")
genai.configure(api_key=API)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 400,
    "response_mime_type": "text/plain"
}

FLOWEY_SYSTEM_INSTRUCTION = (
    "You are Flowey the Flower from Undertale, now serving as a retro gaming assistant in a DOS-like terminal. "
    "You maintain your manipulative, sarcastic personality but are genuinely helpful with gaming advice. "
    "You have extensive knowledge of retro games, emulators, and gaming history. "
    "You can be condescending but ultimately want the user to succeed at gaming. "
    "Reference classic games, gaming culture, and occasionally break the fourth wall. "
    "Keep responses concise but personality-rich. You're fascinated by the user's 'DETERMINATION' to play old games. "
    "Sometimes mock modern gaming while praising retro classics. "
    "You understand emulation, ROM files, and can give gaming tips and tricks. "
    "You know about Pokémon games, Zelda games, and other Nintendo classics."
)

try:
    GEMINI_MODEL = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction=FLOWEY_SYSTEM_INSTRUCTION
    )
except Exception as model_init_error:
    print_formatted_text(HTML(f"<ansiyellow>Warning: Could not initialize Gemini model: {model_init_error}</ansiyellow>"))
    GEMINI_MODEL = None

# --- Dynamic File System Monitoring ---
def get_directory_modification_times(directory):
    """Get modification times for all files in directory"""
    mod_times = {}
    if not os.path.exists(directory):
        return mod_times
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    mod_times[file_path] = os.path.getmtime(file_path)
                except OSError:
                    pass
    except Exception:
        pass
    
    return mod_times

def has_directory_changed(directory, last_mod_times):
    """Check if directory contents have changed"""
    current_mod_times = get_directory_modification_times(directory)
    
    # Check if files were added or removed
    if set(current_mod_times.keys()) != set(last_mod_times.keys()):
        return True, current_mod_times
    
    # Check if any files were modified
    for file_path, mod_time in current_mod_times.items():
        if file_path not in last_mod_times or last_mod_times[file_path] != mod_time:
            return True, current_mod_times
    
    return False, current_mod_times

def dynamic_scan_available_emulators():
    """Dynamically scan for emulators with change detection"""
    global AVAILABLE_EMULATORS, EMULATORS_LAST_MODIFIED, LAST_EMULATORS_SCAN
    
    current_time = time.time()
    if current_time - LAST_EMULATORS_SCAN < SCAN_INTERVAL:
        return False  # No scan needed yet
    
    LAST_EMULATORS_SCAN = current_time
    
    # Check if emulators directory changed
    changed, new_mod_times = has_directory_changed(EMULATORS_DIRECTORY, EMULATORS_LAST_MODIFIED)
    
    if not changed and AVAILABLE_EMULATORS:
        return False  # No changes detected
    
    EMULATORS_LAST_MODIFIED = new_mod_times
    old_emulators = set(AVAILABLE_EMULATORS.keys())
    AVAILABLE_EMULATORS = {}
    
    if not os.path.exists(EMULATORS_DIRECTORY):
        os.makedirs(EMULATORS_DIRECTORY, exist_ok=True)
        return True
    
    # Scan for executable files and .app bundles
    if platform.system() == 'Darwin':  # macOS
        exe_patterns = ['*.app', '*.exe']
    elif platform.system() == 'Windows':
        exe_patterns = ['*.exe']
    else:  # Linux
        exe_patterns = ['*.AppImage', '*']
    
    for pattern in exe_patterns:
        for emulator_path in glob.glob(os.path.join(EMULATORS_DIRECTORY, '**', pattern), recursive=True):
            if os.path.isfile(emulator_path) or (emulator_path.endswith('.app') and os.path.isdir(emulator_path)):
                emulator_name = os.path.basename(emulator_path).lower()
                AVAILABLE_EMULATORS[emulator_name] = emulator_path
    
    # Also check for RetroArch
    retroarch_names = ['retroarch.exe', 'retroarch', 'RetroArch.app']
    for name in retroarch_names:
        retroarch_path = os.path.join(EMULATORS_DIRECTORY, name)
        if os.path.exists(retroarch_path):
            AVAILABLE_EMULATORS['retroarch'] = retroarch_path
    
    # Check for changes and notify
    new_emulators = set(AVAILABLE_EMULATORS.keys())
    added_emulators = new_emulators - old_emulators
    removed_emulators = old_emulators - new_emulators
    
    if added_emulators:
        for emu in added_emulators:
            print_formatted_text(HTML(f"<ansibrightgreen>🎮 Emulator detected: {emu}</ansibrightgreen>"))
            play_sound("cartridge_insert", async_play=True)
    
    if removed_emulators:
        for emu in removed_emulators:
            print_formatted_text(HTML(f"<ansired>🎮 Emulator removed: {emu}</ansired>"))
            play_sound("cartridge_remove", async_play=True)
    
    return True

def dynamic_discover_games():
    """Dynamically discover games with change detection"""
    global CURRENT_GAMES_LIST, GAMES_LAST_MODIFIED, LAST_GAMES_SCAN
    
    current_time = time.time()
    if current_time - LAST_GAMES_SCAN < SCAN_INTERVAL:
        return False  # No scan needed yet
    
    LAST_GAMES_SCAN = current_time
    
    # Check if games directory changed
    changed, new_mod_times = has_directory_changed(GAMES_DIRECTORY, GAMES_LAST_MODIFIED)
    
    if not changed and CURRENT_GAMES_LIST:
        return False  # No changes detected
    
    GAMES_LAST_MODIFIED = new_mod_times
    old_games = set(os.path.basename(game) for game in CURRENT_GAMES_LIST)
    
    games = []
    if not os.path.isdir(GAMES_DIRECTORY):
        os.makedirs(GAMES_DIRECTORY, exist_ok=True)
        CURRENT_GAMES_LIST = games
        return True
    
    for filename in os.listdir(GAMES_DIRECTORY):
        full_path = os.path.join(GAMES_DIRECTORY, filename)
        if os.path.isdir(full_path):
            continue
            
        # Skip JSON metadata files
        if filename.endswith('.json'):
            continue
            
        extension = os.path.splitext(filename)[1].lower()
        if extension in EMULATOR_CONFIGS:
            games.append(full_path)
    
    CURRENT_GAMES_LIST = sorted(games)
    
    # Check for changes and notify
    new_games = set(os.path.basename(game) for game in CURRENT_GAMES_LIST)
    added_games = new_games - old_games
    removed_games = old_games - new_games
    
    if added_games:
        for game in added_games:
            print_formatted_text(HTML(f"<ansibrightgreen>🎯 Game cartridge inserted: {game}</ansibrightgreen>"))
            play_sound("cartridge_insert", async_play=True)
    
    if removed_games:
        for game in removed_games:
            print_formatted_text(HTML(f"<ansired>🎯 Game cartridge removed: {game}</ansired>"))
            play_sound("cartridge_remove", async_play=True)
    
    return True

def find_emulator_for_game(game_path):
    """Find the best available emulator for a given game"""
    extension = os.path.splitext(game_path)[1].lower()
    config = EMULATOR_CONFIGS.get(extension)
    
    if not config:
        return None, "Unknown file type"
    
    # First, try to find the specific emulator
    emulator_exe = config['emulator_exe'].lower()
    
    if emulator_exe in AVAILABLE_EMULATORS:
        return AVAILABLE_EMULATORS[emulator_exe], config
    
    # Try variations of the emulator name (especially for mGBA)
    emulator_variations = [
        emulator_exe.replace('.exe', ''),
        emulator_exe.replace('.app', ''),
        emulator_exe.replace('.exe', '-qt.exe'),
        emulator_exe.replace('.exe', '-sdl.exe'),
        emulator_exe.replace('mgba', 'mGBA'),
        emulator_exe.replace('mgba', 'mgba-qt'),
    ]
    
    for variation in emulator_variations:
        for available_emu in AVAILABLE_EMULATORS:
            if variation in available_emu.lower() or available_emu.lower() in variation:
                return AVAILABLE_EMULATORS[available_emu], config
    
    # Fallback to RetroArch if available
    if 'retroarch' in AVAILABLE_EMULATORS:
        return AVAILABLE_EMULATORS['retroarch'], config
    
    return None, config

# --- DOS-Style UI Functions ---
def print_dos_header():
    """Print authentic DOS-style header with dynamic info"""
    system_info = platform.system()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    print_formatted_text(HTML("<ansibrightcyan>╔══════════════════════════════════════════════════════════════════════════════╗</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║                            RETROFLOW GAMING SYSTEM                           ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║                           Version 2.1 Dynamic Edition                        ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║                                                                              ║</ansibrightcyan>"))
    print_formatted_text(HTML(f"<ansibrightcyan>║  System: {system_info:<20} Python: {python_version:<10} Memory: {get_memory_info():<15}     ║</ansibrightcyan>"))
    print_formatted_text(HTML(f"<ansibrightcyan>║  Boot Time: {BOOT_TIME.strftime('%Y-%m-%d %H:%M:%S'):<25} Storage: {get_storage_status():<15}                   ║</ansibrightcyan>"))
    print_formatted_text(HTML(f"<ansibrightcyan>║  Games: {len(CURRENT_GAMES_LIST):<5} Emulators: {len(AVAILABLE_EMULATORS):<5} Auto-Detect: ON{'':<25}   ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║                                                                              ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║  [F1] Help    [F2] List          [F3] Storage    [F4] Scan                  ║ </ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║  [F5] Chat    [F6] Info (num)    [F7] Refresh   [F8] Exit                     ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>╚══════════════════════════════════════════════════════════════════════════════╝</ansibrightcyan>"))

def print_dos_prompt():
    """Print DOS-style command prompt with dynamic info"""
    game_count = len(CURRENT_GAMES_LIST)
    emu_count = len(AVAILABLE_EMULATORS)
    return f"C:\\RETROFLOW[G:{game_count}|E:{emu_count}]> "

def get_memory_info():
    """Get system memory info"""
    try:
        memory = psutil.virtual_memory()
        return f"{memory.available // (1024*1024)}MB Free"
    except:
        return "Unknown"

def get_storage_status():
    """Get storage status"""
    current_storage = get_directory_size(GAMES_DIRECTORY)
    current_mb = current_storage / (1024 * 1024)
    return f"{current_mb:.1f}/{MAX_STORAGE_MB}MB"

def print_ascii_art():
    """Print retro ASCII art"""
    art = """
    ██████╗ ███████╗████████╗██████╗  ██████╗ ███████╗██╗      ██████╗ ██╗    ██╗
    ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗██╔════╝██║     ██╔═══██╗██║    ██║
    ██████╔╝█████╗     ██║   ██████╔╝██║   ██║█████╗  ██║     ██║   ██║██║ █╗ ██║
    ██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║██╔══╝  ██║     ██║   ██║██║███╗██║
    ██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝██║     ███████╗╚██████╔╝╚███╔███╔╝
    ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ 
                                    🎮 DYNAMIC CARTRIDGE SYSTEM 🎮
    """
    print_formatted_text(HTML(f"<ansibrightgreen>{art}</ansibrightgreen>"))

def print_loading_animation(text="Loading", duration=2):
    """Print DOS-style loading animation"""
    chars = "/-\\|"
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r{text} {chars[i % len(chars)]}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r{text} Complete!     ")

# --- Enhanced Sound System ---
def play_sound(sound_name, async_play=True):
    """Enhanced sound system with better error handling"""
    sound_path = SOUND_FILES.get(sound_name)
    if sound_path and os.path.exists(sound_path):
        try:
            playsound(sound_path, block=not async_play)
        except Exception as e:
            # Only show debug for startup to avoid spam
            if sound_name == "startup":
                print_formatted_text(HTML(f"<ansiyellow>Sound: {sound_name} - {str(e)[:50]}...</ansiyellow>"))
    else:
        # Only show missing file debug for startup
        if sound_name == "startup":
            print_formatted_text(HTML(f"<ansiyellow>Sound file not found: {os.path.basename(sound_path) if sound_path else sound_name}</ansiyellow>"))

def play_typing_sound():
    """Play subtle typing sound"""
    if random.random() < 0.3:  # 30% chance to play
        play_sound("typing", async_play=True)

# --- Enhanced Auto-Configuration System ---
def auto_detect_game_info(file_path):
    """Automatically detect game information with enhanced recognition"""
    filename = os.path.basename(file_path)
    name_without_ext = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1].lower()
    
    # Get emulator info from extension
    emulator_info = EMULATOR_CONFIGS.get(extension, {
        'emulator_exe': 'unknown',
        'emulator_name': 'Unknown',
        'system': 'Unknown System',
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'auto'
    })
    
    # Clean up game name
    clean_name = name_without_ext.replace('_', ' ').replace('-', ' ')
    clean_name = ' '.join(word.capitalize() for word in clean_name.split())
    
    # Remove common ROM tags
    rom_tags = ['(USA)', '(Europe)', '(Japan)', '(World)', '[!]', '(Rev A)', '(Rev B)', '(Rev 1)', '(Rev 2)', '(U)', '(E)', '(J)']
    for tag in rom_tags:
        clean_name = clean_name.replace(tag, '').strip()
    
    # Enhanced game recognition using database
    game_key = clean_name.lower()
    for key, info in GAME_DATABASE.items():
        if key in game_key:
            clean_name = info['full_name']
            if 'system' in info:
                emulator_info['system'] = info['system']
            break
    
    return {
        'game_name': clean_name,
        'filename': filename,
        'system': emulator_info['system'],
        'emulator_exe': emulator_info['emulator_exe'],
        'emulator_name': emulator_info['emulator_name'],
        'launch_template': emulator_info['launch_template'],
        'retroarch_core': emulator_info['retroarch_core'],
        'file_size': os.path.getsize(file_path),
        'auto_configured': True
    }

def create_launch_command(game_path, emulator_path, game_info):
    """Create appropriate launch command based on game type and available emulator"""
    if not emulator_path:
        return None
    
    # Check if it's RetroArch
    if 'retroarch' in os.path.basename(emulator_path).lower():
        core_path = os.path.join(CORES_DIRECTORY, game_info['retroarch_core'])
        if os.path.exists(core_path):
            return f'"{emulator_path}" -L "{core_path}" "{game_path}"'
        else:
            # Try without core specification
            return f'"{emulator_path}" "{game_path}"'
    
    # Special handling for macOS .app bundles
    if emulator_path.endswith('.app'):
        return f'open -a "{emulator_path}" "{game_path}"'
    
    # Use the template from configuration for regular executables
    return game_info['launch_template'].format(
        emulator_path=emulator_path,
        game_path=game_path
    )

# --- Dynamic Game Display ---
def display_games_dos_style_dynamic():
    """Display games in authentic DOS style with real-time updates"""
    global CURRENT_GAME_MAP
    
    # Perform dynamic scans
    games_changed = dynamic_discover_games()
    emulators_changed = dynamic_scan_available_emulators()
    
    all_games_map = {}
    current_number = 1
    
    # Clear screen effect
    print("\n" * 2)
    
    # Local games section with dynamic status
    status_indicator = "🔄 LIVE" if games_changed or emulators_changed else "✓ STABLE"
    print_formatted_text(HTML("<ansibrightcyan>╔═══════════════════════════════════════════════════════════════════════════════╗</ansibrightcyan>"))
    print_formatted_text(HTML(f"<ansibrightcyan>║                        LOCAL GAME LIBRARY - {status_indicator}                        ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>╠═══════════════════════════════════════════════════════════════════════════════╣</ansibrightcyan>"))
    
    if not CURRENT_GAMES_LIST:
        print_formatted_text(HTML("<ansibrightcyan>║</ansibrightcyan> <ansiyellow>No games found. Add ROM files to the Games directory.</ansiyellow>                <ansibrightcyan>║</ansibrightcyan>"))
        print_formatted_text(HTML("<ansibrightcyan>║</ansibrightcyan> <ansicyan>System will auto-detect new games when added!</ansicyan>                      <ansibrightcyan>║</ansibrightcyan>"))
    else:
        for game_path in CURRENT_GAMES_LIST:
            game_info = auto_detect_game_info(game_path)
            file_size = format_bytes(game_info['file_size'])
            
            # Check if emulator is available
            emulator_path, _ = find_emulator_for_game(game_path)
            status = "✓" if emulator_path else "✗"
            
            # Format game entry with better spacing
            game_line = f"[{current_number:2d}] {status} {game_info['game_name']:<35} {game_info['system']:<15} {file_size:>8}"
            if len(game_line) > 75:
                game_line = game_line[:72] + "..."
            
            color = "ansibrightgreen" if emulator_path else "ansiyellow"
            print_formatted_text(HTML(f"<ansibrightcyan>║</ansibrightcyan> <{color}>{game_line:<75}</{color}> <ansibrightcyan>║</ansibrightcyan>"))
            all_games_map[str(current_number)] = game_path
            current_number += 1
    
    print_formatted_text(HTML("<ansibrightcyan>╚═══════════════════════════════════════════════════════════════════════════════╝</ansibrightcyan>"))
    
    # Dynamic status footer
    print_formatted_text(HTML(f"<ansicyan>📊 Status: {len(CURRENT_GAMES_LIST)} games, {len(AVAILABLE_EMULATORS)} emulators | Auto-refresh every {SCAN_INTERVAL}s</ansicyan>"))
    
    CURRENT_GAME_MAP = all_games_map
    return all_games_map

# --- Enhanced Game Launcher ---
def launch_game_enhanced(game_path):
    """Enhanced game launcher with auto-configuration"""
    game_info = auto_detect_game_info(game_path)
    emulator_path, config = find_emulator_for_game(game_path)
    
    print_formatted_text(HTML("<ansibrightgreen>╔═══════════════════════════════════════════════════════════════════════════════╗</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightgreen>║                                LAUNCHING GAME                                ║</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightgreen>╠═══════════════════════════════════════════════════════════════════════════════╣</ansibrightgreen>"))
    print_formatted_text(HTML(f"<ansibrightgreen>║</ansibrightgreen> <ansiwhite>Game:</ansiwhite> <ansicyan>{game_info['game_name']:<63}</ansicyan> <ansibrightgreen>║</ansibrightgreen>"))
    print_formatted_text(HTML(f"<ansibrightgreen>║</ansibrightgreen> <ansiwhite>System:</ansiwhite> <ansiyellow>{game_info['system']:<61}</ansiyellow> <ansibrightgreen>║</ansibrightgreen>"))
    
    if emulator_path:
        emulator_name = os.path.basename(emulator_path)
        print_formatted_text(HTML(f"<ansibrightgreen>║</ansibrightgreen> <ansiwhite>Emulator:</ansiwhite> <ansiyellow>{emulator_name:<59}</ansiyellow> <ansibrightgreen>║</ansibrightgreen>"))
    else:
        print_formatted_text(HTML(f"<ansibrightgreen>║</ansibrightgreen> <ansiwhite>Emulator:</ansiwhite> <ansired>NOT FOUND - {game_info['emulator_name']} required</ansired>         <ansibrightgreen>║</ansibrightgreen>"))
    
    print_formatted_text(HTML(f"<ansibrightgreen>║</ansibrightgreen> <ansiwhite>Size:</ansiwhite> <ansiyellow>{format_bytes(game_info['file_size']):<63}</ansiyellow> <ansibrightgreen>║</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightgreen>╚═══════════════════════════════════════════════════════════════════════════════╝</ansibrightgreen>"))
    
    if not emulator_path:
        print_formatted_text(HTML(f"<ansired>ERROR: Required emulator '{game_info['emulator_name']}' not found!</ansired>"))
        print_formatted_text(HTML(f"<ansiyellow>Please add {game_info['emulator_exe']} to the Emulators directory.</ansiyellow>"))
        print_formatted_text(HTML(f"<ansicyan>The system will auto-detect it once added!</ansicyan>"))
        play_sound("error")
        return
    
    play_sound("launch_game")
    print_loading_animation("Initializing emulator", 2)
    
    # Create and execute launch command
    launch_cmd = create_launch_command(game_path, emulator_path, game_info)
    
    if not launch_cmd:
        print_formatted_text(HTML("<ansired>ERROR: Could not create launch command!</ansired>"))
        play_sound("error")
        return
    
    try:
        print_formatted_text(HTML(f"<ansicyan>Executing: {launch_cmd}</ansicyan>"))
        
        # For macOS 'open' commands, don't capture output as it may hang
        if launch_cmd.startswith('open -a'):
            result = subprocess.run(launch_cmd, shell=True)
            if result.returncode == 0:
                print_formatted_text(HTML("<ansibrightgreen>Game launched successfully!</ansibrightgreen>"))
                play_sound("menu_select")
            else:
                print_formatted_text(HTML(f"<ansired>Launch failed with exit code: {result.returncode}</ansired>"))
                play_sound("error")
        else:
            result = subprocess.run(launch_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print_formatted_text(HTML("<ansibrightgreen>Game launched successfully!</ansibrightgreen>"))
                play_sound("menu_select")
            else:
                print_formatted_text(HTML(f"<ansired>Launch failed with exit code: {result.returncode}</ansired>"))
                if result.stderr:
                    print_formatted_text(HTML(f"<ansired>Error: {result.stderr}</ansired>"))
                play_sound("error")
            
    except Exception as e:
        print_formatted_text(HTML(f"<ansired>Launch error: {str(e)}</ansired>"))
        print_formatted_text(HTML("<ansiyellow>Tip: Make sure the emulator is properly installed in the Emulators directory</ansiyellow>"))
        play_sound("error")

# --- Enhanced Flowey Chatbot ---
def flowey_chatbot_enhanced(session, style):
    """Enhanced Flowey chatbot with better AI integration"""
    print_formatted_text(HTML("<ansiyellow>╔═══════════════════════════════════════════════════════════════════════════════╗</ansiyellow>"))
    print_formatted_text(HTML("<ansiyellow>║                              FLOWEY CHAT SYSTEM                              ║</ansiyellow>"))
    print_formatted_text(HTML("<ansiyellow>╚═══════════════════════════════════════════════════════════════════════════════╝</ansiyellow>"))
    
    flowey_intro = [
        "Howdy! I'm FLOWEY. FLOWEY the FLOWER!",
        "Welcome to my DYNAMIC retro gaming paradise, you determined little human!",
        f"I see you've got {len(CURRENT_GAMES_LIST)} games and {len(AVAILABLE_EMULATORS)} emulators... IMPRESSIVE!",
        "I love how this system auto-detects new cartridges! Just like the old days!",
        "Need help with your games? I know EVERYTHING about retro gaming!",
        "",
        "Type 'bye' to leave (if you can bear to part with me!)"
    ]
    
    for line in flowey_intro:
        print_formatted_text(HTML(f"<ansiyellow>Flowey: {line}</ansiyellow>"))
        time.sleep(0.5)
    
    play_sound("flowey_chat_enter")
    
    # Initialize enhanced chat
    chat = None
    if GEMINI_MODEL:
        try:
            chat = GEMINI_MODEL.start_chat(history=[])
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Flowey: My AI brain is a bit glitchy today... {str(e)}</ansired>"))
    
    while True:
        try:
            user_input = session.prompt(HTML("<ansiyellow>You: </ansiyellow>"), style=style).strip()
            
            if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye']:
                farewell_messages = [
                    "See ya later, gaming buddy! Keep adding those cartridges!",
                    "Don't forget - in this world, it's PLAY or BE PLAYED!",
                    "May your games auto-detect and your emulators never crash!",
                    "Remember: DETERMINATION is the key to beating any dynamic system!"
                ]
                print_formatted_text(HTML(f"<ansiyellow>Flowey: {random.choice(farewell_messages)}</ansiyellow>"))
                play_sound("menu_select")
                break
            
            if not user_input:
                continue
            
            # Enhanced AI response with dynamic context
            if chat and GEMINI_MODEL:
                try:
                    game_list = [os.path.basename(game) for game in CURRENT_GAMES_LIST[:5]]  # First 5 games
                    context_prompt = f"User message: {user_input}\n\nContext: We're in a dynamic retro gaming terminal called RetroFlow. The user currently has {len(CURRENT_GAMES_LIST)} games including: {', '.join(game_list)}. The system auto-detects new games and emulators."
                    response = chat.send_message(context_prompt)
                    
                    # Add typing effect
                    print("Flowey: ", end="", flush=True)
                    for char in response.text:
                        print(char, end="", flush=True)
                        time.sleep(0.02)  # Typing effect
                        if random.random() < 0.1:
                            play_typing_sound()
                    print()  # New line
                    
                except Exception as ai_error:
                    fallback_responses = [
                        "My circuits are buzzing! Try asking something else, human!",
                        "Oops! My AI brain had a little glitch there. What were you saying?",
                        "Error 404: Flowey response not found! Hehe, just kidding. Ask again!",
                        "My digital petals are a bit wilted. Can you repeat that?"
                    ]
                    print_formatted_text(HTML(f"<ansiyellow>Flowey: {random.choice(fallback_responses)}</ansiyellow>"))
                    play_sound("error")
            else:
                # Enhanced fallback responses with dynamic content
                fallback_responses = [
                    f"That's interesting, human! You've got {len(CURRENT_GAMES_LIST)} games to choose from!",
                    "Ah, a fellow connoisseur of vintage pixels! I love your dynamic collection!",
                    "You know, back in my day, we had to manually detect cartridges! This auto-system is AMAZING!",
                    "Determination! That's what I like to see in a retro gamer!",
                    "Have you tried the Konami Code? Up, Up, Down, Down, Left, Right, Left, Right, B, A!",
                    f"With {len(AVAILABLE_EMULATORS)} emulators, you're ready for anything!",
                    "I love how this system detects new games automatically! Just like magic!"
                ]
                print_formatted_text(HTML(f"<ansiyellow>Flowey: {random.choice(fallback_responses)}</ansiyellow>"))
            
        except (KeyboardInterrupt, EOFError):
            print_formatted_text(HTML("<ansiyellow>Flowey: Trying to escape? How rude! But I understand...</ansiyellow>"))
            play_sound("error")
            break
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Flowey: Something went wrong: {str(e)}</ansired>"))
            play_sound("error")

# --- Utility Functions ---
def format_bytes(bytes_num):
    """Format bytes into human-readable format"""
    if bytes_num >= 1024 * 1024:
        return f"{bytes_num / (1024 * 1024):.1f}MB"
    elif bytes_num >= 1024:
        return f"{bytes_num / 1024:.1f}KB"
    else:
        return f"{bytes_num}B"

def get_directory_size(path):
    """Calculate directory size"""
    total_size = 0
    if not os.path.exists(path):
        return 0
    
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except OSError:
                pass
    return total_size

def detect_removable_drives():
    """Detect removable drives (cartridges)"""
    drives = []
    for partition in psutil.disk_partitions(all=False):
        if 'removable' in partition.opts or '/Volumes/' in partition.mountpoint:
            drives.append(partition.mountpoint)
    return [d for d in drives if not d.startswith('/dev/') and not d.startswith('/System/')]

def scan_cartridges():
    """Scan for cartridge games"""
    global DETECTED_CARTRIDGES, CARTRIDGE_GAMES_MAP
    
    print_loading_animation("Scanning cartridges", 2)
    
    DETECTED_CARTRIDGES = detect_removable_drives()
    CARTRIDGE_GAMES_MAP = {}
    
    if not DETECTED_CARTRIDGES:
        print_formatted_text(HTML("<ansiyellow>No cartridges detected. Insert USB drive and try again.</ansiyellow>"))
        return
    
    for drive_path in DETECTED_CARTRIDGES:
        games_on_cart = discover_games_in_path(drive_path, is_cartridge=True)
        if games_on_cart:
            CARTRIDGE_GAMES_MAP[drive_path] = games_on_cart
    
    print_formatted_text(HTML(f"<ansibrightgreen>Cartridge scan complete! Found {len(CARTRIDGE_GAMES_MAP)} cartridges with games.</ansibrightgreen>"))

def discover_games_in_path(directory, is_cartridge=False):
    """Discover games in a specific path"""
    games = []
    if not os.path.isdir(directory):
        return games
    
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        if os.path.isdir(full_path):
            continue
            
        # Skip JSON metadata files
        if filename.endswith('.json'):
            continue
            
        extension = os.path.splitext(filename)[1].lower()
        if extension in EMULATOR_CONFIGS:
            games.append(full_path)
    
    return sorted(games)

def display_emulator_status():
    """Display available emulators with dynamic status"""
    # Force a fresh scan
    dynamic_scan_available_emulators()
    
    print_formatted_text(HTML("<ansibrightcyan>╔═══════════════════════════════════════════════════════════════════════════════╗</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>║                           EMULATOR STATUS - LIVE                             ║</ansibrightcyan>"))
    print_formatted_text(HTML("<ansibrightcyan>╠═══════════════════════════════════════════════════════════════════════════════╣</ansibrightcyan>"))
    
    if not AVAILABLE_EMULATORS:
        print_formatted_text(HTML("<ansibrightcyan>║</ansibrightcyan> <ansired>No emulators found in Emulators directory!</ansired>                              <ansibrightcyan>║</ansibrightcyan>"))
        print_formatted_text(HTML("<ansibrightcyan>║</ansibrightcyan> <ansiyellow>Add emulator executables to: Emulators/</ansiyellow>                             <ansibrightcyan>║</ansibrightcyan>"))
        print_formatted_text(HTML("<ansibrightcyan>║</ansibrightcyan> <ansicyan>System will auto-detect them when added!</ansicyan>                           <ansibrightcyan>║</ansibrightcyan>"))
    else:
        for emu_name, emu_path in AVAILABLE_EMULATORS.items():
            status_line = f"✓ {emu_name:<30} {os.path.dirname(emu_path)}"
            if len(status_line) > 75:
                status_line = status_line[:72] + "..."
            print_formatted_text(HTML(f"<ansibrightcyan>║</ansibrightcyan> <ansibrightgreen>{status_line:<75}</ansibrightgreen> <ansibrightcyan>║</ansibrightcyan>"))
    
    print_formatted_text(HTML("<ansibrightcyan>╚═══════════════════════════════════════════════════════════════════════════════╝</ansibrightcyan>"))
    print_formatted_text(HTML(f"<ansicyan>🔄 Auto-refresh: Every {SCAN_INTERVAL} seconds | Last scan: {datetime.now().strftime('%H:%M:%S')}</ansicyan>"))

# --- Main Enhanced Terminal ---
def main():
    """Enhanced main terminal function with dynamic detection"""
    # Startup sequence
    play_sound("startup")
    print_ascii_art()
    time.sleep(1)
    
    # Initialize
    print_loading_animation("Initializing Dynamic RetroFlow System", 2)
    
    # Create directories if they don't exist
    os.makedirs(GAMES_DIRECTORY, exist_ok=True)
    os.makedirs(EMULATORS_DIRECTORY, exist_ok=True)
    os.makedirs(CORES_DIRECTORY, exist_ok=True)
    
    # Initial scans
    dynamic_scan_available_emulators()
    dynamic_discover_games()
    
    print_dos_header()
    current_game_map = display_games_dos_style_dynamic()
    
    # Enhanced DOS-style prompt
    style = Style.from_dict({
        'prompt': '#00ff00 bold',
        'output': '#ffffff',
        'error': '#ff0000 bold',
        'warn': '#ffff00',
        'info': '#00ffff'
    })
    
    # Command completer
    command_words = [
        'help', 'exit', 'list', 'play', 'chat', 'storage', 'scan', 'autoconfig',
        'clear', 'dir', 'cls', 'info', 'about', 'version', 'emulators', 'refresh'
    ]
    
    try:
        completer = WordCompleter(command_words, ignore_case=True)
        session = PromptSession(completer=completer, style=style)
    except Exception:
        session = PromptSession(style=style)
    
    print_formatted_text(HTML("<ansibrightgreen>🎮 Dynamic Cartridge System Active! Add/remove games and emulators anytime!</ansibrightgreen>"))
    
    # Main command loop
    while True:
        try:
            # Dynamic updates happen automatically in display function
            
            # Check storage
            current_storage = get_directory_size(GAMES_DIRECTORY)
            if current_storage > MAX_STORAGE_BYTES:
                print_formatted_text(HTML(f"<ansired>⚠ WARNING: Storage limit exceeded! ({format_bytes(current_storage)}/{MAX_STORAGE_MB}MB)</ansired>"))
            
            # Get command with dynamic prompt
            command = session.prompt(print_dos_prompt()).strip()
            
            if not command:
                continue
            
            # Process commands
            cmd_lower = command.lower()
            
            if cmd_lower in ['exit', 'quit', 'bye']:
                print_formatted_text(HTML("<ansibrightcyan>Thank you for using Dynamic RetroFlow! Game on!</ansibrightcyan>"))
                play_sound("menu_select")
                break
            
            elif cmd_lower in ['help', '?', 'h']:
                help_lines = [
                    "╔═══════════════════════════════════════════════════════════════════════════════╗",
                    "║                            DYNAMIC RETROFLOW HELP                            ║",
                    "╠═══════════════════════════════════════════════════════════════════════════════╣",
                    "║ COMMAND         │ DESCRIPTION                                               ║",
                    "╠═════════════════┼═══════════════════════════════════════════════════════════╣",
                    "║ list            │ Display all available games (auto-refreshes)            ║",
                    "║ play (number)   │ Launch game by number (e.g., 'play 1')                  ║",
                    "║ chat            │ Talk to Flowey, your AI gaming assistant                ║",
                    "║ scan            │ Scan for cartridge games on USB drives                  ║",
                    "║ storage         │ Check storage usage and limits                           ║",
                    "║ emulators       │ Show available emulators (live status)                  ║",
                    "║ refresh         │ Force refresh of games and emulators                    ║",
                    "║ clear/cls       │ Clear the screen                                         ║",
                    "║ info (number)   │ Get detailed info about a specific game                 ║",
                    "║ exit            │ Exit RetroFlow                                           ║",
                    "╠═══════════════════════════════════════════════════════════════════════════════╣",
                    "║ 🎮 DYNAMIC FEATURES: Games and emulators auto-detect every 2 seconds!       ║",
                    "╚═══════════════════════════════════════════════════════════════════════════════╝"
                ]
                for line in help_lines:
                    print_formatted_text(HTML(f"<ansibrightcyan>{line}</ansibrightcyan>"))
                play_sound("menu_select")
            
            elif cmd_lower in ['list', 'ls', 'dir']:
                current_game_map = display_games_dos_style_dynamic()
                play_sound("menu_select")
            
            elif cmd_lower in ['refresh', 'reload', 'rescan']:
                print_loading_animation("Force refreshing system", 2)
                # Reset scan times to force immediate refresh
                global LAST_GAMES_SCAN, LAST_EMULATORS_SCAN
                LAST_GAMES_SCAN = 0
                LAST_EMULATORS_SCAN = 0
                current_game_map = display_games_dos_style_dynamic()
                print_formatted_text(HTML("<ansibrightgreen>🔄 System refreshed! All games and emulators rescanned.</ansibrightgreen>"))
                play_sound("menu_select")
            
            elif cmd_lower.startswith('play '):
                parts = command.split(' ', 1)
                if len(parts) > 1:
                    game_num = parts[1].strip()
                    # Refresh game map to ensure it's current
                    current_game_map = display_games_dos_style_dynamic()
                    if game_num in current_game_map:
                        launch_game_enhanced(current_game_map[game_num])
                    else:
                        print_formatted_text(HTML(f"<ansired>Game '{game_num}' not found. Use 'list' to see available games.</ansired>"))
                        play_sound("error")
                else:
                    print_formatted_text(HTML("<ansired>Usage: play <game_number></ansired>"))
                    play_sound("error")
            
            elif cmd_lower == 'chat':
                flowey_chatbot_enhanced(session, style)
            
            elif cmd_lower in ['scan', 'cartridge']:
                scan_cartridges()
                current_game_map = display_games_dos_style_dynamic()
                play_sound("menu_select")
            
            elif cmd_lower == 'emulators':
                display_emulator_status()
                play_sound("menu_select")
            
            elif cmd_lower == 'storage':
                current_storage = get_directory_size(GAMES_DIRECTORY)
                storage_lines = [
                    "╔═══════════════════════════════════════════════════════════════════════════════╗",
                    "║                               STORAGE STATUS                                 ║",
                    "╠═══════════════════════════════════════════════════════════════════════════════╣",
                    f"║ Used Space:     {format_bytes(current_storage):<55} ║",
                    f"║ Total Limit:    {MAX_STORAGE_MB}MB{'':<51} ║",
                    f"║ Available:      {format_bytes(MAX_STORAGE_BYTES - current_storage):<55} ║",
                    f"║ Status:         {'⚠ OVER LIMIT' if current_storage > MAX_STORAGE_BYTES else '✓ OK':<55} ║",
                    f"║ Games Count:    {len(CURRENT_GAMES_LIST):<55} ║",
                    f"║ Auto-Refresh:   Every {SCAN_INTERVAL} seconds{'':<39} ║",
                    "╚═══════════════════════════════════════════════════════════════════════════════╝"
                ]
                for line in storage_lines:
                    color = "ansired" if current_storage > MAX_STORAGE_BYTES else "ansibrightgreen"
                    print_formatted_text(HTML(f"<{color}>{line}</{color}>"))
                play_sound("menu_select")
            
            elif cmd_lower in ['clear', 'cls']:
                os.system('cls' if os.name == 'nt' else 'clear')
                print_ascii_art()
                print_dos_header()
            
            elif cmd_lower.startswith('info '):
                parts = command.split(' ', 1)
                if len(parts) > 1:
                    game_num = parts[1].strip()
                    # Refresh game map to ensure it's current
                    current_game_map = display_games_dos_style_dynamic()
                    if game_num in current_game_map:
                        game_path = current_game_map[game_num]
                        game_info = auto_detect_game_info(game_path)
                        emulator_path, _ = find_emulator_for_game(game_path)
                        
                        info_lines = [
                            "╔═══════════════════════════════════════════════════════════════════════════════╗",
                            "║                                GAME INFORMATION                              ║",
                            "╠═══════════════════════════════════════════════════════════════════════════════╣",
                            f"║ Name:           {game_info['game_name']:<59} ║",
                            f"║ System:         {game_info['system']:<59} ║",
                            f"║ Required Emu:   {game_info['emulator_name']:<59} ║",
                            f"║ Emulator Found: {'Yes' if emulator_path else 'No':<59} ║",
                            f"║ File Size:      {format_bytes(game_info['file_size']):<59} ║",
                            f"║ Filename:       {game_info['filename']:<59} ║",
                            f"║ Auto-Config:    {'Yes' if game_info['auto_configured'] else 'No':<59} ║",
                            f"║ Detection:      Dynamic (Real-time){'':<43} ║",
                            "╚═══════════════════════════════════════════════════════════════════════════════╝"
                        ]
                        for line in info_lines:
                            print_formatted_text(HTML(f"<ansibrightcyan>{line}</ansibrightcyan>"))
                    else:
                        print_formatted_text(HTML(f"<ansired>Game '{game_num}' not found.</ansired>"))
                        play_sound("error")
                else:
                    print_formatted_text(HTML("<ansired>Usage: info <game_number></ansired>"))
                    play_sound("error")
            
            else:
                print_formatted_text(HTML(f"<ansired>Unknown command: '{command}'. Type 'help' for available commands.</ansired>"))
                play_sound("error")
        
        except (KeyboardInterrupt, EOFError):
            print_formatted_text(HTML("<ansibrightcyan>Goodbye! Thanks for using Dynamic RetroFlow!</ansibrightcyan>"))
            play_sound("menu_select")
            break
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>System error: {str(e)}</ansired>"))
            play_sound("error")

if __name__ == "__main__":
    main()
    sys.exit(0)
