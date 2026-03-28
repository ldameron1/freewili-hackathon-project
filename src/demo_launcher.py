"""
Mafia Game Launcher Demo — Runs on FREE-WILi
=============================================
Displays a menu on the FREE-WILi screen, handles button navigation,
cycles LEDs to show role colors, and plays audio feedback.

This demo proves out the core interaction loop that the full game will use:
  - Display rendering (320x240)
  - Button input (yellow=up, white=down, green=select, red=back)
  - LED role signaling (per player color)
  - Audio feedback (tones on selection)
  - Camera capture attempt (WilEye Orca)

Run:
    source venv/bin/activate
    python src/demo_launcher.py
"""

import time
import sys
from datetime import datetime

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

# ── Role colors for LEDs (R, G, B) ──
ROLE_COLORS = {
    "Mafia":      (20, 0, 0),     # Red
    "Doctor":     (0, 20, 0),     # Green
    "Detective":  (0, 0, 20),     # Blue
    "Town":       (15, 15, 15),   # White
}

# ── Menu structure ──
MAIN_MENU = [
    "[1] AI-Only Mode",
    "[2] Mixed Mode (2H+7AI)",
    "[3] Camera Test",
    "[4] LED Role Demo",
    "[5] Audio Test",
    "[6] Device Info",
    "[7] WiFi Setup / Test",
]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def render_menu(fw: FreeWili, items: list, selected: int, title: str = "MAFIA LAUNCHER") -> None:
    """Render a menu on the FREE-WILi display."""
    lines = [title, "=" * len(title), ""]
    for i, item in enumerate(items):
        prefix = ">" if i == selected else " "
        lines.append(f"{prefix} {item}")
    lines.append("")
    lines.append("[Y]Up [W]Down [G]Select")
    text = "\n".join(lines)
    fw.show_text_display(text, FreeWiliProcessorType.Display)


def set_role_leds(fw: FreeWili, role: str) -> None:
    """Light all 7 LEDs in the color for a given role."""
    r, g, b = ROLE_COLORS.get(role, (10, 10, 10))
    for led in range(7):
        fw.set_board_leds(led, r, g, b)


def clear_leds(fw: FreeWili) -> None:
    """Turn off all LEDs."""
    for led in range(7):
        fw.set_board_leds(led, 0, 0, 0)


def play_select_tone(fw: FreeWili) -> None:
    """Play a short confirmation beep."""
    fw.play_audio_tone(660, 0.1, 0.3)
    time.sleep(0.15)


def play_navigate_tone(fw: FreeWili) -> None:
    """Play a short navigation tick."""
    fw.play_audio_tone(440, 0.05, 0.2)
    time.sleep(0.08)


def demo_role_leds(fw: FreeWili) -> None:
    """Cycle through role colors on LEDs."""
    log("LED Role Demo: cycling through roles...")
    fw.show_text_display("LED ROLE DEMO\n\nWatch the LEDs\ncycle through\nMafia roles...", FreeWiliProcessorType.Display)

    for role, (r, g, b) in ROLE_COLORS.items():
        log(f"  {role}: RGB({r},{g},{b})")
        fw.show_text_display(f"LED ROLE DEMO\n\nRole: {role}\nRGB({r},{g},{b})", FreeWiliProcessorType.Display)
        set_role_leds(fw, role)
        fw.play_audio_tone(440 + list(ROLE_COLORS.keys()).index(role) * 110, 0.2, 0.3)
        time.sleep(1.5)

    clear_leds(fw)
    log("  LED Demo complete")


def demo_audio(fw: FreeWili) -> None:
    """Play a sequence of tones."""
    log("Audio Demo: playing tone sequence...")
    fw.show_text_display("AUDIO DEMO\n\nPlaying tones...\n\n440 > 550 > 660 > 880 Hz", FreeWiliProcessorType.Display)

    for hz in [440, 550, 660, 880]:
        log(f"  Playing {hz}Hz...")
        fw.play_audio_tone(hz, 0.3, 0.4)
        time.sleep(0.5)

    log("  Audio Demo complete")


def demo_camera(fw: FreeWili) -> None:
    """Attempt to capture a photo with WilEye camera."""
    log("Camera Test: attempting photo capture...")
    fw.show_text_display("CAMERA TEST\n\nCapturing photo\nvia WilEye Orca...", FreeWiliProcessorType.Display)

    try:
        result = fw.wileye_take_picture(0, "demo_photo.jpg")
        if result.is_ok():
            msg = "Photo captured!\nSaved: demo_photo.jpg"
            log(f"  Camera: photo captured!")
        else:
            err = result.unwrap_err()
            msg = f"Camera failed:\n{err}\n\nCamera may need\nre-initialization."
            log(f"  Camera failed: {err}")
    except Exception as e:
        msg = f"Camera error:\n{str(e)[:60]}"
        log(f"  Camera error: {e}")

    fw.show_text_display(f"CAMERA TEST\n\n{msg}", FreeWiliProcessorType.Display)
    time.sleep(2)


