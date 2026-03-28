"""Entry point for the FREE-WILi Mafia Game."""
import argparse
import time
import threading
import sys
import logging

from dotenv import load_dotenv

# Suppress verbose Flask output to keep console clean for game logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

from src.game.state import Player, Role, DEFAULT_VOICES
from src.game.engine import MafiaEngine
from src.game import display
from src.moderator.app import create_app


def start_flask(engine: MafiaEngine):
    app = create_app(engine)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def build_ai_players() -> list[Player]:
    # 9 player game: 7 Town, 2 Mafia (1 Human, 8 AI)
    roles = [
        Role.MAFIA, Role.MAFIA,
        Role.DOCTOR, Role.DETECTIVE,
        Role.TOWN, Role.TOWN, Role.TOWN, Role.TOWN, Role.TOWN
    ]
    # "User" is the human player
    names = ["User", "Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi"]
    personalities = [
        "The human participant", "Analytical and cautious", "Boisterous and friendly",
        "Nervous and defensive", "Quiet but observant", "Aggressive and accusatory",
        "Sarcastic and witty", "Helpful and naive", "Overthinking everything"
    ]
    
    players = []
    for i in range(9):
        is_human = (names[i] == "User")
        players.append(Player(
            name=names[i],
            role=roles[i],
            is_ai=not is_human,
            voice_id=DEFAULT_VOICES[i % len(DEFAULT_VOICES)],
            personality=personalities[i]
        ))
    return players


def handle_wifi_setup(fw: FreeWili):
    """Prompt for WiFi credentials on host and send to device."""
    fw.show_text_display("WIFI SETUP\\n\\nCheck your laptop\\nterminal for prompts.", FreeWiliProcessorType.Display)
    print("\n--- FREE-WiLi WiFi Setup ---")
    ssid = input("Enter SSID: ")
    password = input("Enter Password: ")
    
    # The 'e\w' command is used to connect via the main serial bridge
    # We use main_serial directly if available, or fw.send
    cmd = f"e\\w {ssid} {password}"
    print(f"Sending command: {cmd}")
    
    try:
        if hasattr(fw, 'main_serial') and fw.main_serial:
            fw.main_serial.serial_port.send(cmd)
        else:
            # Fallback if library wrapper is used
            fw.show_text_display("WIFI SETUP\\n\\nError: Serial port\\nnot accessible.", FreeWiliProcessorType.Display)
            return

        fw.show_text_display(f"WIFI SETUP\\n\\nConnecting to:\\n{ssid}...\\n\\n(Wait for LED confirm)", FreeWiliProcessorType.Display)
        time.sleep(5)
        print("WiFi command sent. Check device for connection status.")
    except Exception as e:
        print(f"WiFi Setup Error: {e}")

def handle_camera_test(fw: FreeWili):
    """Capture a test photo via WilEye Orca."""
    fw.show_text_display("CAMERA TEST\\n\\nCapturing photo...", FreeWiliProcessorType.Display)
    print("Testing WilEye Camera...")
    
    # Dest 0 = SD, 1 = Main FS, 2 = Display FS
    filename = "startup_test.jpg"
    try:
        # Some versions of the library might need fw.wileye_take_picture or fw.main_serial.wileye_take_picture
        res = fw.wileye_take_picture(0, filename)
        if res.is_ok():
            msg = f"SUCCESS!\\nCaptured: {filename}"
            print(f"Camera Success: {res.unwrap()}")
        else:
            msg = f"FAILED\\n{res.unwrap_err()}"
            print(f"Camera Failed: {res.unwrap_err()}")
    except Exception as e:
        msg = f"ERROR\\n{str(e)[:40]}"
        print(f"Camera Error: {e}")
        
    fw.show_text_display(f"CAMERA TEST\\n\\n{msg}", FreeWiliProcessorType.Display)
    time.sleep(3)

def wait_for_menu_selection(fw: FreeWili) -> int:
    """Uses White=Up, Yellow=Down, Green=Select."""
    items = [
        "Start Mafia Game", 
        "WiFi Setup (Bottlenose)",
        "Camera Test (WilEye)",
        "Exit"
    ]
    selected = 0
    display.render_selection_screen(fw, "MAFIA MENU", items, selected)
    
    last_buttons = fw.read_all_buttons().expect("Failed to read buttons")
    
    while True:
        buttons = fw.read_all_buttons().expect("Failed to read buttons")
        
        for color, state in buttons.items():
            if state and not last_buttons.get(color, False):
                name = color.name
                
                if name == "White":  # UP
                    selected = (selected - 1) % len(items)
                    display.render_selection_screen(fw, "MAFIA MENU", items, selected)
                    fw.play_audio_tone(440, 0.05, 0.2)
                    
                elif name == "Yellow":  # DOWN
                    selected = (selected + 1) % len(items)
                    display.render_selection_screen(fw, "MAFIA MENU", items, selected)
                    fw.play_audio_tone(440, 0.05, 0.2)
                    
                elif name == "Green":  # SELECT
                    fw.play_audio_tone(660, 0.1, 0.3)
                    return selected
                    
        last_buttons = buttons
        time.sleep(0.05)


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-menu", action="store_true", help="Skip hardware menu, auto-start AI-only")
    args = parser.parse_args()

    print("Searching for FREE-WILi...")
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to connect to FREE-WILi")
        print(f"Connected: {fw}")
    except Exception as e:
        print(f"Hardware failure: {e}")
        sys.exit(1)

    try:
        if not args.skip_menu:
            while True:
                selection = wait_for_menu_selection(fw)
                if selection == 0: # Start Game
                    break
                elif selection == 1: # WiFi
                    handle_wifi_setup(fw)
                elif selection == 2: # Camera
                    handle_camera_test(fw)
                elif selection == 3: # Exit
                    return

        print("\nStarting Game Engine...")
        engine = MafiaEngine(fw)
        players = build_ai_players()
        
        # Start Flask UI in background
        print("Starting Moderator UI on http://localhost:5000")
        threading.Thread(target=start_flask, args=(engine,), daemon=True).start()
        
        # Run game
        engine.setup_game(players)
        engine.run_registration_phase()
        engine.run_game_loop()

    except KeyboardInterrupt:
        print("\nTerminated.")
    finally:
        display.clear_leds(fw)
        fw.reset_display()
        fw.close()
        print("Disconnected.")

if __name__ == "__main__":
    main()
