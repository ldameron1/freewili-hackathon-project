Note: This repository is entirely vibe-coded.

# 🎭 AI Integrated Social Intrigue Game(s) for FREE-WILi

> Turn the [FREE-WILi](https://freewili.com) embedded platform into an AI-powered social deduction game host — where AI agents think, speak, and scheme alongside human players.

---

## What Is This?

A hackathon project that combines **embedded hardware**, **generative AI**, and **social deduction games** into a portable, self-contained game experience. The FREE-WILi device acts as the game master: it displays game state, speaks AI dialogue, signals player roles via LED wristbands, and even watches human reactions through a camera module.

**First game mode: [Mafia](https://en.wikipedia.org/wiki/Mafia_(party_game))** — 9 players (2 human + 7 AI) compete in a social deduction battle. AI agents reason with Gemini, speak with unique ElevenLabs voices, and display facial expressions on screen.

---

## Hardware

| Component | Purpose |
|-----------|---------|
| [FREE-WILi](https://freewili.com) | Game hub — display, buttons, speaker, mic, LEDs, 433MHz radio |
| [ESP32-P4-EYE](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32p4/esp32-p4-eye/user_guide.html) (WILEYE Camera Orca) | Camera for facial analysis — plugged into FREE-WILi Orca port |
| DEF CON Wristbands (x2) | LED role indicators for human players |
| Host Laptop | Thin API proxy — relays Gemini/ElevenLabs calls over USB |

## Software Stack

| Component | Technology |
|-----------|-----------|
| Game logic (on-device) | C/WASM via [fwwasm SDK](https://github.com/freewili/fwwasm) |
| Hardware I/O (on-device) | WASM display/LED/audio/button/radio APIs |
| API proxy (host) | Python 3.x ([`freewili-python`](https://freewili.github.io/freewili-python/)) |
| AI reasoning | [Gemini API](https://ai.google.dev/gemini-api/docs) (structured JSON) |
| Voice synthesis | [ElevenLabs TTS](https://elevenlabs.io/docs) |
| Speech recognition | Gemini API / Whisper (via FREE-WILi mic) |
| Facial analysis | Gemini Vision API (via WilEye camera) |
| Moderator panel | Localhost web UI |

---

## Architecture

```
┌──────────────────────┐    USB/Serial    ┌───────────────────────┐
│    FREE-WILi         │◄────────────────►│   Host Laptop         │
│                      │                  │                       │
│ WASM Game Engine     │                  │  Python API Proxy     │
│ ├─ Game state machine│  ◄── requests ── │  ├─ Gemini API relay  │
│ ├─ 320x240 LCD       │  ── responses ──►│  ├─ ElevenLabs relay  │
│ ├─ Speaker + Mic     │                  │  ├─ Speech-to-text   │
│ ├─ 5 Buttons         │                  │  └─ Moderator web UI │
│ ├─ 7 LEDs            │                  └───────────────────────┘
│ ├─ 433MHz Radio ─── RF ──► DEF CON Wristbands
│ └─ WilEye Camera (Orca)
└──────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- FREE-WILi connected via USB
- ESP32-P4-EYE connected
- API keys for Gemini and ElevenLabs

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd Hackathon

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
# Create .env with your GEMINI_API_KEY and ELEVENLABS_API_KEY
```

### Run

To run the main Mafia game engine, you must use `sudo` to access the FREE-WILi serial ports, and you must point to the virtual environment's Python to ensure dependencies are found:

```bash
# Run the main game (standard)
sudo ./venv/bin/python3 src/main.py

# Run and skip the hardware menu (auto-start AI-only)
sudo ./venv/bin/python3 src/main.py --skip-menu
```

*Note: Running with `sudo` is required for serial port access on Linux.*

---

## FREE-WILi Audio Rules

These are the working rules for audio on this project. Do not deviate from them unless you re-verify on hardware.

1. Build playback WAVs as `8 kHz`, `mono`, `16-bit PCM`.
2. Upload audio files to the Display processor under `/sounds/`.
3. Play audio by basename only.

Working example:

```python
fw.send_file("/tmp/freewili_tone.wav", "/sounds/tone.wav", processor=FreeWiliProcessorType.Display, chunk_size=4096)
fw.play_audio_file("tone.wav", processor=FreeWiliProcessorType.Display)
```

Non-working pattern seen during debugging:

```python
fw.play_audio_file("/sounds/tone.wav", processor=FreeWiliProcessorType.Display)
```

Additional rules:

1. Keep filenames within the SDK's 8.3 filename expectation.
2. If upload stalls, retry with smaller `send_file(..., chunk_size=4096)` and then `2048`.
3. Kill stale Python processes before hardware tests:

```bash
sudo pkill -9 -f 'src/main.py|hardware_tone_test.py|cleanup_hw.py|test_tts_playback.py|tests/test_tts_playback.py'
```

Canonical code paths in this repo:

1. `hardware_tone_test.py`
2. `src/game/announcer.py`
3. `tests/test_tts_playback.py`

---

## Speech-To-Text Notes

Current STT path:

1. human holds `GREEN`
2. `src/game/engine.py` captures mic samples from FREE-WILi Display audio events
3. audio is written to `/tmp/temp_human_<name>.wav`
4. `src/game/speech.py` uploads that WAV to Gemini and requests transcription

In principle, yes: Gemini STT should work with the current design.

What must be true:

1. `GEMINI_API_KEY` is present
2. FREE-WILi audio events are actually arriving during button-held capture
3. the captured WAV is non-empty and valid
4. Gemini model quota/rate limits are not blocking the request

The main known bug that was removed:

1. old capture path used `get_file()` after on-device recording and failed with `division by zero`
2. current path avoids that by streaming audio events locally instead

---

## Controls (FREE-WILi Buttons)

Orient the device with the FREE-WILi logo on top.

| Button | Color | Function |
|--------|-------|----------|
| ^ | Yellow | Navigate up |
| v | White | Navigate down |
| OK | Green | Select / confirm |
| X | Red | Back / cancel |
| * | Blue | Context-dependent |

---

## Game Modes

| Mode | Players | Status |
|------|---------|--------|
| **AI-only** | 9 AI agents | MVP — for testing and demo |
| **Mixed** | 2 human + 7 AI | MVP — core experience |
| **Human-only** | All human | Stretch — FREE-WILi as moderator |

---

## Project Structure

```
Hackathon/
├── README.md                  # This file
├── Design document.md         # Detailed design specification
├── .gitignore
├── .env                       # API keys (git-ignored)
├── src/
│   └── demo_launcher.py       # Interactive demo for FREE-WILi
├── tests/
│   └── test_hardware.py       # Hardware connectivity tests
├── references/
│   ├── design_document_original.md
│   ├── hardware_references.md
│   └── api_references.md
├── firmware/                  # (future) FREE-WILi WASM modules
└── venv/                      # Python virtual environment (git-ignored)
```

---

## AI Tools Used

- [Google AI Studio](https://aistudio.google.com)
- Google Antigravity
- [Gemini API](https://ai.google.dev) (structured output + vision)
- [ElevenLabs](https://elevenlabs.io) (TTS + ElevenAgents)

---

## References

- [FREE-WILi Documentation](https://docs.freewili.com)
- [Gemini Structured Output](https://ai.google.dev/gemini-api/docs/structured-output)
- [ElevenLabs Conversational AI](https://elevenlabs.io/docs/conversational-ai)
- [ESP32-P4-EYE User Guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32p4/esp32-p4-eye/user_guide.html)

See `references/` directory for detailed hardware and API reference docs.

---

## License

Hackathon project — license TBD.