def demo_device_info(fw: FreeWili) -> None:
    """Show device information."""
    log("Device Info...")
    try:
        app_info = fw.get_app_info().expect("Failed")
        info_text = f"DEVICE INFO\n\n{app_info}\nFW: MainCPU v91.3"
    except Exception:
        info_text = "DEVICE INFO\n\nCould not read."

    fw.show_text_display(info_text, FreeWiliProcessorType.Display)
    time.sleep(2)


def demo_ai_mode_placeholder(fw: FreeWili, mode_name: str) -> None:
    """Placeholder for game modes."""
    log(f"Mode: {mode_name} (not yet implemented)")
    fw.show_text_display(
        f"{mode_name}\n\n"
        "This mode will run\n"
        "a full Mafia game\n"
        "with AI agents.\n\n"
        "Coming soon...\n\n"
        "[Red] Back",
        FreeWiliProcessorType.Display
    )
    # Flash LEDs in Mafia red
    set_role_leds(fw, "Mafia")
    fw.play_audio_tone(330, 0.3, 0.3)
    time.sleep(0.5)
    fw.play_audio_tone(440, 0.3, 0.3)
    time.sleep(0.5)
    fw.play_audio_tone(550, 0.5, 0.4)
    time.sleep(2)
    clear_leds(fw)


def main() -> None:
    log("=" * 50)
    log("🎭 MAFIA GAME LAUNCHER — FREE-WILi Demo")
    log("=" * 50)

    # Find and connect
    log("Searching for FREE-WILi...")
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found!")
    except Exception as e:
        log(f"❌ Could not find FREE-WILi: {e}")
        sys.exit(1)

    log(f"Found: {fw}")
    fw.open().expect("Failed to open connection")
    log("✅ Connected!")

    try:
        selected = 0
        render_menu(fw, MAIN_MENU, selected)
        # Welcome tone
        fw.play_audio_tone(440, 0.15, 0.3)
        time.sleep(0.2)
        fw.play_audio_tone(660, 0.15, 0.3)
        time.sleep(0.2)
        fw.play_audio_tone(880, 0.3, 0.4)

        log("Menu displayed. Listening for buttons...")
        log("  (White=Up, Yellow=Down, Green=Select, Red=Exit)")
        log("  Press Ctrl+C on host to exit")

        last_buttons = fw.read_all_buttons().expect("Failed to read buttons")

        while True:
            try:
                buttons = fw.read_all_buttons().expect("Failed to read buttons")

                # Detect rising edges (button just pressed)
                for color, state in buttons.items():
                    if state and not last_buttons.get(color, False):
                        name = color.name

                        if name == "White":
                            # Navigate up
                            selected = (selected - 1) % len(MAIN_MENU)
                            play_navigate_tone(fw)
                            render_menu(fw, MAIN_MENU, selected)
                            log(f"  ▲ Selected: {MAIN_MENU[selected]}")

                        elif name == "Yellow":
                            # Navigate down
                            selected = (selected + 1) % len(MAIN_MENU)
                            play_navigate_tone(fw)
                            render_menu(fw, MAIN_MENU, selected)
                            log(f"  ▼ Selected: {MAIN_MENU[selected]}")

                        elif name == "Green":
                            # Select / Enter
                            play_select_tone(fw)
                            log(f"  ✓ Activated: {MAIN_MENU[selected]}")

                            if selected == 0:    # AI-Only Mode
                                demo_ai_mode_placeholder(fw, "AI-ONLY MAFIA")
                            elif selected == 1:  # Mixed Mode
                                demo_ai_mode_placeholder(fw, "MIXED MODE")
                            elif selected == 2:  # Camera Test
                                demo_camera(fw)
                            elif selected == 3:  # LED Role Demo
                                demo_role_leds(fw)
                            elif selected == 4:  # Audio Test
                                demo_audio(fw)
                            elif selected == 5:  # Device Info
                                demo_device_info(fw)
                            elif selected == 6:  # WiFi Setup
                                demo_ai_mode_placeholder(fw, "WIFI SETUP / TEST")

                            # Return to menu
                            render_menu(fw, MAIN_MENU, selected)

                        elif name == "Red":
                            # Exit
                            log("  ✕ Exit requested")
                            fw.show_text_display("Goodbye!\n\n** Mafia Game **\n   Launcher\n\n  See you soon!", FreeWiliProcessorType.Display)
                            fw.play_audio_tone(880, 0.15, 0.3)
                            time.sleep(0.2)
                            fw.play_audio_tone(660, 0.15, 0.3)
                            time.sleep(0.2)
                            fw.play_audio_tone(440, 0.3, 0.3)
                            time.sleep(1)
                            return

                last_buttons = buttons
                time.sleep(0.05)  # 20Hz polling

            except KeyboardInterrupt:
                log("\n🛑 Host interrupted")
                break

    finally:
        clear_leds(fw)
        fw.reset_display()
        fw.close()
        log("🔒 Disconnected from FREE-WILi")


if __name__ == "__main__":
    main()
