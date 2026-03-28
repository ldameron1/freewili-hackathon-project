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
    # 9 player game: 7 Town, 2 Mafia
    roles = [
        Role.MAFIA, Role.MAFIA,
        Role.DOCTOR, Role.DETECTIVE,
        Role.TOWN, Role.TOWN, Role.TOWN, Role.TOWN, Role.TOWN
    ]
    names = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi", "Ivan"]
    personalities = [
        "Analytical and cautious", "Boisterous and friendly", "Nervous and defensive",
        "Quiet but observant", "Aggressive and accusatory", "Sarcastic and witty",
        "Helpful and naive", "Overthinking everything", "Calm and cold"
    ]
    
    players = []
    for i in range(9):
        players.append(Player(
            name=names[i],
            role=roles[i],
            is_ai=True,
            voice_id=DEFAULT_VOICES[i % len(DEFAULT_VOICES)],
            personality=personalities[i]
        ))
    return players


def wait_for_menu_selection(fw: FreeWili) -> int:
    """Uses White=Up, Yellow=Down, Green=Select."""
    items = [
        "Mafia", 
        "[Coming soon]"
    ]
    selected = 0
    display.render_selection_screen(fw, "MAFIA MENU", items, selected)
    
    last_buttons = fw.read_all_buttons().expect("Failed to read buttons")
    
    # Yellow=Up/Down reversed in UI rendering usually, but to match exactly the prompt: "White will be up, yellow will be down"
    # Wait for user input
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
            selection = wait_for_menu_selection(fw)
            if selection != 0:
                display.render_main_display(fw, None, "Mixed mode not yet implemented.\nPress Ctrl+C to abort.")
                time.sleep(3)
                return

        print("\nStarting Game Engine...")
        engine = MafiaEngine(fw)
        players = build_ai_players()
        
        # Start Flask UI in background
        print("Starting Moderator UI on http://localhost:5000")
        threading.Thread(target=start_flask, args=(engine,), daemon=True).start()
        
        # Run game
        engine.setup_game(players)
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
