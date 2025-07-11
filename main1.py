import subprocess
import sys
import os
import json
import psutil
import time
import random
import html
from datetime import datetime
import platform
import glob
import threading
import traceback
from pathlib import Path # Ensure this is imported
import pygame # ADD THIS LINE
import pygame.mixer as mixer # Ensure this is also present

# --- Third-Party Library Imports ---
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.styles import Style
    from prompt_toolkit import print_formatted_text, HTML
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold # Only import these
    # Explicitly import these
    # import pygame.mixer as mixer # This line is redundant if already imported above
except ImportError as e:
    print(f"FATAL ERROR: A required library is missing: {e.name}")
    print("Please run: pip install prompt_toolkit psutil google-generativeai pygame")
    sys.exit(1)


# --- Enhanced Configuration with Dynamic Detection ---

# Determine the project root dynamically, essential for portable paths
def get_project_root():
    """
    Finds the absolute path to the project's root folder.
    This works whether running as a script or a frozen .exe in a 'dist' subfolder.
    """
    if getattr(sys, 'frozen', False):
        # When running as an .exe, the executable is in 'dist'. This navigates up one level.
        return Path(sys.executable).resolve().parent.parent
    else:
        # For development, the root is where the script is located.
        return Path(__file__).resolve().parent

PROJECT_ROOT = get_project_root()
GAMES_DIRECTORY = PROJECT_ROOT / "Games"
EMULATORS_DIRECTORY = PROJECT_ROOT / "Emulators"
CORES_DIRECTORY = PROJECT_ROOT / "Cores"
SOUNDS_DIRECTORY = PROJECT_ROOT / "Sounds"
CONFIG_FILE = PROJECT_ROOT / "config.json"
LOG_FILE = PROJECT_ROOT / "retroflow.log"

# Define the sound files and their actual filenames
SOUND_FILES = {
    "startup": "retro-wave-style-track-59892.mp3",
    "launch_game": "retro-game-jingleaif-14638.mp3",
    "error": "retro-blip-2-236668.mp3",
    "menu_select": "retro-fart-104576.mp3",
    "flowey_chat_enter": "retro-jump-1-236684.mp3",
    "typing": "retro-jump-1-236684.mp3",
    "cartridge_insert": "retro-jump-1-236684.mp3",
    "cartridge_remove": "retro-blip-2-236668.mp3"
}


# Enhanced emulator configuration with better Game Boy/GBA support and RetroArch integration
# Each entry now includes 'notes' for internal documentation and 'platforms' for broader system types
EMULATOR_CONFIGS = {
    '.nes': {
        'emulator_exe': 'fceux.exe',
        'emulator_name': 'FCEUX',
        'system': 'Nintendo Entertainment System',
        'platforms': ['windows'], # Specify OS compatibility if known
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'fceumm_libretro.dll',
        'notes': 'A classic NES emulator. For Linux/macOS, consider `nestopia` or RetroArch.'
    },
    '.smc': { # SNES roms often use .smc or .sfc
        'emulator_exe': 'snes9x.exe',
        'emulator_name': 'Snes9x',
        'system': 'Super Nintendo',
        'platforms': ['windows', 'linux', 'macos'], # Snes9x is cross-platform
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'snes9x_libretro.dll',
        'notes': 'Highly compatible SNES emulator. Ensure the correct executable for your OS.'
    },
    '.sfc': { # SNES roms often use .smc or .sfc
        'emulator_exe': 'snes9x.exe',
        'emulator_name': 'Snes9x',
        'system': 'Super Nintendo',
        'platforms': ['windows', 'linux', 'macos'],
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'snes9x_libretro.dll',
        'notes': 'Alias for .smc, handled by Snes9x.'
    },
    '.gba': {
        'emulator_exe': 'mgba/mGBA.app', # Path relative to EMULATORS_DIRECTORY
        'emulator_name': 'mGBA',
        'system': 'Game Boy Advance',
        # For macOS .app bundles, use 'open -a'
        'launch_template': 'open -a "{emulator_path}" --args "{game_path}"',
        # Remove 'retroarch_core' if you are not using RetroArch for GBA,
        # otherwise, ensure you have the 'mgba_libretro.dylib' core
        'retroarch_core': 'mgba_libretro.dylib' # Change .dll to .dylib for macOS RetroArch
    },
    '.gbc': {
        'emulator_exe': 'mgba/mGBA.app', # Path relative to EMULATORS_DIRECTORY
        'emulator_name': 'mGBA',
        'system': 'Game Boy Advance',
        # For macOS .app bundles, use 'open -a'
        'launch_template': 'open -a "{emulator_path}" --args "{game_path}"',
        # Remove 'retroarch_core' if you are not using RetroArch for GBA,
        # otherwise, ensure you have the 'mgba_libretro.dylib' core
        'retroarch_core': 'mgba_libretro.dylib' # Change .dll to .dylib for macOS RetroArch
    },
    '.gb': {
        'emulator_exe': 'mgba/mGBA.app', # Path relative to EMULATORS_DIRECTORY
        'emulator_name': 'mGBA',
        'system': 'Game Boy Advance',
        # For macOS .app bundles, use 'open -a'
        'launch_template': 'open -a "{emulator_path}" --args "{game_path}"',
        # Remove 'retroarch_core' if you are not using RetroArch for GBA,
        # otherwise, ensure you have the 'mgba_libretro.dylib' core
        'retroarch_core': 'mgba_libretro.dylib' # Change .dll to .dylib for macOS RetroArch

    },
    '.md': { # Sega Genesis/Mega Drive
        'emulator_exe': 'gens.exe', # Gens or Fusion (Windows)
        'emulator_name': 'Gens',
        'system': 'Sega Genesis',
        'platforms': ['windows'],
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'genesis_plus_gx_libretro.dll',
        'notes': 'Popular Genesis emulator for Windows. Genesis Plus GX core is highly accurate.'
    },
    '.gen': { # Sega Genesis/Mega Drive (alternative extension)
        'emulator_exe': 'gens.exe',
        'emulator_name': 'Gens',
        'system': 'Sega Genesis',
        'platforms': ['windows'],
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'genesis_plus_gx_libretro.dll',
        'notes': 'Alias for .md, handled by Gens.'
    },
    '.n64': {
        'emulator_exe': 'project64.exe', # Project64 (Windows only)
        'emulator_name': 'Project64',
        'system': 'Nintendo 64',
        'platforms': ['windows'],
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'mupen64plus_next_libretro.dll',
        'notes': 'Well-known N64 emulator for Windows. Mupen64Plus Next core for RetroArch is a good alternative.'
    },
    '.ps1': { # PlayStation 1
        'emulator_exe': 'epsxe.exe', # ePSXe (Windows, Linux, macOS)
        'emulator_name': 'ePSXe',
        'system': 'PlayStation 1',
        'platforms': ['windows', 'linux', 'macos'],
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'pcsx_rearmed_libretro.dll',
        'notes': 'Versatile PS1 emulator. Requires BIOS files for full functionality.'
    },
    '.nds': { # Nintendo DS
        'emulator_exe': 'desmume.exe', # DeSmuME (Windows, Linux, macOS)
        'emulator_name': 'DeSmuME',
        'system': 'Nintendo DS',
        'platforms': ['windows', 'linux', 'macos'],
        'launch_template': '"{emulator_path}" "{game_path}"',
        'retroarch_core': 'desmume_libretro.dll',
        'notes': 'Popular Nintendo DS emulator. High compatibility.'
    },
    '.exe': { # Generic executable games
        'emulator_exe': None, # No specific emulator, the game itself is the executable
        'emulator_name': 'PC Game',
        'system': 'PC',
        'platforms': ['windows'], # .exe is primarily Windows
        'launch_template': '"{game_path}"',
        'retroarch_core': None,
        'notes': 'Launches the executable directly. Use with caution for untrusted files.'
    }
}

