"""
Hardware Connectivity Test for AI Integrated Social Intrigue Game(s)
====================================================================
Tests FREE-WILi and WilEye Camera (ESP32-P4-EYE) connectivity.

Run: python tests/test_hardware.py
"""

import time
import sys
from datetime import datetime

# ── Results tracker ──
results = []

def log(msg: str) -> None:
    """Print with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def test_pass(name: str, detail: str = "") -> None:
    results.append(("PASS", name, detail))
    log(f"  ✅ {name}: {detail}" if detail else f"  ✅ {name}")

def test_fail(name: str, detail: str = "") -> None:
    results.append(("FAIL", name, detail))
    log(f"  ❌ {name}: {detail}" if detail else f"  ❌ {name}")

def test_skip(name: str, detail: str = "") -> None:
    results.append(("SKIP", name, detail))
    log(f"  ⏭️  {name}: {detail}" if detail else f"  ⏭️  {name}")


# ════════════════════════════════════════════════════
# 1. Device Discovery
# ════════════════════════════════════════════════════
log("=" * 60)
log("🔍 TEST 1: Device Discovery")
log("=" * 60)

try:
    from freewili import FreeWili
    test_pass("Import freewili")
except ImportError as e:
    test_fail("Import freewili", str(e))
    log("Cannot proceed without freewili library.")
    sys.exit(1)

# Find all devices
devices = FreeWili.find_all()
log(f"  Found {len(devices)} FreeWili device(s)")

if not devices:
    test_fail("Find devices", "No FREE-WILi devices found. Is it connected and powered?")
    log("\nNo devices found. Exiting.")
    sys.exit(1)

test_pass("Find devices", f"{len(devices)} device(s)")

for i, dev in enumerate(devices, start=1):
    log(f"  Device {i}: {dev}")
    log(f"    Main:    {dev.main}")
    log(f"    Display: {dev.display}")
    log(f"    FPGA:    {dev.fpga}")

# Use the first device
fw = devices[0]

# ════════════════════════════════════════════════════
# 2. Open Connection
# ════════════════════════════════════════════════════
log("")
log("=" * 60)
log("🔌 TEST 2: Open Connection")
log("=" * 60)

try:
    fw.open().expect("Failed to open FreeWili")
    test_pass("Open connection")
except Exception as e:
    test_fail("Open connection", str(e))
    log("Cannot proceed without connection. Exiting.")
    sys.exit(1)

try:
    # ════════════════════════════════════════════════════
    # 3. Read Buttons
    # ════════════════════════════════════════════════════
    log("")
    log("=" * 60)
    log("🔘 TEST 3: Read Buttons")
    log("=" * 60)

    try:
        buttons = fw.read_all_buttons().expect("Failed to read buttons")
        log(f"  Button states: {buttons}")
        for color, state in buttons.items():
            state_str = "Pressed" if state else "Released"
            log(f"    {color.name}: {state_str}")
        test_pass("Read buttons", f"{len(buttons)} buttons detected")
    except Exception as e:
        test_fail("Read buttons", str(e))

    # ════════════════════════════════════════════════════
    # 4. LED Test (cycle through all 7 LEDs)
    # ════════════════════════════════════════════════════
    log("")
    log("=" * 60)
    log("💡 TEST 4: LED Cycle")
    log("=" * 60)

    try:
        # Cycle through LEDs with different colors
        colors = [
            (20, 0, 0),   # Red
            (0, 20, 0),   # Green
            (0, 0, 20),   # Blue
            (20, 20, 0),  # Yellow
            (0, 20, 20),  # Cyan
            (20, 0, 20),  # Magenta
            (20, 20, 20), # White
        ]
        for led_num in range(7):
            r, g, b = colors[led_num]
            fw.set_board_leds(led_num, r, g, b).expect(f"Failed to set LED {led_num}")
            log(f"  LED {led_num}: RGB({r},{g},{b})")
            time.sleep(0.2)

        test_pass("LED cycle", "All 7 LEDs set successfully")
        time.sleep(1)  # Let user see the LEDs

        # Turn all LEDs off
        for led_num in range(7):
            fw.set_board_leds(led_num, 0, 0, 0).expect(f"Failed to clear LED {led_num}")
        log("  All LEDs cleared")
    except Exception as e:
        test_fail("LED cycle", str(e))

    # ════════════════════════════════════════════════════
    # 5. Audio Test (play a tone)
    # ════════════════════════════════════════════════════
    log("")
    log("=" * 60)
    log("🔊 TEST 5: Audio Tone")
    log("=" * 60)

    try:
        # Play a 440Hz (A4) tone for 0.5 seconds
        log("  Playing 440Hz tone for 0.5s...")
        fw.play_audio_tone(440, 0.5, 0.5)
        time.sleep(0.6)
        # Play a 880Hz (A5) tone
        log("  Playing 880Hz tone for 0.5s...")
        fw.play_audio_tone(880, 0.5, 0.5)
        time.sleep(0.6)
        test_pass("Audio tone", "Two tones played (440Hz, 880Hz)")
    except Exception as e:
        test_fail("Audio tone", str(e))

    # ════════════════════════════════════════════════════
    # 6. WilEye Camera Test
    # ════════════════════════════════════════════════════
    log("")
    log("=" * 60)
    log("📷 TEST 6: WilEye Camera (ESP32-P4-EYE)")
    log("=" * 60)

    try:
        # Use main_serial for WilEye commands
        cam = fw.main_serial if hasattr(fw, 'main_serial') else fw

        log("  Taking test photo...")
        result = cam.wileye_take_picture(0, "hw_test_photo.jpg")
        if result.is_ok():
            test_pass("Camera photo", "Photo captured as hw_test_photo.jpg")
        else:
            err = result.unwrap_err()
            test_fail("Camera photo", f"Failed: {err}")
    except AttributeError:
        # Try directly on the device object
        try:
            result = fw.wileye_take_picture(0, "hw_test_photo.jpg")
            if result.is_ok():
                test_pass("Camera photo", "Photo captured as hw_test_photo.jpg")
            else:
                test_fail("Camera photo", f"Failed: {result.unwrap_err()}")
        except Exception as e2:
            test_fail("Camera photo", str(e2))
    except Exception as e:
        test_fail("Camera photo", str(e))

    # ════════════════════════════════════════════════════
    # 7. App Info
    # ════════════════════════════════════════════════════
    log("")
    log("=" * 60)
    log("ℹ️  TEST 7: Device Info")
    log("=" * 60)

    try:
        app_info = fw.get_app_info().expect("Failed to get app info")
        log(f"  App info: {app_info}")
        test_pass("Device info", str(app_info))
    except Exception as e:
        test_fail("Device info", str(e))

    try:
        uid = fw.unique_id().expect("Failed to get unique ID")
        log(f"  Unique ID: {uid}")
        test_pass("Unique ID", str(uid))
    except Exception as e:
        test_fail("Unique ID", str(e))

finally:
    # Always close the connection
    fw.close()
    log("\n🔒 Connection closed")

# ════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════
log("")
log("=" * 60)
log("📊 TEST SUMMARY")
log("=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
skipped = sum(1 for r in results if r[0] == "SKIP")
total = len(results)

for status, name, detail in results:
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️ "}[status]
    suffix = f" — {detail}" if detail else ""
    log(f"  {icon} {name}{suffix}")

log("")
log(f"  Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
if failed == 0:
    log("  🎉 All tests passed!")
else:
    log(f"  ⚠️  {failed} test(s) failed")
