"""FREE-WILi Display & LED management."""
import time
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

from .state import GameState, Role, ROLE_LED_COLORS, Player
from .render_utils import HardwareRenderer

# Initialize the Noir-Tech Renderer
renderer = HardwareRenderer()

# ASCII Art Portraits for AI Personalities (Charming Edition)
ASCII_PHIZ = {
    "Zeus":     ["  /\\___/\\  ", " (  ^ . ^ ) ", "  \\  _  /  ", "   v---v   "],
    "Alice":    ["  _______  ", " | [0-0] | ", " |  ___  | ", "  \\_____/  "],
    "Bob":      ["  _______  ", " (  >.<  ) ", " (   o   ) ", "  \\_____/  "],
    "Charlie":  ["   _____   ", "  / o o \\  ", " (  ---  ) ", "  \\_____/  "],
    "Dave":     ["  -------  ", " |  -_-  | ", " |   _   | ", "  -------  "],
    "Eve":      ["  \\\\\\\\^////  ", " (  #.#  ) ", "  \\  ~  /  ", "   v---v   "],
    "Frank":    ["   _____   ", "  / s s \\  ", " (  ---  ) ", "  \\_mmm_/  "],
    "Grace":    ["   /\\ /\\   ", "  ( o.o )  ", "   \\ u /   ", "    ---    "],
    "Heidi":    ["  ///////  ", " (  @ @  ) ", " (   ?   ) ", "  \\\\\\\\\\\\\\  "],
    "User":     ["   _____   ", "  |o---o|  ", "  |  ^  |  ", "  \\_---_/  "],
    "Default":  ["    ???    ", "   ( ? )   ", "    ???    ", "           "]
}

def render_main_display(fw: FreeWili, state: GameState, message: str = "", active_player: Player = None) -> None:
    """Render the current game state as a Noir-Tech image to the 320x240 screen."""
    title = f"{state.phase.value.split('_')[0]} : TURN {state.turn}"
    
    items = []
    if active_player:
        items.append(f"ACTIVE: {active_player.name}")
        items.append(f"BUDGET: {active_player.talk_count}/5")
        if message:
            # Wrap message or truncate if needed, but for now just show it
            items.append(message)
    else:
        for p in state.living_players()[:6]:
            status = "[ALIVE]" if p.alive else "[DEAD]"
            items.append(f"{p.name} {status}")

    fwi_path = renderer.render_game_screen(title, items, turn_info=f"T{state.turn}")
    
    # Upload and Show (Use unique paths to bypass hardware file cache)
    remote_path = f"/images/g_{int(time.time())}.fwi"
    fw.send_file(fwi_path, remote_path, processor=FreeWiliProcessorType.Display)
    fw.show_gui_image(remote_path)

def render_selection_screen(fw: FreeWili, title: str, items: list[str], selected: int) -> None:
    """Render a premium Noir selection menu as an image."""
    fwi_path = renderer.render_menu(title, items, selected)
    
    # Upload and Show (Unique paths for menu items)
    remote_path = f"/images/m_{int(time.time())}.fwi"
    fw.send_file(fwi_path, remote_path, processor=FreeWiliProcessorType.Display)
    fw.show_gui_image(remote_path)

def set_role_leds(fw: FreeWili, role: Role) -> None:
    """Set all LEDs to the role color."""
    r, g, b = ROLE_LED_COLORS.get(role, (10, 10, 10))
    for i in range(7):
        fw.set_board_leds(i, r, g, b)

def clear_leds(fw: FreeWili) -> None:
    for i in range(7):
        fw.set_board_leds(i, 0, 0, 0)

def flash_leds(fw: FreeWili, r: int, g: int, b: int, count: int = 3, delay: float = 0.2) -> None:
    for _ in range(count):
        for i in range(7):
            fw.set_board_leds(i, r, g, b)
        time.sleep(delay)
        clear_leds(fw)
        time.sleep(delay)

def run_led_countdown(fw: FreeWili, duration_sec: int) -> None:
    """A blocking countdown using the 7 LEDs as a progress bar."""
    total_leds = 7
    interval = duration_sec / total_leds

    for i in range(total_leds):
        fw.set_board_leds(i, 0, 20, 0)  # Init all green
        
    time.sleep(0.5)
    
    for i in reversed(range(total_leds)):
        # Calculate time passed for this LED chunk
        start = time.time()
        
        # Make the current "active" LED fade or pulse to show time ticking
        while time.time() - start < interval:
            progress = (time.time() - start) / interval
            # fade from Green to Yellow to Red
            r = int(20 * progress)
            g = int(20 * (1.0 - progress))
            fw.set_board_leds(i, r, g, 0)
            time.sleep(0.1)
            
        # Turn off LED when its chunk is done
        fw.set_board_leds(i, 0, 0, 0)
        
    # Time's up — flash red
    flash_leds(fw, 20, 0, 0, count=2, delay=0.1)