RETROARCH_EXE = 'retroarch.exe' # Default RetroArch executable name
RETROARCH_PATH = EMULATORS_DIRECTORY / RETROARCH_EXE

# Global state for managing games and mapping numbers to paths
CURRENT_GAME_MAP = {} # Maps display number (string) to game_path (string)
LOCAL_GAMES = [] # List of game info dicts from GAMES_DIRECTORY
CARTRIDGE_GAMES = {} # Maps drive letter/mount point (string) to a list of game info dicts
LAST_SCAN_TIMES = {} # Stores last modification time for directories to optimize scans
SCAN_INTERVAL_SECONDS = 30 # How often to scan for new/removed cartridges/games (in seconds)
MIN_DRIVE_SIZE_MB = 100 # Minimum size for a drive to be considered for scanning (to avoid system partitions)

# AI configuration
GEMINI_API_KEY = None
GEN_MODEL = None # Will be initialized if API key is set

# --- Flowey Personality System Instruction ---
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
# --- End Flowey Personality ---


# Threading for background scanning
SCAN_THREAD = None
SCAN_EVENT = threading.Event() # Event to signal the scan thread to stop
SCAN_LOCK = threading.Lock() # Lock to protect CURRENT_GAME_MAP and game lists during updates
# --- Logging and Utility Functions ---

