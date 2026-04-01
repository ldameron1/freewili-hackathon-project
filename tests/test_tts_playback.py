"""
ElevenLabs TTS → FREE-WiLi Audio Playback Test
================================================
Generates a short TTS clip via ElevenLabs, uploads it to the FREE-WiLi,
and plays it on the device speaker.

Run:
    source venv/bin/activate
    python tests/test_tts_playback.py

Optional args:
    --text "Your custom text here"
    --voice VOICE_ID
"""

import os
import sys
import time
import wave
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from src.game.audio import build_freewili_samples, write_mono_wav

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def main():
    parser = argparse.ArgumentParser(description="Test ElevenLabs TTS → FREE-WiLi playback")
    parser.add_argument("--text", default="The town awakens. Night has fallen, and someone has been eliminated.",
                        help="Text to synthesize")
    parser.add_argument("--voice", default="nPczCjzI2devNBz1zQrb",
                        help="ElevenLabs voice ID (default: Brian)")
    args = parser.parse_args()

    log("=" * 55)
    log("🔊 ElevenLabs TTS → FREE-WiLi Playback Test")
    log("=" * 55)

    # ── Step 1: Check API key ──
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        log("❌ ELEVENLABS_API_KEY not set in .env")
        sys.exit(1)
    log(f"✅ API key found ({api_key[:8]}...)")

    # ── Step 2: Generate TTS audio ──
    log(f"Generating TTS for: \"{args.text}\"")
    log(f"Voice ID: {args.voice}")

    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    try:
        audio_generator = client.text_to_speech.convert(
            text=args.text,
            voice_id=args.voice,
            model_id="eleven_multilingual_v2",
            output_format="pcm_16000",  # Raw 16kHz PCM
        )
        audio_bytes = b"".join(audio_generator)
        log(f"✅ TTS generated: {len(audio_bytes)} bytes of PCM data")
    except Exception as e:
        log(f"❌ TTS generation failed: {e}")
        sys.exit(1)

    # ── Step 3: Convert to FREE-WILi-safe 8k WAV ──
    tmp_path = "/tmp/tts_test.wav"
    try:
        playback_samples = build_freewili_samples(audio_bytes)
        write_mono_wav(Path(tmp_path), playback_samples)
        log(f"✅ Saved FREE-WILi 8k WAV to {tmp_path}")
    except Exception as e:
        log(f"❌ Failed saving WAV: {e}")
        sys.exit(1)

    # ── Step 4: Connect to FREE-WiLi ──
    log("Searching for FREE-WiLi...")
    from freewili import FreeWili
    from freewili.types import FreeWiliProcessorType

    try:
        fw = FreeWili.find_first().expect("No FREE-WiLi found!")
    except Exception as e:
        log(f"❌ Could not find FREE-WiLi: {e}")
        sys.exit(1)

    log(f"Found: {fw}")
    fw.open().expect("Failed to open connection")
    log("✅ Connected to FREE-WiLi")

    try:
        # Show status on display
        fw.show_text_display(
            "TTS PLAYBACK TEST\n\n"
            "Uploading audio...\n\n"
            f"Size: {len(audio_bytes)/1024:.1f} KB",
            FreeWiliProcessorType.Display
        )

        # ── Step 5: Upload to FREE-WiLi ──
        # 8.3 filename limit per SDK docs
        target_name = "tts.wav"
        remote_target = f"/sounds/{target_name}"
        log(f"Uploading {tmp_path} → device:{target_name}...")
        upload_start = time.time()
        result = fw.send_file(tmp_path, remote_target, processor=FreeWiliProcessorType.Display)
        upload_time = time.time() - upload_start
        if result.is_ok():
            log(f"✅ Upload complete in {upload_time:.1f}s")
        else:
            err = result.unwrap_err()
            log(f"❌ Upload failed: {err}")
            fw.show_text_display(f"UPLOAD FAILED\n\n{err}", FreeWiliProcessorType.Display)
            time.sleep(3)
            return

        # ── Step 6: Play on device ──
        fw.show_text_display(
            "TTS PLAYBACK TEST\n\n"
            "Playing audio...\n\n"
            f"\"{args.text[:40]}...\"",
            FreeWiliProcessorType.Display
        )

        log(f"Playing {target_name} on device speaker...")
        play_result = fw.play_audio_file(target_name, processor=FreeWiliProcessorType.Display)

        if play_result.is_ok():
            log("✅ Play command sent!")
        else:
            err = play_result.unwrap_err()
            log(f"❌ Play failed: {err}")
            fw.show_text_display(f"PLAY FAILED\n\n{err}", FreeWiliProcessorType.Display)
            time.sleep(3)
            return

        # Give audio time to play (rough estimate: 5 seconds for a short phrase)
        log("Waiting for playback to finish...")
        time.sleep(6)

        fw.show_text_display(
            "TTS PLAYBACK TEST\n\n"
            "Done!\n\n"
            "Audio played\n"
            "successfully.",
            FreeWiliProcessorType.Display
        )
        log("✅ Test complete!")
        time.sleep(2)

    finally:
        fw.reset_display()
        fw.close()
        log("🔒 Disconnected from FREE-WiLi")


if __name__ == "__main__":
    main()
