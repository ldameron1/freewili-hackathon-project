#!/home/ld/Pictures/Hackathon/venv/bin/python
"""Entry point for the FREE-WILi Mafia Game."""
import argparse
import time
import threading
import sys
import logging
import os
import psutil

from dotenv import load_dotenv

# Add project root to path so we can import src modules seamlessly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress verbose Flask output
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType, ButtonColor

from src.game.state import Player, Role, DEFAULT_VOICES
from src.game.engine import MafiaEngine
from src.game import display
from src.moderator.app import create_app


def start_flask(engine: MafiaEngine):
    app = create_app(engine)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def cleanup_stale_processes() -> None:
    current_pid = os.getpid()
    protected_pids = {current_pid}
    try:
        current_process = psutil.Process(current_pid)
        protected_pids.update(parent.pid for parent in current_process.parents())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    target_markers = {
        "src/main.py",
        "hardware_tone_test.py",
        "test_tts_playback.py",
        "tests/test_tts_playback.py",
        "src/utils/cleanup_hw.py",
    }
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid in protected_pids:
                continue
            cmdline = proc.info.get("cmdline") or []
            joined = " ".join(cmdline)
            if "python" not in joined:
                continue
            if any(marker in joined for marker in target_markers):
                print(f"[Startup] Terminating stale process {proc.pid}: {joined}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def build_ai_players(mode: str) -> list[Player]:
    roles = [
        Role.MAFIA, Role.MAFIA,
        Role.DOCTOR, Role.DETECTIVE,
        Role.TOWN, Role.TOWN, Role.TOWN, Role.TOWN, Role.TOWN
    ]
    
    if mode in ["mixed", "debug"]:
        names = ["User", "Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi"]
    elif mode == "human_only":
        names = ["User", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"]
    else: # ai_only
        names = ["Zeus", "Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi"]

    personalities = [
        "The human participant", "Analytical and cautious", "Boisterous and friendly",
        "Nervous and defensive", "Quiet but observant", "Aggressive and accusatory",
        "Sarcastic and witty", "Helpful and naive", "Overthinking everything"
    ]
    
    players = []
    for i in range(9):
        is_human = (names[i].startswith("User"))
        players.append(Player(
            name=names[i],
            role=roles[i],
            is_ai=not is_human,
            voice_id=DEFAULT_VOICES[i % len(DEFAULT_VOICES)],
            personality=personalities[i]
        ))
    return players


def wait_for_menu_selection(fw: FreeWili) -> str:
    items = ["DEBUG: Human Mafia", "Play: Mixed Mode", "Play: AI-Only", "Exit"]
    actions = ["debug", "mixed", "ai_only", "exit"]
    selected = 0
    
    print("\n[MENU] Rendering to FREE-WILi...")
    display.render_selection_screen(fw, "MAFIA MENU", items, selected)
    
    # Wait for button release
    print("[MENU] Release buttons to start...")
    while True:
        try:
            btns = fw.read_all_buttons().expect("Button fail")
            if not any(btns.values()): break
        except Exception: pass
        time.sleep(0.05)
    time.sleep(0.1)

    last_buttons = fw.read_all_buttons().expect("Button fail")
    print("[MENU] Listening for input...")
    
    while True:
        try:
            buttons = fw.read_all_buttons().expect("Button fail")
            for color, state in buttons.items():
                if state and not last_buttons.get(color, False):
                    name = color.name
                    if name == "White":
                        selected = (selected - 1) % len(items)
                        display.render_selection_screen(fw, "MAFIA MENU", items, selected)
                        fw.play_audio_tone(440, 0.05, 0.2)
                    elif name == "Yellow":
                        selected = (selected + 1) % len(items)
                        display.render_selection_screen(fw, "MAFIA MENU", items, selected)
                        fw.play_audio_tone(440, 0.05, 0.2)
                    elif name == "Green":
                        print(f"[MENU] Selected: {actions[selected]}")
                        # RESTORE THE SELECTION TONE
                        fw.play_audio_tone(660, 0.15, 0.3)
                        return actions[selected]
            last_buttons = buttons
        except Exception: pass
        time.sleep(0.05)

def main():
    print("Main script starting...")
    load_dotenv()
    cleanup_stale_processes()

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-menu", action="store_true")
    args = parser.parse_args()

    print("Connecting to FREE-WILi...")
    try:
        fw = FreeWili.find_first().expect("No device")
        fw.open().expect("Open fail")
        if fw.main_serial: fw.main_serial.is_badge = False
        if fw.display_serial: fw.display_serial.is_badge = False
        print("Connected!")
    except Exception as e:
        print(f"Hardware Error: {e}"); sys.exit(1)

    try:
        mode = "ai_only" if args.skip_menu else None
        if not mode:
            mode = wait_for_menu_selection(fw)
            if mode == "exit": return

        print(f"Mode: {mode}")
        engine = MafiaEngine(fw)
        players = build_ai_players(mode)
        
        if mode == "debug":
            for p in players:
                if p.name == "User": p.role = Role.MAFIA
            print("DEBUG: User forced to Mafia.")

        # Start Moderator UI
        threading.Thread(target=start_flask, args=(engine,), daemon=True).start()
        
        engine.setup_game(players)
        
        # RESTORE THE DEBUG SPLASH AND WAIT FOR SECOND CLICK
        if mode == "debug":
            fw.show_text_display("DEBUG MODE\n\nHuman is MAFIA\n\nPress GREEN to start", FreeWiliProcessorType.Display)
            # Wait for button press
            while True:
                try:
                    btns = fw.read_all_buttons().expect("Buttons fail")
                    if btns.get(ButtonColor.Green, False):
                        fw.play_audio_tone(880, 0.1, 0.3)
                        break
                except: pass
                time.sleep(0.05)
            # Wait for release
            while True:
                try:
                    btns = fw.read_all_buttons().expect("Buttons fail")
                    if not any(btns.values()): break
                except: pass
                time.sleep(0.05)

        # Introduction Phase
        engine.run_intro_phase()
        
        # Registration (skipped in debug)
        if mode != "debug":
            engine.run_registration_phase()
        
        engine.run_game_loop()

    except KeyboardInterrupt:
        print("\nShutdown.")
    finally:
        display.clear_leds(fw); fw.reset_display(); fw.close()

if __name__ == "__main__":
    main()