def log_message(level, message):
    """Writes a timestamped message to the log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] {message}\n"
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except IOError as e:
        # Corrected line: Make the error message general
        print_formatted_text(HTML(f"<ansired>Error: Could not write to log file: {e}</ansired>"))

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def play_sound(sound_key): # Changed argument name to sound_key
    """Plays a sound from the Sounds directory using pygame.mixer based on its key."""
    sound_filename = SOUND_FILES.get(sound_key)
    if not sound_filename:
        log_message("WARNING", f"Sound key '{sound_key}' not found in SOUND_FILES mapping. No sound played.")
        return # Exit if the key isn't mapped

    sound_path = SOUNDS_DIRECTORY / sound_filename # Construct the full path here
    
    if sound_path.exists():
        try:
            sound = mixer.Sound(str(sound_path))
            sound.play()
            log_message("INFO", f"Played sound: '{sound_key}' (file: {sound_filename})")
        except pygame.error as e: # Corrected error handling
            log_message("WARNING", f"Pygame sound error playing '{sound_key}' ({sound_filename}) at '{sound_path}': {e}")
            pass # Suppress sound errors to not clutter console
        except Exception as e: # Catch any other unexpected errors
            log_message("WARNING", f"Could not play sound '{sound_key}' ({sound_filename}) at '{sound_path}': {e}")
            pass # Suppress sound errors to not clutter console
    else:
        log_message("WARNING", f"Sound file for '{sound_key}' ({sound_filename}) not found at '{sound_path}'. Please verify path and file.")
        pass # Suppress sound file not found errors


def load_config():
    """Loads configuration (like API key) from config.json."""
    global GEMINI_API_KEY
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: # Added encoding
                config = json.load(f)
                GEMINI_API_KEY = config.get("gemini_api_key")
                if GEMINI_API_KEY:
                    configure_gemini_api(GEMINI_API_KEY)
            log_message("INFO", "Configuration loaded successfully.")
        except json.JSONDecodeError:
            log_message("ERROR", "Config file is corrupt. Creating a new one.")
            print_formatted_text(HTML("<ansiyellow>Config file is corrupt. Creating a new one.</ansiyellow>"))
            save_config()
        except Exception as e:
            log_message("ERROR", f"Error loading config file: {e}")
            print_formatted_text(HTML(f"<ansired>Error loading config: {e}</ansired>"))
    else:
        log_message("INFO", "Config file not found. Creating default.")
        save_config() # Create default config if it doesn't exist

def save_config():
    """Saves current configuration to config.json."""
    config = {"gemini_api_key": GEMINI_API_KEY}
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: # Added encoding
            json.dump(config, f, indent=4)
        log_message("INFO", "Configuration saved successfully.")
    except Exception as e:
        log_message("ERROR", f"Error saving config file: {e}")
        print_formatted_text(HTML(f"<ansired>Error saving config: {e}</ansired>"))

def configure_gemini_api(api_key):
    """Configures the Google Gemini API."""
    global GEN_MODEL
    if api_key and api_key != "YOUR_API_KEY":
        try:
            genai.configure(api_key=api_key)
            GEN_MODEL = genai.GenerativeModel(
                'gemini-2.0-flash', # Changed back to gemini-pro, if gemini-2.0-flash works keep that one
                safety_settings=[
                    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
                    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
                ]
            )
            print_formatted_text(HTML("<ansigreen>Gemini API configured successfully!</ansigreen>"))
            play_sound("menu_select") # Using the new sound key
            log_message("INFO", "Gemini API configured.")
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Failed to configure Gemini API: {e}</ansired>"))
            GEN_MODEL = None
            play_sound("error") # Using the new sound key
            log_message("ERROR", f"Failed to configure Gemini API: {e}")
    else:
        print_formatted_text(HTML("<ansiyellow>Gemini API key not set. AI features disabled.</ansiyellow>"))
        GEN_MODEL = None
        log_message("INFO", "Gemini API key not set, AI features disabled.")


def get_directory_modification_times(path):
    """
    Returns a dictionary of paths and their last modification times for all files
    and subdirectories within the given path.
    Used to detect changes for more efficient scanning.
    """
    mod_times = {}
    if not path.is_dir():
        return mod_times # Return empty if path is not a directory

    try:
        for root, dirs, files in os.walk(path):
            current_path = Path(root)
            mod_times[str(current_path)] = current_path.stat().st_mtime
            for d in dirs:
                dir_path = current_path / d
                try:
                    mod_times[str(dir_path)] = dir_path.stat().st_mtime
                except OSError:
                    log_message("WARNING", f"Could not get modification time for directory (permission error?): {dir_path}")
            for f in files:
                file_path = current_path / f
                try:
                    mod_times[str(file_path)] = file_path.stat().st_mtime
                except OSError:
                    log_message("WARNING", f"Could not get modification time for file (permission error?): {file_path}")
        return mod_times
    except Exception as e:
        log_message("ERROR", f"Error getting modification times for {path}: {e}")
        return {}

# --- Game Discovery and Management Functions ---

def find_emulator_for_game(game_path):
    """
    Finds the best emulator configuration for a given game path.
    Prioritizes specific emulator EXEs, then RetroArch with cores.
    Returns (emulator_config, emulator_path, is_retroarch_launch).
    """
    game_path_obj = Path(game_path)
    game_extension = game_path_obj.suffix.lower()
    config = EMULATOR_CONFIGS.get(game_extension)

    if not config:
        log_message("DEBUG", f"No emulator config found for extension: {game_extension}")
        return None, None, False

    # Check for specific emulator EXE first
    if config.get('emulator_exe'):
        emulator_exe_path = EMULATORS_DIRECTORY / config['emulator_exe']
        if emulator_exe_path.exists():
            log_message("DEBUG", f"Found specific emulator {emulator_exe_path} for {game_extension}")
            return config, str(emulator_exe_path), False

    # Check for RetroArch with specific core
    if RETROARCH_PATH.exists() and config.get('retroarch_core'):
        core_path = CORES_DIRECTORY / config['retroarch_core']
        if core_path.exists():
            log_message("DEBUG", f"Found RetroArch core {core_path} for {game_extension}")
            # Create a RetroArch specific launch config
            ra_config = config.copy()
            # Ensure path is quoted correctly for subprocess
            ra_config['launch_template'] = f'"{RETROARCH_PATH}" -L "{core_path}" "{game_path_obj}"'
            ra_config['emulator_name'] = f"RetroArch ({Path(config['retroarch_core']).stem})"
            return ra_config, str(RETROARCH_PATH), True
    
    # For .exe games, the game path itself is the executable
    if game_extension == '.exe' and game_path_obj.exists():
        log_message("DEBUG", f"Treating .exe game as its own executable: {game_path_obj}")
        return config, str(game_path_obj), False # The game path is the "emulator"

    log_message("DEBUG", f"No suitable launcher found for {game_path_obj.name} (ext: {game_extension})")
    return None, None, False # No suitable emulator found

def discover_games_in_path(base_path):
    """
    Scans a given path for supported game ROMs.
    Returns a list of dictionaries, each describing a game.
    """
    found_games = []
    if not base_path.is_dir():
        log_message("WARNING", f"Attempted to scan non-existent directory: {base_path}")
        return []

    try:
        for root, _, files in os.walk(base_path):
            for filename in files:
                file_path = Path(root) / filename
                extension = file_path.suffix.lower()

                if extension in EMULATOR_CONFIGS:
                    emulator_config, emulator_path, is_retroarch = find_emulator_for_game(file_path)
                    
                    game_info = {
                        'name': file_path.stem,
                        'path': str(file_path),
                        'extension': extension,
                        'system': EMULATOR_CONFIGS[extension]['system'],
                        'filename': filename,
                        'launcher_found': bool(emulator_path),
                        'auto_configured': True # All dynamically found games are auto-configured
                    }
                    found_games.append(game_info)
                    log_message("DEBUG", f"Discovered game: {file_path.name} (Launcher found: {game_info['launcher_found']})")
        return found_games
    except Exception as e:
        log_message("ERROR", f"Error discovering games in {base_path}: {e}")
        return []

def detect_removable_drives():
    """
    Detects currently connected removable drives.
    Returns a list of Path objects for detected removable drives.
    Filters by minimum size to avoid very small system partitions or virtual drives.
    """
    removable_drives = []
    for partition in psutil.disk_partitions(all=False):
        try:
            # Check if the partition is a removable drive
            is_removable = False
            if platform.system() == "Windows":
                # psutil.disk_partitions provides 'opts' like 'rw,removable' or 'rw,fixed'
                if 'removable' in partition.opts:
                    is_removable = True
                # Sometimes optical drives show as removable, exclude them if preferred
                if 'cdrom' in partition.opts:
                    is_removable = False
            else: # Linux/macOS - relies more on mount point conventions and options
                # Look for common mount points for external devices
                if any(str(partition.mountpoint).startswith(p) for p in ['/media', '/mnt', '/Volumes']):
                    is_removable = True
                # Check for options that suggest removable media (e.g., 'rw' for writeable, 'nosuid' often for user mounts)
                if 'rw' in partition.opts and 'nosuid' in partition.opts: # Simple heuristic
                    is_removable = True

            if is_removable:
                drive_path = Path(partition.mountpoint)
                if drive_path.exists():
                    usage = psutil.disk_usage(str(drive_path))
                    if usage.total > (MIN_DRIVE_SIZE_MB * 1024 * 1024): # Check if total size is above threshold
                        removable_drives.append(drive_path)
                        log_message("DEBUG", f"Detected removable drive: {drive_path} (Total: {usage.total / (1024*1024*1024):.2f} GB)")
                    else:
                        log_message("DEBUG", f"Skipping small drive: {drive_path} (Size: {usage.total / (1024*1024):.2f} MB)")
                else:
                    log_message("DEBUG", f"Detected partition {partition.mountpoint} but path does not exist.")
        except Exception as e:
            log_message("ERROR", f"Error detecting drive {partition.mountpoint}: {e}")
            continue
    return list(set(removable_drives)) # Use set to remove duplicates if any

def update_game_lists():
    """
    Scans for local and cartridge games and updates the global game maps.
    This function is thread-safe and optimized with modification times.
    """
    global LOCAL_GAMES, CARTRIDGE_GAMES, CURRENT_GAME_MAP, LAST_SCAN_TIMES

    log_message("INFO", "Starting game list update.")

    # Scan local games
    local_mod_times = get_directory_modification_times(GAMES_DIRECTORY)
    if 'local_games' not in LAST_SCAN_TIMES or local_mod_times != LAST_SCAN_TIMES.get('local_games'):
        new_local_games = discover_games_in_path(GAMES_DIRECTORY)
        log_message("INFO", f"Local games rescanned. Found {len(new_local_games)} games.")
        LAST_SCAN_TIMES['local_games'] = local_mod_times
    else:
        new_local_games = LOCAL_GAMES # Use existing if no change detected
        log_message("DEBUG", "Local games directory unchanged, skipping rescan.")

    # Scan cartridge games
    new_cartridge_games = {}
    detected_drives = detect_removable_drives()
    current_connected_drive_ids = {str(d) for d in detected_drives}

    # First, handle drives that are no longer connected
    removed_drives = set(CARTRIDGE_GAMES.keys()) - current_connected_drive_ids
    for drive_id in removed_drives:
        log_message("INFO", f"Cartridge removed: {drive_id}")
        if drive_id in LAST_SCAN_TIMES:
            del LAST_SCAN_TIMES[drive_id] # Clear its last scan time

    for drive_path in detected_drives:
        drive_id = str(drive_path)
        
        current_mod_times = get_directory_modification_times(drive_path)
        
        # Only rescan if drive wasn't scanned recently or its content changed
        if drive_id not in LAST_SCAN_TIMES or current_mod_times != LAST_SCAN_TIMES.get(drive_id):
            log_message("INFO", f"Scanning new/changed cartridge: {drive_path}")
            print_formatted_text(HTML(f"<ansiyellow>Scanning cartridge: {drive_path}...</ansiyellow>"))
            new_cartridge_games[drive_id] = discover_games_in_path(drive_path)
            LAST_SCAN_TIMES[drive_id] = current_mod_times
        else:
            # If no change, retain previously scanned games for this drive if it's still connected
            if drive_id in CARTRIDGE_GAMES:
                new_cartridge_games[drive_id] = CARTRIDGE_GAMES[drive_id]
                log_message("DEBUG", f"Cartridge {drive_id} unchanged, skipping rescan.")
            else: # Fallback for newly connected drives that didn't immediately trigger a full scan
                 new_cartridge_games[drive_id] = discover_games_in_path(drive_path)
                 LAST_SCAN_TIMES[drive_id] = current_mod_times
                 log_message("INFO", f"New cartridge {drive_id} detected and scanned.")


    # Acquire lock before updating global state
    with SCAN_LOCK:
        LOCAL_GAMES = new_local_games
        CARTRIDGE_GAMES = new_cartridge_games

        # Clear and rebuild CURRENT_GAME_MAP
        CURRENT_GAME_MAP.clear()
        game_number = 1

        # Add local games to the map
        for game in LOCAL_GAMES:
            CURRENT_GAME_MAP[str(game_number)] = game['path']
            game_number += 1

        # Add cartridge games to the map, preserving order
        # Sort cartridge drives by path for consistent numbering
        sorted_cartridge_drives = sorted(CARTRIDGE_GAMES.keys())
        for drive_path_str in sorted_cartridge_drives:
            games_on_drive = CARTRIDGE_GAMES[drive_path_str]
            for game in games_on_drive:
                CURRENT_GAME_MAP[str(game_number)] = game['path']
                game_number += 1
    log_message("INFO", f"Game lists updated. Total games mapped: {len(CURRENT_GAME_MAP)}")
    # print_formatted_text(HTML("<ansigreen>Game lists updated.</ansigreen>")) # For debugging

def background_scan_thread():
    """Thread function to periodically scan for games."""
    log_message("INFO", "Background scan thread started.")
    while not SCAN_EVENT.is_set():
        update_game_lists()
        # Wait for the interval or until signaled to stop
        SCAN_EVENT.wait(SCAN_INTERVAL_SECONDS)
    log_message("INFO", "Background scan thread stopped.")

def start_background_scan():
    """Starts the background game scanning thread."""
    global SCAN_THREAD
    if SCAN_THREAD is None or not SCAN_THREAD.is_alive():
        SCAN_EVENT.clear()
        SCAN_THREAD = threading.Thread(target=background_scan_thread, daemon=True)
        SCAN_THREAD.start()
        log_message("INFO", "Background scan thread launched.")
        # print("Background scan thread started.") # For debugging

def stop_background_scan():
    """Stops the background game scanning thread."""
    global SCAN_THREAD
    if SCAN_THREAD and SCAN_THREAD.is_alive():
        log_message("INFO", "Signaling background scan thread to stop.")
        SCAN_EVENT.set()
        SCAN_THREAD.join(timeout=SCAN_INTERVAL_SECONDS + 5) # Give it time to finish
        if SCAN_THREAD.is_alive():
            log_message("WARNING", "Background scan thread did not stop gracefully.")
            print_formatted_text(HTML("<ansiyellow>Warning: Background scan thread did not stop gracefully.</ansiyellow>"))
        SCAN_THREAD = None
        log_message("INFO", "Background scan thread stopped successfully.")

def find_game_info_by_path(game_path):
    """Retrieves detailed game information by its path from the current game lists."""
    game_path_obj = Path(game_path)
    extension = game_path_obj.suffix.lower()
    
    # Check if the game is in LOCAL_GAMES
    for game in LOCAL_GAMES:
        if game['path'] == str(game_path_obj):
            game_source = "Local"
            config, emulator_path, is_retroarch = find_emulator_for_game(game_path_obj)
            game['source'] = game_source
            game['emulator_used'] = config['emulator_name'] if config else 'None'
            game['is_retroarch'] = is_retroarch
            return game
    
    # Check if the game is in CARTRIDGE_GAMES
    for drive_path_str, games_on_drive in CARTRIDGE_GAMES.items():
        for game in games_on_drive:
            if game['path'] == str(game_path_obj):
                game_source = f"Cartridge ({Path(drive_path_str).name or drive_path_str})"
                config, emulator_path, is_retroarch = find_emulator_for_game(game_path_obj)
                game['source'] = game_source
                game['emulator_used'] = config['emulator_name'] if config else 'None'
                game['is_retroarch'] = is_retroarch
                return game

    log_message("WARNING", f"Game information not found for path: {game_path}")
    return None # Game not found in current lists

# --- Display Functions (Enhanced UI) ---

def display_intro_splash():
    """Displays an elaborate intro splash screen."""
    clear_screen()
    play_sound("startup") # Using the new sound key
    intro_lines = [
        "<ansibrightmagenta>██████╗ ███████╗████████╗██████╗ ███████╗██████╗  █████╗ ██╗     ███████╗</ansibrightmagenta>",
        "<ansibrightmagenta>██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     ██╔════╝</ansibrightmagenta>",
        "<ansibrightmagenta>██████╔╝█████╗     ██║   ██████╔╝█████╗  ██████╔╝███████║██║     █████╗  </ansibrightmagenta>",
        "<ansibrightmagenta>██╔══██╗██╔══╝     ██║   ██╔══██╗██╔══╝  ██╔══██╗██╔══██║██║     ██╔══╝  </ansibrightmagenta>",
        "<ansibrightmagenta>██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║██║  ██║███████╗███████╗</ansibrightmagenta>",
        "<ansibrightmagenta>╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝</ansibrightmagenta>",
        "",
        "<ansibrightgreen>                A Dynamic, AI-Powered Retro Game Launcher</ansibrightgreen>",
        "<ansibrightyellow>                       Developed by Your AI Assistant</ansibrightyellow>",
        "",
        "<ansibrightcyan>         ----------------------------------------------------------</ansibrightcyan>",
        f"<ansibrightcyan>         Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<40}</ansibrightcyan>",
        "<ansibrightcyan>         ----------------------------------------------------------</ansibrightcyan>",
        "",
        "<ansigreen>Initializing system components...</ansigreen>",
        "<ansiyellow>Scanning for local games and removable cartridges in the background...</ansiyellow>",
        "<ansicyan>Please wait a moment...</ansicyan>",
        "",
        "<ansibrightwhite>Press any key to continue...</ansibrightwhite>"
    ]
    for line in intro_lines:
        print_formatted_text(HTML(line))
        time.sleep(0.1) # Dramatic pause

    # Wait for user input to clear the splash screen
    input("")
    clear_screen()
    log_message("INFO", "Intro splash screen displayed.")

def display_header(title):
    """Prints a formatted header for various sections."""
    clear_screen()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_lines = [
        "╔═══════════════════════════════════════════════════════════════════════════════╗",
        f"║ <ansibrightyellow>{title.upper().center(75)}</ansibrightyellow> ║",
        "╠═══════════════════════════════════════════════════════════════════════════════╣",
        f"║ <ansibrightcyan>CURRENT SYSTEM TIME:</ansibrightcyan> {current_time:<53} ║",
        "╚═══════════════════════════════════════════════════════════════════════════════╝"
    ]
    for line in header_lines:
        print_formatted_text(HTML(f"<ansibrightmagenta>{line}</ansibrightmagenta>")) # Use magenta for headers
    log_message("INFO", f"Displayed header: {title}")

def display_games_dos_style_dynamic():
    """
    Displays local and cartridge games in a DOS-like, numbered list.
    Includes an indicator if an emulator is missing, with enhanced styling.
    """
    display_header("RetroFlow Game List")
    play_sound("menu_select") # Using the new sound key

    num_local_games = len(LOCAL_GAMES)
    num_cartridge_games = sum(len(games) for games in CARTRIDGE_GAMES.values())

    # Local Games Section
    print_formatted_text(HTML("\n<ansibrightblue>██████████████████████ LOCAL GAMES ██████████████████████</ansibrightblue>"))
    if not LOCAL_GAMES:
        print_formatted_text(HTML("<ansiyellow>  No local games found in the 'Games' directory.</ansiyellow>"))
        print_formatted_text(HTML("<ansiyellow>  Make sure your ROMs are placed in:</ansiyellow>"))
        print_formatted_text(HTML(f"<ansiyellow>  {GAMES_DIRECTORY}</ansiyellow>"))
    else:
        print_formatted_text(HTML("<ansibrightyellow>  #   Game Title                                 System             Status       </ansibrightyellow>"))
        print_formatted_text(HTML("<ansibrightyellow>  --- ------------------------------------------ ------------------ ------------ </ansibrightyellow>"))
        idx = 0
        with SCAN_LOCK: # Acquire lock to read game lists safely
            for game in LOCAL_GAMES:
                idx += 1
                game_num = str(idx)
                status_text = "READY" if game['launcher_found'] else "NO LAUNCHER"
                status_color = "ansigreen" if game['launcher_found'] else "ansired"
                print_formatted_text(HTML(f"  <ansibrightcyan>{game_num:<3}</ansibrightcyan> <ansiblue>{game['name'][:42]:<42}</ansiblue> <ansimagenta>{game['system'][:18]:<18}</ansimagenta> <{status_color}>{status_text:<12}</{status_color}>"))

    # Cartridge Games Section
    print_formatted_text(HTML("\n<ansibrightblue>███████████████████ CARTRIDGE GAMES █████████████████████</ansibrightblue>"))
    if not CARTRIDGE_GAMES or num_cartridge_games == 0:
        print_formatted_text(HTML("<ansiyellow>  No cartridge games detected.</ansiyellow>"))
        print_formatted_text(HTML("<ansiyellow>  Insert a USB drive containing supported ROMs.</ansiyellow>"))
        print_formatted_text(HTML("<ansiyellow>  You can also type 'scan' to force a rescan.</ansiyellow>"))
    else:
        current_game_idx = len(LOCAL_GAMES) # Start numbering from after local games
        
        # Sort cartridge drives for consistent display order
        sorted_cartridge_drive_items = sorted(CARTRIDGE_GAMES.items())

        with SCAN_LOCK: # Acquire lock to read game lists safely
            for drive_path_str, games_on_drive in sorted_cartridge_drive_items:
                drive_name = Path(drive_path_str).name or drive_path_str # Use drive name or path
                print_formatted_text(HTML(f"\n<ansibrightyellow>  Drive: {drive_name} ({len(games_on_drive)} games found)</ansibrightyellow>"))
                if not games_on_drive:
                    print_formatted_text(HTML("<ansiyellow>    No supported games found on this cartridge.</ansiyellow>"))
                    continue

                print_formatted_text(HTML("<ansibrightyellow>    #   Game Title                                 System             Status       </ansibrightyellow>"))
                print_formatted_text(HTML("<ansibrightyellow>    --- ------------------------------------------ ------------------ ------------ </ansibrightyellow>"))
                for game in games_on_drive:
                    current_game_idx += 1
                    game_num = str(current_game_idx)
                    status_text = "READY" if game['launcher_found'] else "NO LAUNCHER"
                    status_color = "ansigreen" if game['launcher_found'] else "ansired"
                    print_formatted_text(HTML(f"    <ansibrightcyan>{game_num:<3}</ansibrightcyan> <ansiblue>{game['name'][:42]:<42}</ansiblue> <ansimagenta>{game['system'][:18]:<18}</ansimagenta> <{status_color}>{status_text:<12}</{status_color}>"))

    print_formatted_text(HTML("\n" + "═" * 80))
    print_formatted_text(HTML(f"<ansibrightwhite>Total Games Mapped: {len(CURRENT_GAME_MAP)}</ansibrightwhite>"))
    print_formatted_text(HTML("═" * 80))
    log_message("INFO", "Game list display updated.")

def display_help():
    """Displays available commands and their usage with enhanced styling."""
    display_header("Help - Available Commands")
    play_sound("menu_select") # Using the new sound key
    help_text = [
        ("list", "Display the list of local and cartridge games.", "Refreshes the game display."),
        ("play &lt;number&gt;", "Launch a game by its number.", "Example: play 5"),
        ("info &lt;number&gt;", "Show detailed information about a game.", "Example: info 12"),
        ("scan / cartridge / refresh", "Force an immediate scan for new/removed cartridge drives and games.", "Useful after inserting/removing a cartridge."),
        ("drives / cartridges", "List all currently detected cartridge drives and their status.", "Shows mount points and game counts."),
        ("ai &lt;prompt&gt;", "Ask the AI a question about games or general topics.", "Example: ai 'What is the best NES game?'"),
        ("apikey", "Set or update your Google Gemini API key.", "Required for AI features."),
        ("settings", "Display current application settings and configuration.", "Shows paths, scan intervals, etc."),
        ("log", "Display the last few entries from the application log.", "Useful for debugging issues."),
        ("clear / cls", "Clear the terminal screen.", "Clears the console output."),
        ("exit", "Exit the RetroFlow application.", "Safely shuts down the system."),
        ("help", "Display this help message.", "You are here!"),
    ]

    print_formatted_text(HTML("<ansibrightgreen>Command Reference:</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightyellow>  Command              Description                                      Usage Example</ansibrightyellow>"))
    print_formatted_text(HTML("<ansibrightyellow>  -------------------- ------------------------------------------------ ---------------------------------</ansibrightyellow>"))

    for cmd, desc, usage in help_text:
        print_formatted_text(HTML(f"  <ansibrightcyan>{cmd:<20}</ansibrightcyan> <ansicyan>{desc:<48}</ansicyan> <ansiblue>{usage}</ansiblue>"))
    print_formatted_text(HTML("\n<ansibrightwhite>Note: Game numbers change dynamically with cartridge insertions/removals and scans.</ansibrightwhite>"))
    print_formatted_text(HTML("═" * 80))
    log_message("INFO", "Help page displayed.")

def display_settings():
    """Displays current application settings with enhanced styling."""
    display_header("RetroFlow Application Settings")
    play_sound("menu_select") # Using the new sound key
    settings = [
        ("Project Root", PROJECT_ROOT),
        ("Games Directory", GAMES_DIRECTORY),
        ("Emulators Directory", EMULATORS_DIRECTORY),
        ("Cores Directory", CORES_DIRECTORY),
        ("Sounds Directory", SOUNDS_DIRECTORY),
        ("Config File", CONFIG_FILE),
        ("Log File", LOG_FILE),
        ("API Key Set", "Yes" if GEMINI_API_KEY else "No"),
        ("AI Model Initialized", "Yes" if GEN_MODEL else "No"),
        ("Background Scan Interval", f"{SCAN_INTERVAL_SECONDS} seconds"),
        ("Minimum Drive Size for Scan", f"{MIN_DRIVE_SIZE_MB} MB"),
        ("Background Scanner Status", "Running" if SCAN_THREAD and SCAN_THREAD.is_alive() else "Inactive"),
        (f"Local Games Detected", len(LOCAL_GAMES)),
        (f"Cartridge Drives Connected", len(CARTRIDGE_GAMES)),
        (f"Total Mapped Games", len(CURRENT_GAME_MAP)),
    ]

    print_formatted_text(HTML("<ansibrightgreen>Current Configuration:</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightyellow>  Setting                           Value</ansibrightyellow>"))
    print_formatted_text(HTML("<ansibrightyellow>  --------------------------------- ------------------------------------------------</ansibrightyellow>"))
    for setting, value in settings:
        print_formatted_text(HTML(f"  <ansibrightcyan>{setting:<33}</ansibrightcyan> <ansicyan>{str(value)}</ansicyan>"))
    
    print_formatted_text(HTML("\n<ansibrightgreen>Emulator Configurations (Extensions & Systems):</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightyellow>  Extension   System             Primary Emulator</ansibrightyellow>"))
    print_formatted_text(HTML("<ansibrightyellow>  ----------- ------------------ ---------------------------------</ansibrightyellow>"))
    for ext, config in EMULATOR_CONFIGS.items():
        primary_emulator = config.get('emulator_name', 'N/A')
        print_formatted_text(HTML(f"  <ansibrightcyan>{ext:<11}</ansibrightcyan> <ansimagenta>{config['system'][:18]:<18}</ansimagenta> <ansiblue>{primary_emulator}</ansiblue>"))

    print_formatted_text(HTML("═" * 80))
    log_message("INFO", "Settings page displayed.")

def display_log(num_lines=20):
    """Displays the last few entries from the log file."""
    display_header("RetroFlow Log - Recent Entries")
    play_sound("menu_select") # Using the new sound key
    try:
        if not LOG_FILE.exists():
            print_formatted_text(HTML("<ansiyellow>Log file not found. No entries to display.</ansiyellow>"))
            log_message("WARNING", "Attempted to display log, but file does not exist.")
            return

        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                print_formatted_text(HTML("<ansiyellow>Log file is empty.</ansiyellow>"))
                return
            
            print_formatted_text(HTML("<ansibrightyellow>  Timestamp               Level   Message</ansibrightyellow>"))
            print_formatted_text(HTML("<ansibrightyellow>  ----------------------- ------- ------------------------------------------------</ansibrightyellow>"))
            import re # Ensure re is imported for regex operations
            for line in lines[-num_lines:]: # Display last num_lines
                line = line.strip()
                match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([A-Z]+)\] (.*)$', line)
                if match:
                    timestamp, level, message = match.groups()
                    level_color = {
                        'INFO': 'ansigreen',
                        'WARNING': 'ansiyellow',
                        'ERROR': 'ansired',
                        'DEBUG': 'ansiblue',
                        'CRITICAL': 'ansired' # Added CRITICAL for consistency
                    }.get(level, 'ansicyan')
                    print_formatted_text(HTML(f"  <ansicyan>{timestamp}</ansicyan> <{level_color}>{level:<7}</{level_color}> <ansibrightwhite>{html.escape(message)}</ansibrightwhite>")) # HTML escape message
                else:
                    print_formatted_text(HTML(f"  <ansigray>{html.escape(line)}</ansigray>")) # Fallback for malformed lines
        log_message("INFO", f"Displayed last {num_lines} log entries.")
    except Exception as e:
        print_formatted_text(HTML(f"<ansired>Error reading log file: {e}</ansired>"))
        log_message("ERROR", f"Error displaying log: {e}")
    print_formatted_text(HTML("═" * 80))


# --- Core Logic Functions ---

def launch_game_universal(game_path):
    """
    Launches a game using the determined emulator or RetroArch.
    Handles different operating systems.
    """
    game_path_obj = Path(game_path)
    emulator_config, emulator_path, is_retroarch_launch = find_emulator_for_game(game_path_obj)

    if not emulator_path:
        print_formatted_text(HTML(f"<ansired>Error: No suitable emulator found for '{html.escape(game_path_obj.name)}'.</ansired>"))
        play_sound("error") # Using the new sound key
        log_message("ERROR", f"No suitable emulator found for {game_path_obj.name}")
        return

    command = ""
    try:
        # Construct the command based on the launch template
        template = emulator_config['launch_template']
        command = template.format(emulator_path=emulator_path, game_path=str(game_path_obj))
        
        log_message("INFO", f"Attempting to launch game: {game_path_obj.name} with command: {command}")
        print_formatted_text(HTML(f"Launching {emulator_config['emulator_name']}: {html.escape(game_path_obj.name)}"))
        if platform.system() == "Windows":
            subprocess.Popen(command, shell=True)
        else:
            subprocess.Popen(command, shell=True)
        
        play_sound("launch_game") # Using the new sound key for game launch
        # Give the emulator a moment to launch before clearing
        time.sleep(1)
        clear_screen() # Clear after launching for a cleaner look
        log_message("INFO", f"Successfully launched {game_path_obj.name}.")
    except FileNotFoundError:
        print_formatted_text(HTML(f"<ansired>Error: Launcher executable not found.</ansired>"))
        print_formatted_text(HTML(f"<ansired>Please check if '{Path(emulator_path).name}' exists in '{EMULATORS_DIRECTORY}'.</ansired>"))
        play_sound("error") # Using the new sound key
        log_message("ERROR", f"Launcher not found for {game_path_obj.name}: {emulator_path}")
    except Exception as e:
        print_formatted_text(HTML(f"<ansired>Error launching game: {e}</ansired>"))
        print_formatted_text(HTML(f"Command attempted: {html.escape(command)}"))

        play_sound("error") # Using the new sound key
        log_message("ERROR", f"General error launching {game_path_obj.name}: {e} (Command: {command})")

def set_api_key_command():
    """Allows the user to set or update the Gemini API key."""
    global GEMINI_API_KEY
    print_formatted_text(HTML("<ansiyellow>Enter your Google Gemini API Key (or 'cancel' to abort):</ansiyellow>"))
    log_message("INFO", "Prompting user for Gemini API key.")
    try:
        new_key = input("API Key: ").strip()
        if new_key.lower() == 'cancel':
            print_formatted_text(HTML("<ansiyellow>API Key setup cancelled.</ansiyellow>"))
            play_sound("error") # Using the new sound key
            log_message("INFO", "Gemini API key setup cancelled by user.")
            return
        if new_key:
            GEMINI_API_KEY = new_key
            save_config()
            configure_gemini_api(GEMINI_API_KEY)
            log_message("INFO", "Gemini API key updated.")
        else:
            print_formatted_text(HTML("<ansired>API Key cannot be empty.</ansired>"))
            play_sound("error") # Using the new sound key
            log_message("WARNING", "Attempted to set empty Gemini API key.")
    except Exception as e:
        print_formatted_text(HTML(f"<ansired>Error setting API key: {e}</ansired>"))
        play_sound("error") # Using the new sound key
        log_message("ERROR", f"Error during API key setup: {e}")

async def ask_gemini_command(prompt_text):
    """Sends a prompt to Google Gemini and prints the response."""
    if not GEN_MODEL:
        print_formatted_text(HTML("<ansired>AI not configured. Please set your Gemini API key using the 'apikey' command.</ansired>"))
        play_sound("error") # Using the new sound key
        log_message("WARNING", "AI command attempted but Gemini model not configured.")
        return

    print_formatted_text(HTML("<ansibrightcyan>Asking Gemini...</ansibrightcyan>"))
    play_sound("flowey_chat_enter") # Using the new sound key
    log_message("INFO", f"Sending prompt to Gemini: '{prompt_text[:50]}...'")
    try:
        # Initialize chat with the system instruction for Flowey's personality
        initial_history = [
            {'role': 'user', 'parts': [FLOWEY_SYSTEM_INSTRUCTION]},
            {'role': 'model', 'parts': ["Howdy! Let's talk about some good old games. What's on your mind?"]} 
        ]
        chat = GEN_MODEL.start_chat(history=initial_history)
        
        # Send the actual user prompt
        response = chat.send_message(prompt_text)

        print_formatted_text(HTML(f"<ansigreen>Gemini:</ansigreen> <ansiblue>{html.escape(response.text)}</ansiblue>"))
        play_sound("menu_select") # Using the new sound key
        log_message("INFO", f"Gemini response received: '{response.text[:50]}...'")
    except Exception as e:
        print_formatted_text(HTML(f"<ansired>Error communicating with Gemini: {e}</ansired>"))
        print_formatted_text(HTML("<ansiyellow>Please check your API key and network connection.</ansiyellow>"))
        play_sound("error") # Using the new sound key
        log_message("ERROR", f"Error communicating with Gemini: {e}")

# --- Main Application Flow ---

def initialize_directories():
    """Ensures all necessary directories exist and logs missing expected sound files."""
    required_dirs = [GAMES_DIRECTORY, EMULATORS_DIRECTORY, CORES_DIRECTORY, SOUNDS_DIRECTORY]
    for d in required_dirs:
        d.mkdir(parents=True, exist_ok=True)
        log_message("INFO", f"Ensured directory exists: {d}")
    
    # Check for existence of each sound file listed in SOUND_FILES
    for sound_key, sound_filename in SOUND_FILES.items():
        sound_path = SOUNDS_DIRECTORY / sound_filename
        if not sound_path.exists():
            log_message("WARNING", f"Missing expected sound file for '{sound_key}': '{sound_path}'. Please ensure it exists for full experience.")

def create_command_completer():
    """Creates a completer for prompt_toolkit commands."""
    commands = [
        "list", "play", "info", "scan", "cartridge", "drives", "cartridges",
        "ai", "apikey", "clear", "cls", "exit", "help", "settings", "refresh", "log"
    ]
    # Add game numbers dynamically to completer for 'play' and 'info'
    # This might make the completer slow with thousands of games, but okay for moderate numbers.
    with SCAN_LOCK: # Acquire lock before accessing CURRENT_GAME_MAP
        game_numbers = list(CURRENT_GAME_MAP.keys())
    return WordCompleter(commands + game_numbers, ignore_case=True)

def main():
    """Main function to run the RetroFlow terminal."""
    initialize_directories()
    load_config() # Load API key and configure Gemini if present

    # Initialize pygame mixer for sound playback
    try:
        mixer.init()
        log_message("INFO", "Pygame mixer initialized.")
    except Exception as e:
        print_formatted_text(HTML(f"<ansiyellow>Warning: Could not initialize sound system: {e}</ansiyellow>"))
        log_message("ERROR", f"Could not initialize pygame mixer: {e}")

    display_intro_splash() # Show the fancy intro

    # Initial scan before starting the main loop
    update_game_lists()
    start_background_scan() # Start the background scanning thread

    # Define prompt_toolkit styles
    cli_style = Style.from_dict({
        '': 'green',  # Default text color (using basic green)
        'prompt': 'blue bold', # For the prompt itself (blue and bold)
        'info': 'cyan',
        'error': 'red bold',
        'warning': 'yellow',
        'header': 'magenta bold', # Make headers bold for "bright" effect
        'sub_header': 'blue',
        'game_num': 'cyan',
        'game_title': 'blue',
        'game_system': 'magenta',
        'status_ok': 'green',
        'status_warn': 'yellow',
        'status_error': 'red',
        'separator': 'gray',
        'footer': 'white bold', # Make footer bold for "bright" effect
        'input_text': 'white',
    })

    session = PromptSession(completer=create_command_completer(), style=cli_style)

    clear_screen()
    print_formatted_text(HTML("<ansibrightgreen>========================================</ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightgreen>  Welcome to Dynamic RetroFlow Terminal!  </ansibrightgreen>"))
    print_formatted_text(HTML("<ansibrightgreen>========================================</ansibrightgreen>"))
    print_formatted_text(HTML("<ansicyan>Type 'help' for available commands.</ansicyan>"))
    print_formatted_text(HTML("<ansiyellow>Scanning for games and cartridges in the background...</ansiyellow>"))
    log_message("INFO", "RetroFlow application started.")
    time.sleep(2) # Give a moment for initial messages

    try:
        while True:
            # Re-create completer in loop to update game numbers dynamically
            session.completer = create_command_completer() 
            try:
                command_line = session.prompt(HTML("\n<prompt>C:\\RETROFLOW> </prompt>")).strip().lower()
            except EOFError: # Ctrl+D to exit
                print_formatted_text(HTML("\n<ansibrightcyan>Ctrl+D detected. Exiting...</ansibrightcyan>"))
                break
            except KeyboardInterrupt: # Ctrl+C to exit (more common)
                print_formatted_text(HTML("\n<ansibrightcyan>KeyboardInterrupt detected. Exiting...</ansibrightcyan>"))
                break
            
            if not command_line:
                continue

            # Robust command parsing using regex
            import re # Ensure re is imported for regex operations
            parts = re.split(r'\s+', command_line, 1) # Split only on first space
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if command == 'exit':
                print_formatted_text(HTML("<ansibrightcyan>Goodbye! Thanks for using Dynamic RetroFlow!</ansibbrightcyan>"))
                play_sound("menu_select") # Using the new sound key
                log_message("INFO", "User exited application.")
                break
            elif command == 'help':
                display_help()
            elif command == 'list':
                display_games_dos_style_dynamic()
            elif command == 'list':
                # 'list' command just re-triggers the display, which happens automatically
                # but it's good to keep it for explicit user action to refresh the view.
                pass # The while loop will call display_games_dos_style_dynamic()
            elif command == 'play':
                if args:
                    game_num_str = args
                    with SCAN_LOCK: # Acquire lock to read game lists
                        game_path = CURRENT_GAME_MAP.get(game_num_str)
                    
                    if game_path:
                        running_game_name = Path(game_path).name
                        print_formatted_text(HTML(f"<ansibrightgreen>Attempting to launch {html.escape(running_game_name)}...</ansibrightgreen>"))
                        
                        launch_game_universal(game_path)
                    else:
                        print_formatted_text(HTML(f"<ansired>Error: Invalid game number '{game_num_str}'. Please check the list.</ansired>"))
                        play_sound("error") # Using the new sound key
                        log_message("WARNING", f"Invalid game number entered for play: {game_num_str}")
                else:
                    print_formatted_text(HTML("<ansired>Usage: play &lt;game_number&gt;</ansired>"))
                    play_sound("error") # Using the new sound key
                    log_message("WARNING", "Play command used without arguments.")
            elif command == 'info':
                if args:
                    game_num_str = args
                    with SCAN_LOCK: # Acquire lock to read game lists
                        game_path = CURRENT_GAME_MAP.get(game_num_str)

                    if game_path:
                        game_info = find_game_info_by_path(game_path)
                        if game_info:
                            display_header("Game Information")
                            play_sound("menu_select") # Using the new sound key
                            info_lines = [
                                "╔═══════════════════════════════════════════════════════════════════════════════╗",
                                f"║ <ansibrightgreen>Game Name:</ansibrightgreen>      {game_info['name'][:59]:<59} ║",
                                f"║ <ansibrightgreen>System:</ansibrightgreen>         {game_info['system'][:59]:<59} ║",
                                f"║ <ansibrightgreen>Source:</ansibrightgreen>         {game_info['source'][:59]:<59} ║",
                                f"║ <ansibrightgreen>Path:</ansibrightgreen>           {html.escape(game_info['path'])[:59]:<59} ║", # Truncate long paths
                                f"║ <ansibrightgreen>Extension:</ansibrightgreen>      {game_info['extension'][:59]:<59} ║",
                                f"║ <ansibrightgreen>Filename:</ansibrightgreen>       {game_info['filename'][:59]:<59} ║",
                                f"║ <ansibrightgreen>Launcher Found:</ansibrightgreen> {'Yes' if game_info['launcher_found'] else 'No':<59} ║",
                                f"║ <ansibrightgreen>Emulator Used:</ansibrightgreen>  {game_info['emulator_used'][:59]:<59} ║",
                                f"║ <ansibrightgreen>Is RetroArch:</ansibrightgreen>   {'Yes' if game_info['is_retroarch'] else 'No':<59} ║",
                                f"║ <ansibrightgreen>Auto-Configured:</ansibrightgreen>{'Yes' if game_info['auto_configured'] else 'No':<59} ║",
                                "╚═══════════════════════════════════════════════════════════════════════════════╝"
                            ]
                            for line in info_lines:
                                print_formatted_text(HTML(f"<ansibrightcyan>{line}</ansibrightcyan>")) # html.escape is already applied in the f-strings
                            
                            print_formatted_text(HTML("═" * 80))
                            log_message("INFO", f"Displayed info for game: {game_info['name']}")
                        else:
                            print_formatted_text(HTML(f"<ansired>Error: Could not retrieve info for game '{game_num_str}'.</ansired>"))
                            play_sound("error") # Using the new sound key
                            log_message("ERROR", f"Could not find full info for game number: {game_num_str}")
                    else:
                        print_formatted_text(HTML(f"<ansired>Error: Game '{game_num_str}' not found in the current mapping.</ansired>"))
                        play_sound("error") # Using the new sound key
                        log_message("WARNING", f"Info command: Game number {game_num_str} not in map.")
                else:
                    print_formatted_text(HTML("<ansired>Usage: info &lt;game_number&gt;</ansired>"))
                    play_sound("error") # Using the new sound key
                    log_message("WARNING", "Info command used without arguments.")
            elif command in ['scan', 'cartridge', 'refresh']:
                print_formatted_text(HTML("<ansibrightyellow>Forcing game and cartridge scan...</ansibrightyellow>"))
                update_game_lists() # Manual trigger for immediate update
                display_games_dos_style_dynamic() # Refresh display immediately
                print_formatted_text(HTML("<ansibrightgreen>Scan complete.</ansibrightgreen>"))
                play_sound("menu_select") # Using the new sound key
                log_message("INFO", "Manual scan completed.")
            elif command in ['drives', 'cartridges']:
                display_header("Detected Cartridge Drives")
                play_sound("menu_select") # Using the new sound key
                detected_drives_list = detect_removable_drives()
                if not detected_drives_list:
                    print_formatted_text(HTML("<ansiyellow>No removable drives detected.</ansiyellow>"))
                    log_message("INFO", "No removable drives detected.")
                else:
                    print_formatted_text(HTML("<ansibrightyellow>  Mount Point                  Games Found   Total Size   Free Space</ansibrightyellow>"))
                    print_formatted_text(HTML("<ansibrightyellow>  ---------------------------- ------------- ------------ ------------</ansibrightyellow>"))
                    for drive_path in detected_drives_list:
                        try:
                            num_games = len(CARTRIDGE_GAMES.get(str(drive_path), []))
                            usage = psutil.disk_usage(str(drive_path))
                            total_gb = usage.total / (1024**3)
                            free_gb = usage.free / (1024**3)
                            print_formatted_text(HTML(f"  <ansibrightcyan>{str(drive_path)[:28]:<28}</ansibrightcyan> <ansigreen>{num_games:<13}</ansigreen> <ansimagenta>{total_gb:<10.2f} GB</ansimagenta> <ansiblue>{free_gb:<10.2f} GB</ansiblue>"))
                            log_message("INFO", f"Drive detected: {drive_path} - Games: {num_games}, Total: {total_gb:.2f}GB, Free: {free_gb:.2f}GB")
                        except Exception as e:
                            print_formatted_text(HTML(f"  <ansired>{str(drive_path)[:28]:<28}</ansired> <ansired>ERROR: {e}</ansired>"))
                            log_message("ERROR", f"Error displaying drive info for {drive_path}: {e}")
                print_formatted_text(HTML("═" * 80))
            elif command == 'ai':
                if args:
                    # AI commands are async, need to run them
                    import asyncio
                    asyncio.run(ask_gemini_command(args))
                else:
                    print_formatted_text(HTML("<ansired>Usage: ai &lt;your_question&gt;</ansired>"))
                    play_sound("error") # Using the new sound key
                    log_message("WARNING", "AI command used without arguments.")
            elif command == 'apikey':
                set_api_key_command()
            elif command in ['clear', 'cls']:
                clear_screen()
                log_message("INFO", "Screen cleared by user command.")
            elif command == 'settings':
                display_settings()
            elif command == 'log':
                display_log()
            else:
                print_formatted_text(HTML(f"<ansired>Unknown command: '{command}'. Type 'help' for available commands.</ansired>"))
                play_sound("error") # Using the new sound key
                log_message("WARNING", f"Unknown command entered: {command}")
        
    except (KeyboardInterrupt, EOFError):
        print_formatted_text(HTML("\n<ansibrightcyan>Application interrupted. Shutting down...</ansibrightcyan>"))
        play_sound("menu_select") # Using the new sound key
        log_message("INFO", "Application interrupted (Ctrl+C/Ctrl+D).")
    except Exception as e:
        clear_screen()
        print_formatted_text(HTML(f"<ansired>A FATAL SYSTEM ERROR OCCURRED:</ansired>"))
        print_formatted_text(HTML(f"<ansired>{html.escape(traceback.format_exc())}</ansired>"))
        play_sound("error") # Using the new sound key
        log_message("CRITICAL", f"Fatal unhandled exception: {traceback.format_exc()}")
    finally:
        stop_background_scan() # Ensure background thread is stopped on exit
        try:
            mixer.quit() # Quit pygame mixer
            log_message("INFO", "Pygame mixer quit.")
        except Exception as e:
            log_message("WARNING", f"Error quitting pygame mixer: {e}")
        log_message("INFO", "RetroFlow application terminated.")
        sys.exit(0)

if __name__ == "__main__":
    main()