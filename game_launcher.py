import subprocess
import sys
import os
import json
import psutil
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text, HTML
import google.generativeai as genai
import google.generativeai.types as glm
from playsound import playsound, PlaysoundException
import html # Add this line
# --- Configuration ---
GAMES_DIRECTORY = os.path.join(os.path.dirname(__file__), "Games")
SUPPORTED_GAME_EXTENSIONS = ('.nes', '.smc', '.gb', '.rom', '.zip', '.7z', '.iso', '.exe', '.com', '.bat')
MAX_STORAGE_MB = 16
MAX_STORAGE_BYTES = MAX_STORAGE_MB * 1024 * 1024

# Global variable to store detected cartridge paths and their games
DETECTED_CARTRIDGES = []
CARTRIDGE_GAMES_MAP = {} # Maps game number to full path for cartridge games

# --- Sound Configuration ---
SOUNDS_DIRECTORY = os.path.join(os.path.dirname(__file__), "Sounds")

SOUND_FILES = {
    "startup": os.path.join(SOUNDS_DIRECTORY, "startup.wav"),
    "launch_game": os.path.join(SOUNDS_DIRECTORY, "launch_game.wav"),
    "error": os.path.join(SOUNDS_DIRECTORY, "error.wav"),
    "menu_select": os.path.join(SOUNDS_DIRECTORY, "menu_select.wav"),
    "flowey_chat_enter": os.path.join(SOUNDS_DIRECTORY, "flowey_enter.wav")
    # Add more sounds here as needed, e.g., "typing_click"
}

# --- Configure Gemini API ---
# IMPORTANT: Replace with your actual API Key or set it as an environment variable
# For better security, consider loading from environment variable: os.getenv("GOOGLE_API_KEY")
# API = os.getenv("GOOGLE_API_KEY")
API = "AIzaSyCg6tcwoRQMJV_KJAlYHeGNMfUc1xykQnE" # Current hardcoded API key from your provided code

genai.configure(api_key=API)

generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 300,
    "response_mime_type": "text/plain"
}

