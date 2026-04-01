Note: This repository is entirely vibe-coded, and the read me is out of date (currently only 1 human player is implemented, and some features were cut for time like the camera integration and wristbands.)

# 🎭 AI Integrated Social Intrigue Game(s) for FREE-WILi

> Turn the [FREE-WILi](https://freewili.com) embedded platform into an AI-powered social deduction game host where AI agents think, speak, and scheme alongside human players.

## What This Repo Actually Runs

This repo currently runs a Python host application that drives a FREE-WILi device over USB using `freewili-python`. The active game mode is a Mafia MVP:

- `src/main.py` connects to the device, shows the hardware menu, and starts the moderator web UI.
- `src/game/engine.py` runs the day/night loop, state transitions, human push-to-talk capture, and AI turns.
- `src/game/agents.py` uses Gemini for structured Mafia decisions.
- `src/game/announcer.py` uses ElevenLabs for TTS and sends audio to the FREE-WILi display processor.
- `src/moderator/app.py` serves a small local Flask UI for watching state and logs.

The older README described a future on-device WASM architecture. That is not what this codebase is today. The current implementation is host-driven Python with the FREE-WILi acting as the physical interface.

## Current Status

- `ai_only` and `mixed` are the main playable paths exposed by the startup menu.
- `debug` mode exists to force the human player into Mafia for demos.
- Human speech capture uses FREE-WILi audio events plus Gemini transcription.
- Camera capture and wristband assignment are currently skipped or stubbed in the active flow.
- `working_backup/` contains older experiments and is not part of the active runtime.

## Hardware + Services

### Hardware

- FREE-WILi badge/device
- Host Linux laptop connected over USB
- Speaker, mic, display, LEDs, and buttons on the FREE-WILi
- Optional camera and wristband hardware were part of the hackathon concept, but they are not fully wired into the active runtime path

### Services

- Gemini API for AI player reasoning and speech transcription
- ElevenLabs for text-to-speech
- Flask for the local moderator panel

## Quick Start

### Prerequisites

- Python 3.10+
- A working FREE-WILi connection
- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```env
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
```

### Run The Game

```bash
sudo ./venv/bin/python src/main.py
```

Skip the menu and start AI-only immediately:

```bash
sudo ./venv/bin/python src/main.py --skip-menu
```

The moderator panel is served on `http://localhost:5000`.

## Runtime Architecture

```text
Host Python Runtime
├─ src/main.py
│  ├─ hardware connection/bootstrap
│  ├─ menu selection
│  └─ Flask moderator thread
├─ src/game/engine.py
│  ├─ game state orchestration
│  ├─ human push-to-talk capture
│  ├─ AI turn scheduling
│  └─ phase transitions
├─ src/game/agents.py
│  └─ Gemini-backed structured decisions
├─ src/game/announcer.py
│  └─ ElevenLabs TTS -> FREE-WILi playback
└─ src/moderator/app.py
   └─ local state/log viewer
```

## Canonical Audio Path

FREE-WILi playback is strict. The shared implementation now lives in `src/game/audio.py`.

Rules the code assumes:

1. Build playback WAVs as mono 16-bit PCM.
2. Default playback sample rate is `8 kHz`.
3. Upload to the display processor under `/sounds/`.
4. Play by basename only, not by full device path.

Canonical code paths:

1. `src/game/audio.py`
2. `src/game/announcer.py`
3. `tests/test_tts_playback.py`
4. `src/utils/cleanup_hw.py`

## Speech-To-Text Path

Human speech currently flows like this:

1. The player holds `GREEN`.
2. `src/game/engine.py` streams FREE-WILi audio events while the button is held.
3. The audio is written to `/tmp/temp_human_<name>.wav`.
4. `src/game/speech.py` uploads that WAV to Gemini for transcription.

This replaced an older on-device recording path that was failing during the hackathon.

## Repo Layout

```text
Hackathon/
├── README.md
├── Design document.md
├── audio_config.json
├── requirements.txt
├── src/
│   ├── main.py
│   ├── moderator/
│   ├── game/
│   │   ├── agents.py
│   │   ├── announcer.py
│   │   ├── audio.py
│   │   ├── engine.py
│   │   ├── state.py
│   │   └── display.py
│   ├── assets/sfx/
│   ├── demo/
│   └── utils/
├── tests/
├── references/
└── working_backup/
```

## Useful Commands

Run focused unit tests:

```bash
./venv/bin/python -m unittest tests.test_announcer_audio tests.test_speech
```

Refresh the device audio assets:

```bash
sudo ./venv/bin/python src/utils/cleanup_hw.py --refresh-assets
```

## Notes

- `src/assets/sfx/` is the canonical local SFX directory used by the runtime utilities.
- There are archived or duplicate experiment artifacts in the repo from hackathon development; the active runtime paths are the modules under `src/game/`, `src/main.py`, and `src/moderator/`.
- Some hardware-facing tests require the device and Linux permissions that the unit tests do not.

## References

- [FREE-WILi Documentation](https://docs.freewili.com)
- [Gemini Structured Output](https://ai.google.dev/gemini-api/docs/structured-output)
- [ElevenLabs Docs](https://elevenlabs.io/docs)
- [ESP32-P4-EYE User Guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32p4/esp32-p4-eye/user_guide.html)

## License

Note from hackathon submission day: "Hackathon project — license TBD."
