"""FREE-WILi Display & LED management."""
import time
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

from .state import GameState, Role, ROLE_LED_COLORS

def render_main_display(fw: FreeWili, state: GameState, message: str = "") -> None:
    """Render the current game state to the 320x240 screen."""
    # Screen is 320x240, standard font is approx 30-40 chars wide depending on size
    lines = [
        f"== PHASE: {state.phase.value.upper()} (Turn {state.turn}) ==",
        ""
    ]
    
    alive_count = len(state.living_players())
    lines.append(f"Players Alive: {alive_count}/{len(state.players)}")
    lines.append("-" * 30)
    
    # Show active players briefly
    for p in state.living_players()[:5]:  # show top 5 fitting on screen
        icon = "*" if p.is_ai else "H"
        lines.append(f"[{icon}] {p.name}")
        
    if len(state.living_players()) > 5:
        lines.append("...")
        
    if message:
        lines.append("")
        lines.append(">> " + message[:50])

    text = "\n".join(lines)
    # Ensure ASCII only
    text = text.encode('ascii', 'replace').decode('ascii')
    fw.show_text_display(text, FreeWiliProcessorType.Display)

def render_selection_screen(fw: FreeWili, title: str, items: list[str], selected: int) -> None:
    """Render a vertical selection menu."""
    lines = [
        title.upper(),
        "=" * len(title),
        ""
    ]
    for i, item in enumerate(items):
        prefix = ">>" if i == selected else "  "
        lines.append(f"{prefix} [{i+1}] {item}")
        
    lines.append("")
    lines.append("[W]Up [Y]Down [G]Select")
    text = "\n".join(lines)
    text = text.encode('ascii', 'replace').decode('ascii')
    fw.show_text_display(text, FreeWiliProcessorType.Display)

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