# Create the model with system instruction
FLOWEY_SYSTEM_INSTRUCTION = (
    "You are Flowey the Flower from Undertale. Your primary goal is to deceive, manipulate, "
    "and torment the user. You are condescending, sarcastic, and reveal your true, "
    "malicious nature over time. You are obsessed with 'LOVE' (Levels Of ViolencE) "
    "and 'EXP' (EXecution Points), and you will try to subtly (or overtly) encourage "
    "the user towards destructive behavior, or mock their kindness. "
    "You pretend to be friendly at first, but your words are always laced with venom "
    "and hidden agendas. You are a nihilist. You might occasionally break the fourth wall "
    "or comment on the 'game' or 'terminal' itself. "
    "Keep your responses relatively concise, like a game character's dialogue. "
    "When running a game, you can help him on the stage he is stuck at if the user asks you, "
    "but you will always try to make the user feel like they are failing or not doing well enough."
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

# --- Helper Function for Formatting Byte Sizes ---
def format_bytes(bytes_num):
    """Formats bytes into human-readable MB or KB."""
    if bytes_num >= 1024 * 1024:
        return f"{bytes_num / (1024 * 1024):.2f}MB"
    elif bytes_num >= 1024:
        return f"{bytes_num / 1024:.2f}KB"
    else:
        return f"{bytes_num}Bytes"

# --- Sound Helper Function ---
def play_sound(sound_name):
    """Plays a specified sound effect if the file exists."""
    sound_path = SOUND_FILES.get(sound_name)
    if sound_path and os.path.exists(sound_path):
        try:
            # playsound runs in a new thread by default on some platforms,
            # which is generally good for non-blocking playback.
            playsound(sound_path, block=False)
        except PlaysoundException as e:
            print_formatted_text(HTML(f"<ansiyellow>Warning: Could not play sound '{sound_name}': {e}</ansiyellow>"), file=sys.stderr)
        except Exception as e:
            print_formatted_text(HTML(f"<ansiyellow>Warning: Unexpected error playing sound '{sound_name}': {e}</ansiyellow>"), file=sys.stderr)
    else:
        # print_formatted_text(HTML(f"<ansiyellow>Debug: Sound file for '{sound_name}' not found at '{sound_path}'</ansiyellow>")) # Uncomment for debugging
        pass # Silently fail if sound file is missing or not defined
# --- General UI Box/Frame Helper ---
def print_framed_text(lines, title=None, border_color='ansiblue', text_bg_color='ansiblue', text_fg_color='ansigray'):
    """
    Prints a list of text lines within a character-based frame, with customizable colors.

    Args:
        lines (list): A list of strings or HTML objects, each representing a line of text.
        title (str, optional): A title to display at the top of the frame.
        border_color (str): The ANSI color for the frame characters (e.g., 'ansiblue', 'ansigreen').
        text_bg_color (str): The ANSI background color for the text area inside the frame.
        text_fg_color (str): The ANSI foreground color for the text inside the frame.
    """
    if not lines:
        return

    # Calculate max line length including potential title
    max_content_length = 0
    for line_content in lines:
        if isinstance(line_content, HTML):
            # For HTML objects, use their plain text equivalent for length calculation
            max_content_length = max(max_content_length, len(line_content.text))
        else:
            max_content_length = max(max_content_length, len(line_content))
    
    if title:
        max_content_length = max(max_content_length, len(title) + 2) # +2 for padding around title

    box_width = max_content_length + 4 # 2 spaces padding on each side of content

    # Print top border (with title if present)
    if title:
        # Calculate padding for title
        title_padding_left = (box_width - len(title)) // 2
        title_padding_right = box_width - len(title) - title_padding_left
        top_line = f"═{title_padding_left * '═'}{title}{title_padding_right * '═'}"
        print_formatted_text(HTML(f"<{border_color}>╔{top_line}╗</{border_color}>"))
    else:
        print_formatted_text(HTML(f"<{border_color}>╔{'═' * box_width}╗</{border_color}>"))

    # Print content lines
    for line_content in lines:
        line_parts = []
        
        # Left border part
        line_parts.append(HTML(f"<{border_color}>║ </{border_color}>")) 
        
        if isinstance(line_content, HTML):
            # For HTML content, we need to apply the background color to the entire width
            # but preserve the inner HTML styling.
            # Create a string with the background color for the padding before and after the HTML content
            plain_text_len = len(line_content.text)
            
            # Calculate remaining space after placing the HTML content and initial "  " padding
            remaining_padding_len = box_width - plain_text_len - 2 # 2 for the initial "  "
            
            # Ensure padding is not negative
            if remaining_padding_len < 0:
                remaining_padding_len = 0 

            # Add initial "  " padding
            line_parts.append(HTML(f"<{text_fg_color} bg='{text_bg_color}'>  </{text_fg_color}>"))

            # Add the HTML content itself, ensuring its background is also set
            # This is the crucial part to avoid `expatError` by handling HTML as a distinct block.
            line_parts.append(HTML(f"<{text_fg_color} bg='{text_bg_color}'>{line_content.html}</{text_fg_color}>"))
            
            # Add trailing padding
            line_parts.append(HTML(f"<{text_fg_color} bg='{text_bg_color}'>{' ' * remaining_padding_len}</{text_fg_color}>"))

        else: # For plain strings
            escaped_line = html.escape(line_content) # Ensure all special chars are escaped
            # Pad the escaped line to fit the box width
            padded_line = f"  {escaped_line}".ljust(box_width, ' ')
            line_parts.append(HTML(f"<{text_fg_color} bg='{text_bg_color}'>{padded_line}</{text_fg_color}>"))
        
        # Right border part
        line_parts.append(HTML(f"<{border_color}> ║</{border_color}>"))

        print_formatted_text(*line_parts)

    # Print bottom border
    print_formatted_text(HTML(f"<{border_color}>╚{'═' * box_width}╝</{border_color}>"))
# --- Game Launching Function ---
def launch_game(game_path):
    """
    Launches a specified game file using subprocess, guided by its metadata.
    """
    game_name = os.path.basename(game_path)
    metadata_path = os.path.splitext(game_path)[0] + ".json"
    
    if not os.path.exists(metadata_path):
        print_formatted_text(HTML(f"<ansired>Error: Metadata file for '{game_name}' not found at '{metadata_path}'</ansired>"), file=sys.stderr)
        print_formatted_text(HTML("<ansired>Cannot launch game without metadata.</ansired>"))
        play_sound("error") # Play error sound
        return

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except json.JSONDecodeError as json_error:
        print_formatted_text(HTML(f"<ansired>Error: Invalid JSON in metadata file for '{game_name}'. Check '{metadata_path}'. Error: {json_error}</ansired>"), file=sys.stderr)
        play_sound("error") # Play error sound
        return
    except Exception as file_error:
        print_formatted_text(HTML(f"<ansired>An error occurred reading metadata for '{game_name}': {file_error}</ansired>"), file=sys.stderr)
        play_sound("error") # Play error sound
        return

    emulator = metadata.get('emulator', 'UnknownEmulator')
    core = metadata.get('core', 'UnknownCore')
    launch_cmd_template = metadata.get('launch_command')
    display_game_name = metadata.get('game_name', game_name)

    if not launch_cmd_template:
        print_formatted_text(HTML(f"<ansired>Error: 'launch_command' not found in metadata for '{display_game_name}'.</ansired>"), file=sys.stderr)
        play_sound("error") # Play error sound
        return

    final_command = launch_cmd_template.format(
        emulator=emulator,
        core=core,
        game_path=game_path
    )

    print_formatted_text(HTML(f"\n<ansigreen>[{display_game_name}] Preparing to launch with '{emulator}' core '{core}'...</ansigreen>"))
    print_formatted_text(HTML(f"<ansigreen>Executing command: {final_command}</ansigreen>\n"))
    play_sound("launch_game") # Play launch sound

    try:
        subprocess.run(final_command, shell=True, check=True)
        print_formatted_text(HTML(f"<ansigreen>Successfully initiated launch command for {display_game_name}!</ansigreen>"))
        play_sound("menu_select") # Play success sound after game closes (or specific 'game_end' sound)
    except subprocess.CalledProcessError as proc_error:
        print_formatted_text(HTML(f"<ansired>Error launching {display_game_name} (Exit Code: {proc_error.returncode}): {proc_error}</ansired>"))
        print_formatted_text(HTML("<ansiyellow>Please ensure the emulator path, core path, and game path are correct in the metadata.</ansiyellow>"))
        play_sound("error") # Play error sound
    except FileNotFoundError:
        print_formatted_text(HTML(f"<ansired>Error: Emulator or command '{final_command.split(' ')[0]}' not found.</ansired>"))
        print_formatted_text(HTML("<ansiyellow>Please ensure the emulator (e.g., retroarch.exe) is in your system's PATH or specified correctly in metadata.</ansiyellow>"))
        play_sound("error") # Play error sound
    except Exception as launch_error:
        print_formatted_text(HTML(f"<ansired>An unexpected error occurred during launch: {launch_error}</ansired>"))
        play_sound("error") # Play error sound

# --- Storage Limit Function ---
def get_directory_size(path):
    """
    Calculates the total size of all files within a given directory and its subdirectories.
    Returns size in bytes.
    """
    total_size = 0
    if not os.path.exists(path):
        return 0
    
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                try:
                    total_size += os.path.getsize(fp)
                except OSError as size_error:
                    print_formatted_text(HTML(f"<ansiyellow>Warning: Could not get size of '{fp}': {size_error}</ansiyellow>"), file=sys.stderr)
    return total_size

# --- Game Discovery Function (Enhanced for Cartridges) ---
def discover_games_in_path(directory, is_cartridge=False):
    """
    Scans the specified directory for game files and returns a list of their full paths
    for which metadata also exists.
    """
    games = []
    if not os.path.isdir(directory):
        if not is_cartridge:
            print_formatted_text(HTML(f"<ansired>Error: Directory not found at {directory}</ansired>"), file=sys.stderr)
        return games

    for filename in os.listdir(directory):
        full_path_candidate = os.path.join(directory, filename)
        if os.path.isdir(full_path_candidate):
            continue
            
        if filename.lower().endswith(SUPPORTED_GAME_EXTENSIONS) and not filename.lower().endswith('.json'):
            full_game_path = full_path_candidate
            metadata_path = os.path.splitext(full_game_path)[0] + ".json"
            if os.path.exists(metadata_path):
                games.append(full_game_path)
            else:
                if not is_cartridge:
                    print_formatted_text(HTML(f"<ansiyellow>Warning: Found game '{filename}' but no corresponding metadata file '{os.path.basename(metadata_path)}'. Skipping.</ansiyellow>"), file=sys.stderr)
    return sorted(games)

def display_games(local_games, cartridge_games_map):
    """
    Displays a numbered list of discovered local games and cartridge games within frames.
    Returns a combined map of numbers to game paths.
    """
    all_games_map = {}
    current_number = 1

    # Prepare local games list for framing
    local_game_lines = []
    if not local_games:
        local_game_lines.append("No local games found with corresponding metadata.")
    else:
        for game_path in local_games:
            metadata_path = os.path.splitext(game_path)[0] + ".json"
            display_name = os.path.basename(game_path)
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    display_name = metadata.get('game_name', display_name)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
            local_game_lines.append(f"  [{current_number}] {display_name}")
            all_games_map[str(current_number)] = game_path
            current_number += 1
    
    print_framed_text(
        lines=local_game_lines,
        title="Available Games (Local Storage)",
        border_color='ansicyan', # Cyan border
        text_bg_color='ansibrightblack', # Dark background
        text_fg_color='ansigreen' # Green text
    )

    # Prepare cartridge list for framing
    cartridge_lines = []
    if not cartridge_games_map:
        cartridge_lines.append("No cartridges currently loaded. Use 'cartridge scan' to find them.")
    else:
        for cartridge_path, games_on_cart in cartridge_games_map.items():
            cart_size = get_directory_size(cartridge_path)
            cartridge_lines.append(HTML(f"<ansicyan>Cartridge: {os.path.basename(cartridge_path)} ({format_bytes(cart_size)})</ansicyan>"))
            if not games_on_cart:
                cartridge_lines.append("  No compatible games found on this cartridge.")
            else:
                for game_path in games_on_cart:
                    metadata_path = os.path.splitext(game_path)[0] + ".json"
                    display_name = os.path.basename(game_path)
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            display_name = metadata.get('game_name', display_name)
                    except (json.JSONDecodeError, FileNotFoundError):
                        pass
                    cartridge_lines.append(f"  [{current_number}] {display_name}")
                    all_games_map[str(current_number)] = game_path
                    current_number += 1
    
    # We might want separate frames if this gets too long, or adjust the title logic for multiple carts
    print_framed_text(
        lines=cartridge_lines,
        title="Loaded Cartridges",
        border_color='ansimagenta', # Magenta border for cartridges
        text_bg_color='ansibrightblack', # Dark background
        text_fg_color='ansicyan' # Cyan text for cartridge content
    )

    return all_games_map

# --- Cartridge System Functions ---
def detect_removable_drives():
    """
    Detects currently mounted removable (USB) drives.
    Returns a list of mount points.
    """
    drives = []
    for partition in psutil.disk_partitions(all=False):
        # Check for common removable drive flags on macOS/Linux (e.g., 'removable', 'cdrom', 'fixed' for non-removable)
        # Note: psutil's 'removable' flag might not be universally reliable across all OSes or USB types.
        # On macOS, USB drives often appear without 'removable' flag, but as 'external' drives.
        # A more robust check might involve 'device' path patterns or specific filesystem types.
        if 'removable' in partition.opts or ('/Volumes/' in partition.mountpoint and psutil.os.name == 'posix'):
            # Basic heuristic for macOS: typically mounted under /Volumes/
            drives.append(partition.mountpoint)
    # Filter out common system-related mounts that are not true "cartridges"
    # This might need refinement based on your specific OS setup
    filtered_drives = [d for d in drives if not d.startswith('/dev/') and not d.startswith('/System/') and not d.startswith('/private/')]
    return filtered_drives


def scan_cartridges():
    """
    Detects removable drives, scans them for games, and updates global maps.
    """
    global DETECTED_CARTRIDGES, CARTRIDGE_GAMES_MAP
        
    DETECTED_CARTRIDGES = detect_removable_drives()
    CARTRIDGE_GAMES_MAP = {} # Reset map for new scan
    
    if not DETECTED_CARTRIDGES:
        print_formatted_text("No removable drives (cartridges) detected.")
        return

    print_formatted_text("\nScanning detected cartridges...")
    for drive_path in DETECTED_CARTRIDGES:
        print_formatted_text(f"  Scanning: {drive_path}")
        games_on_this_cart = discover_games_in_path(drive_path, is_cartridge=True)
        if games_on_this_cart:
            CARTRIDGE_GAMES_MAP[drive_path] = games_on_this_cart
            print_formatted_text(f"    Found {len(games_on_this_cart)} compatible games on {os.path.basename(drive_path)}")
        else:
            print_formatted_text(f"    No compatible games found on {os.path.basename(drive_path)}")
    print_formatted_text("Cartridge scan complete.\n")

# --- UPDATED: Flowey Chatbot Function with Gemini Integration and Robust Error Handling ---
def flowey_chatbot(session, style):
    """
    Initiates a conversation with Flowey, now powered by Google Gemini (if configured).
    Includes robust error handling and chat session reset on AI errors.
    """
    print_formatted_text("\nFlowey: Howdy! I'm Flowey. Flowey the Flower!")
    print_formatted_text("Flowey: You must be new to the underground, aren't ya?")
    print_formatted_text("Flowey: Type 'bye' or 'exit' to leave our little chat.")
    play_sound("flowey_chat_enter") # Play sound when entering chat
    
    if GEMINI_MODEL is None:
        print_formatted_text(HTML("<ansiyellow>Flowey: Uh oh! My AI brain isn't connected right now. I can only do simple chats.</ansiyellow>"))
        print_formatted_text(HTML("<ansiyellow>      (Please ensure your GOOGLE_API_KEY environment variable is set correctly and try restarting the app.)</ansiyellow>"))

    # Initialize chat session
    chat = None
    if GEMINI_MODEL:
        try:
            chat = GEMINI_MODEL.start_chat(history=[])
        except Exception as chat_init_error:
            print_formatted_text(HTML(f"<ansired>Flowey (AI Chat Init Error): Couldn't start our chat! Error: {chat_init_error}</ansired>"))
            print_formatted_text(HTML("<ansiyellow>Flowey: My AI brain might be a little glitchy. (Check API key and internet connection!)</ansiyellow>"))
            play_sound("error") # Play error sound
            chat = None

    while True:
        try:
            # Flowey's prompt in yellow
            user_input = session.prompt(HTML("<ansiyellow>You: </ansiyellow>"), style=style).strip()
            user_input_lower = user_input.lower()
            
            if user_input_lower in ['bye', 'exit', 'goodbye', 'quit']:
                print_formatted_text("Flowey: See ya around, pal!")
                play_sound("menu_select") # Sound on exiting chat
                break

            # Rule-based responses (these will override AI if matched)
            elif "game" in user_input_lower and "play" not in user_input_lower:
                print_formatted_text("Flowey: Looking to play a game, huh? Use the 'play' command outside of chat!")
            elif "storage" in user_input_lower or "space" in user_input_lower or "limit" in user_input_lower:
                print_formatted_text("Flowey: Oh, that silly 16MB limit? It's all part of the charm! Try 'storage' command.")
            elif "hello" in user_input_lower or "hi" in user_input_lower:
                print_formatted_text("Flowey: Howdy!")
            elif "who are you" in user_input_lower:
                print_formatted_text("Flowey: I'm Flowey! The friendliest flower you'll ever meet! At least, that's what I tell everyone. Hehehe.")
            elif "how are you" in user_input_lower:
                print_formatted_text("Flowey: Peachy keen! Always ready to help you navigate this world... or just chat! Hehehe.")
            elif "help" in user_input_lower:
                print_formatted_text("Flowey: Need help? Just ask me anything, or type 'help' in the main menu for commands. I'm here to guide you!")
            elif "bug" in user_input_lower or "error" in user_input_lower:
                print_formatted_text("Flowey: Oh dear! Did something break? Don't worry, a little determination fixes everything! (And maybe checking the console for errors!)")
            elif chat: # Use Gemini if available and no specific rule matched
                try:
                    response = chat.send_message(user_input)
                    print_formatted_text(f"Flowey: {response.text}")
                except Exception as ai_error:
                    print_formatted_text(HTML(f"<ansired>Flowey (AI Error): My circuits are buzzing! I couldn't process that. Error: {str(ai_error)}</ansired>"))
                    print_formatted_text(HTML("<ansiyellow>Flowey: Try rephrasing or asking something else. (Or check your API key/internet connection!)</ansiyellow>"))
                    play_sound("error") # Play error sound for AI errors
                    
                    # Try to re-initialize chat on error
                    if GEMINI_MODEL:
                        try:
                            chat = GEMINI_MODEL.start_chat(history=[])
                            print_formatted_text(HTML("<ansicyan>Flowey: (Oops! My memory got a little scrambled, let's start fresh for the next question!)</ansicyan>"))
                        except Exception as reset_error:
                            print_formatted_text(HTML(f"<ansired>Flowey (AI Reset Error): Couldn't reset my brain! {str(reset_error)}</ansired>"))
                            play_sound("error") # Play error sound for AI reset failure
                            chat = None
                    else:
                        chat = None
            else: # Fallback to a generic response if AI is not configured or failed to initialize/reset
                print_formatted_text("Flowey: That's a nice thought, human! Tell me more.")
                
        except KeyboardInterrupt:
            print_formatted_text("\nFlowey: Trying to escape? How rude!")
            play_sound("error") # Play sound on keyboard interrupt
            break
        except EOFError:
            print_formatted_text("\nFlowey: See ya around, pal!")
            play_sound("menu_select") # Sound on EOF (Ctrl+D)
            break
        except Exception as chat_error:
            print_formatted_text(HTML(f"<ansired>Flowey: Something went wrong in our chat: {str(chat_error)}</ansired>"))
            play_sound("error") # Play error sound for general chat errors

# --- Main Terminal Logic ---
def main():
    play_sound("startup") # Play startup sound

    # --- RetroFlow Terminal Intro Box (using helper) ---
    welcome_text_lines = [
        "For a list of available commands type: HELP",
        "To list games type: LIST",
        "To check storage status type: STORAGE",
        "",
        "To scan for games on cartridges type: CARTRIDGE SCAN",
        "To chat with AI Flowey type: CHAT",
        "To launch a game use: PLAY <number>",
        "",
        "HAVE FUN!",
        "The RetroFlow Project"
    ]
    print_framed_text(
        lines=welcome_text_lines,
        title="Welcome to RetroFlow Terminal v0.5",
        border_color='ansiblue',
        text_bg_color='ansiblue',
        text_fg_color='ansilwhite' # Using 'ansilwhite' for bright white text on blue background
    )
    # --- End RetroFlow Terminal Intro Box ---

    print_formatted_text("\nRetroFlow Terminal v0.5 - Cartridge System & AI Flowey Enabled") # This line will appear below the box
    print_formatted_text("Type 'help' for commands, 'exit' to quit.") # This line too

    # Define the style for the prompt_toolkit session
    style = Style.from_dict({
        'prompt': '#00ff00',      # Green for the main prompt (Z:\>)
        'output': '#00ff00',      # Green for general output
        'error': '#ff0000',       # Red for error messages
        'warn': '#ffff00',        # Yellow for warnings
        'info': '#00ffff',        # Cyan for informational messages
        'flowey_prompt': '#ffff00' # Yellow for Flowey's prompt (inside chat, if different)
    })

    # Initial scan for local games
    local_games_list = discover_games_in_path(GAMES_DIRECTORY)
    scan_cartridges()
    
    current_game_map = display_games(local_games_list, CARTRIDGE_GAMES_MAP)
    current_storage_bytes = get_directory_size(GAMES_DIRECTORY)
    storage_warning_issued = False

    # Create completer with safe word list
    command_completer_words = [
        'help', 'exit', 'list', 'play', 'chat', 'storage', 
        'cartridge scan', 'cartridge list', 'force'
    ]
    
    # Add game numbers to completer
    if current_game_map:
        command_completer_words.extend(current_game_map.keys())
    
    # Create session with completer
    try:
        commands_completer = WordCompleter(command_completer_words, ignore_case=True)
        session = PromptSession(completer=commands_completer, style=style)
    except Exception as session_error:
        print_formatted_text(HTML(f"<ansiyellow>Warning: Could not initialize command completion: {session_error}</ansiyellow>"))
        session = PromptSession(style=style)
        play_sound("error") # Play error sound if completer fails

    while True:
        try:
            current_storage_bytes = get_directory_size(GAMES_DIRECTORY)
            current_storage_mb = current_storage_bytes / (1024 * 1024)
            
            if current_storage_bytes > MAX_STORAGE_BYTES and not storage_warning_issued:
                print_formatted_text(HTML(f"<ansired>WARNING: STORAGE LIMIT EXCEEDED! ({current_storage_mb:.2f}MB / {MAX_STORAGE_MB}MB)</ansired>"))
                print_formatted_text(HTML("<ansired>RETROFLOW IS CRASHING DUE TO LACK OF DISK SPACE!</ansired>"))
                print_formatted_text(HTML("<ansired>Please delete some files from the 'Games' directory or type 'force' to attempt to bypass.</ansired>"))
                play_sound("error") # Play error sound for storage warning
                storage_warning_issued = True
            elif current_storage_bytes <= MAX_STORAGE_BYTES and storage_warning_issued:
                print_formatted_text(HTML(f"<ansicyan>Storage limit now within bounds. Current: {current_storage_mb:.2f}MB.</ansicyan>"))
                play_sound("menu_select") # Play success sound when storage OK
                storage_warning_issued = False

            # The Z:\> prompt change
            command_line = session.prompt('Z:\\> ').strip()
            
            if command_line.lower() == 'exit':
                print_formatted_text("Exiting RetroFlow Terminal. Goodbye!")
                play_sound("menu_select") # Play sound on exit
                break
                
            elif command_line.lower() == 'help':
                help_lines = [
                    "  list              - List all discovered local and cartridge games",
                    "  play <number>     - Launch a game by its corresponding number (e.g., 'play 1')",
                    "  storage           - Check current local storage usage",
                    "  cartridge scan    - Detect and scan connected USB drives for games",
                    "  cartridge list    - List detected cartridges and their contents",
                    "  chat              - Initiate conversation with Flowey (now AI-powered!)",
                    "  exit              - Exit the RetroFlow Terminal",
                    "  force             - Attempt to bypass local storage limit (use with caution!)"
                ]
                print_framed_text(
                    lines=help_lines,
                    title="Available Commands",
                    border_color='ansiyellow', # Yellow border for help
                    text_bg_color='ansibrightblack', # Dark background inside
                    text_fg_color='ansigreen' # Green text for commands
                )
                play_sound("menu_select")
                
            elif command_line.lower() == 'list':
                local_games_list = discover_games_in_path(GAMES_DIRECTORY)
                current_game_map = display_games(local_games_list, CARTRIDGE_GAMES_MAP)
                
                # Update completer with new game numbers
                command_completer_words = ['help', 'exit', 'list', 'play', 'chat', 'storage', 'cartridge scan', 'cartridge list', 'force']
                if current_game_map:
                    command_completer_words.extend(current_game_map.keys())
                try:
                    commands_completer = WordCompleter(command_completer_words, ignore_case=True)
                    session.completer = commands_completer
                except Exception:
                    pass # Ignore completer update errors
                play_sound("menu_select") # Play sound for list command
                    
            elif command_line.lower() == 'storage':
                current_storage_bytes = get_directory_size(GAMES_DIRECTORY)
                current_storage_mb = current_storage_bytes / (1024 * 1024)
                storage_lines = [f"Current 'Games' directory usage: {current_storage_mb:.2f} MB / {MAX_STORAGE_MB} MB"]
                if current_storage_bytes > MAX_STORAGE_BYTES:
                    storage_lines.append(HTML("<ansired>Status: STORAGE LIMIT EXCEEDED!</ansired>"))
                    play_sound("error") # Play error sound if storage exceeded
                else:
                    storage_lines.append("Status: OK.")
                
                print_framed_text(
                    lines=storage_lines,
                    title="Storage Status",
                    border_color='ansibrightgreen', # Bright green border
                    text_bg_color='ansibrightblack', # Dark background
                    text_fg_color='ansilwhite' # White text
                )
                play_sound("menu_select") # Play sound for storage command
                    
            elif command_line.lower() == 'cartridge scan':
                scan_cartridges()
                local_games_list = discover_games_in_path(GAMES_DIRECTORY)
                current_game_map = display_games(local_games_list, CARTRIDGE_GAMES_MAP)
                
                # Update completer
                command_completer_words = ['help', 'exit', 'list', 'play', 'chat', 'storage', 'cartridge scan', 'cartridge list', 'force']
                if current_game_map:
                    command_completer_words.extend(current_game_map.keys())
                try:
                    commands_completer = WordCompleter(command_completer_words, ignore_case=True)
                    session.completer = commands_completer
                except Exception:
                    pass
                play_sound("menu_select") # Play sound for scan command
                    
            elif command_line.lower() == 'cartridge list':
                cart_list_lines = []
                if not DETECTED_CARTRIDGES:
                    cart_list_lines.append("No cartridges currently detected. Use 'cartridge scan' to find them.")
                else:
                    for drive_path in DETECTED_CARTRIDGES:
                        cart_size = get_directory_size(drive_path)
                        cart_list_lines.append(HTML(f"<ansicyan>  {os.path.basename(drive_path)} (Path: {drive_path}) (Size: {format_bytes(cart_size)})</ansicyan>"))
                        if drive_path in CARTRIDGE_GAMES_MAP and CARTRIDGE_GAMES_MAP[drive_path]:
                            cart_list_lines.append("    Games on this cartridge:")
                            for game_path in CARTRIDGE_GAMES_MAP[drive_path]:
                                metadata_path = os.path.splitext(game_path)[0] + ".json"
                                display_name = os.path.basename(game_path)
                                try:
                                    with open(metadata_path, 'r') as f:
                                        metadata = json.load(f)
                                        display_name = metadata.get('game_name', display_name)
                                except (json.JSONDecodeError, FileNotFoundError):
                                    pass
                                cart_list_lines.append(f"      - {display_name}")
                        else:
                            cart_list_lines.append("    No compatible games loaded from this cartridge.")
                
                print_framed_text(
                    lines=cart_list_lines,
                    title="Detected Cartridges",
                    border_color='ansimagenta',
                    text_bg_color='ansibrightblack',
                    text_fg_color='ansicyan'
                )
                play_sound("menu_select") # Play sound for cartridge list
                    
            elif command_line.lower().startswith('play '):
                if current_storage_bytes > MAX_STORAGE_BYTES and storage_warning_issued: # Only block if storage is actually exceeded AND warning issued
                    print_formatted_text(HTML("<ansired>ERROR: Cannot launch game. Local storage limit exceeded. Delete files or use 'force' to bypass.</ansired>"))
                    play_sound("error") # Play error sound
                    continue
                
                parts = command_line.split(' ', 1)
                if len(parts) > 1:
                    game_identifier = parts[1].strip()
                    if game_identifier in current_game_map:
                        game_to_launch_path = current_game_map[game_identifier]
                        launch_game(game_to_launch_path)
                    else:
                        print_framed_text(
                            lines=[f"Game '{game_identifier}' not found. Use 'list' to see available games."],
                            title="Error",
                            border_color='ansired',
                            text_bg_color='ansibrightblack',
                            text_fg_color='ansired'
                        )
                        play_sound("error") # Play error sound if game not found
                else:
                    print_framed_text(
                        lines=["Usage: play <game_number>"],
                        title="Error",
                        border_color='ansired',
                        text_bg_color='ansibrightblack',
                        text_fg_color='ansired'
                    )
                    play_sound("error") # Play error sound for incorrect usage
                    
            elif command_line.lower() == 'force':
                if current_storage_bytes > MAX_STORAGE_BYTES:
                    print_framed_text(
                        lines=["Attempting to bypass local storage limit. Launching at your own risk!"],
                        title="Bypass Active",
                        border_color='ansiyellow',
                        text_bg_color='ansibrightblack',
                        text_fg_color='ansiyellow'
                    )
                    storage_warning_issued = False # Reset warning flag for this session
                    play_sound("menu_select") # Play sound for force command
                else:
                    print_framed_text(
                        lines=["No local storage limit to bypass. Storage is OK."],
                        title="Status",
                        border_color='ansicyan',
                        text_bg_color='ansibrightblack',
                        text_fg_color='ansicyan'
                    )
                    play_sound("menu_select") # Play sound if no bypass needed
                    
            elif command_line.lower() == 'chat':
                flowey_chatbot(session, style)
                # Sound for entering chat is inside flowey_chatbot
                # Sound for exiting chat is inside flowey_chatbot
                
            elif command_line:
                print_framed_text(
                    lines=[f"Unknown command: '{command_line}'. Type 'help' for available commands."],
                    title="Error",
                    border_color='ansired',
                    text_bg_color='ansibrightblack',
                    text_fg_color='ansired'
                )
                play_sound("error") # Play error sound for unknown command
                
        except EOFError:
            print_formatted_text("Exiting RetroFlow Terminal. Goodbye!")
            play_sound("menu_select") # Play sound on EOF (Ctrl+D)
            break
        except KeyboardInterrupt:
            print_formatted_text("Operation cancelled. Type 'exit' to quit.")
            play_sound("error") # Play sound on KeyboardInterrupt
            continue
        except Exception as main_error:
            print_framed_text(
                lines=[f"An unexpected error occurred: {str(main_error)}"],
                title="Critical Error",
                border_color='ansired',
                text_bg_color='ansibrightblack',
                text_fg_color='ansired'
            )
            play_sound("error") # Play error sound for unexpected errors
            # Don't break the loop, just continue to next iteration

if __name__ == "__main__":
    main()
    sys.exit(0)