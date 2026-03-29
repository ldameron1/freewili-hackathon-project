# AI Integrated Social Intrigue Game(s) for FREE-WILi

## Design Specification

### Overview

A hackathon project that turns the **FREE-WILi** embedded development platform into an AI-powered social deduction game host. The first game mode is **Mafia**, where AI agents (powered by Gemini + ElevenLabs) play alongside human players, with the FREE-WILi acting as the game master, display, and speaker system.

### Hardware

| Component | Role | Connection |
|-----------|------|------------|
| **FREE-WILi** (RP2040 + ICE40 FPGA) | Central hub: display, buttons, speaker, LEDs, radio, game logic | Host via USB |
| **ESP32-P4-EYE** (WILEYE Camera Orca) | Camera for facial reaction analysis of human players | Plugged into FREE-WILi Orca port |
| **DEF CON Wristbands** (×2) | LED role indicators for human players | Controlled via 433MHz radio from FREE-WILi |
| **Host Laptop** | Thin API proxy: forwards Gemini/ElevenLabs calls over USB serial (temporary measure/alternative mode, ideally we want to use the wifi module that's connected to the wili for internet)) | USB to FREE-WILi |

### Software Stack

| Layer | Technology | Runs On |
|-------|-----------|---------|
| **Game logic & state machine** | C/WASM via fwwasm SDK (primary) | FREE-WILi (on-device) |
| **Hardware I/O** | WASM display/LED/audio/button/radio APIs | FREE-WILi (on-device) |
| **API proxy** | Python (`freewili-python`, `google-generativeai`, `elevenlabs`) | Host laptop (thin relay) |
| **AI reasoning** | Gemini API (structured JSON output) | Cloud (via host proxy) |
| **Voice synthesis** | ElevenLabs TTS API | Cloud (via host proxy) |
| **Speech recognition** | Gemini API / Whisper (via host mic or FREE-WILi mic) | Cloud (via host proxy) |
| **Facial analysis** | Gemini Vision API (camera frames from WilEye Orca) | Cloud (via host proxy) |
| **Moderator panel** | Localhost web UI (Flask/FastAPI) | Host laptop |

> **Architecture Principle**: Maximize code running on the FREE-WILi itself. The host laptop acts only as a dumb pipe for cloud API calls (Gemini, ElevenLabs). Game logic, UI rendering, button handling, LED control, audio playback, and radio signaling all execute on-device via WASM. The host receives structured requests over USB serial, calls APIs, and returns results.

### AI Tools Used

- Google AI Studio
- Google Antigravity
- Gemini API (structured output + vision)
- ElevenLabs API (TTS + ElevenAgents)

---

## Button Mapping

The user orients the FREE-WILi with the logo on top. The colored buttons map as follows:

| Button | Color | Function |
|--------|-------|----------|
| Up | Yellow | Move selection up |
| Down | White | Move selection down |
| Select | Green | Enter / confirm |
| Back | Red | Cancel / go back |
| Special | Blue | Context-dependent (e.g., toggle debug mode) |

---

## Mode 1: Mafia (MVP)

### Game Overview

Mafia is a social deduction game. Players are divided into **Town** (uninformed majority) and **Mafia** (informed minority). The game alternates between Night (secret actions) and Day (discussion + voting) phases.

### Player Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| **Total players** | 9 | Adjustable via moderator panel |
| **Humans** | 2 | Assigned FREE-WILi wristbands |
| **AI agents** | 7 | Each with unique personality, voice, and reasoning |

### Roles (Standard 9-Player Setup)

| Role | Count | Faction | Night Ability |
|------|-------|---------|---------------|
| Townsperson | 5 | Town | None |
| Doctor | 1 | Town | Save one player per night (cannot repeat) |
| Detective | 1 | Town | Investigate one player (Mafia yes/no) |
| Mafia | 2 | Mafia | Collectively choose one player to eliminate |

### Game Flow

#### Setup Phase
1. Players are randomly assigned roles
2. Human players cup their hands around their wristband to see role color privately
3. Wristband LED colors map to roles (controlled via FREE-WILi's 433MHz radio)
4. Players sit in a **U-shaped formation** facing the FREE-WILi for camera visibility

#### Night Phase
1. FREE-WILi announces "Night falls" (speaker)
2. Mafia agents deliberate internally (Gemini reasoning) and select a target
3. Doctor agent selects a player to save
4. Detective agent investigates a player
5. All AI decisions are logged to the game history

#### Day Phase
1. FREE-WILi announces the night's outcome (speaker + display)
2. Discussion period: AI agents voice their public statements via ElevenLabs TTS through the FREE-WILi speaker
3. Human speech is captured via FREE-WILi microphone → transcribed → added to all agents' context
4. Nominations, defense, and voting occur
5. Majority vote → execution → role reveal on display

#### Win Conditions
- **Town wins**: All Mafia eliminated
- **Mafia wins**: Mafia count ≥ Town count

### AI Agent Architecture

Each AI agent has:

| Component | Description |
|-----------|-------------|
| **Personality** | Stored profile defining behavior, tone, temperature |
| **Private thoughts** | Internal reasoning chain (visible to moderator only) |
| **Public statements** | Voiced via ElevenLabs TTS through FREE-WILi speaker |
| **Facial expression** | Emoji/SVG reflecting internal state (e.g., nervous but trying to stay calm), displayed on FREE-WILi screen |
| **Unique voice** | Distinct ElevenLabs voice per agent |
| **Game history** | Full conversational and action log |

### AI Agent Personalities & Strategies

Agents use their assigned personalities to dictate their tone, but their structural *strategy* is determined by their assigned role via specific Gemini system prompt instructions:

| Role | Core Strategy |
|------|---------------|
| **Mafia** | **Blend In & Deflect**: Avoid acting like a leader to avoid a target on their back. Subtly agree with townies to build trust. If accused, demand logical reasoning and turn the spotlight onto a third party. Fake-claim a power role only if cornered. |
| **Detective** | **Subtle Guidance**: Use night investigation knowledge to steer town suspicion without explicitly revealing their role (which invites assassination). Example: "I have a very bad feeling about [X]'s inconsistencies." |
| **Doctor** | **Protect the Vocal**: Try to anticipate Mafia targets (usually the most vocal or helpful "Town" players). Avoid self-protection unless absolutely necessary to ensure the survival of town leaders. |
| **Townsperson** | **The Truth-Seeker**: No special powers, so they must ask probing questions. Challenge players who bandwagon votes or change opinions rapidly. Look for logical inconsistencies rather than emotional outbursts. |

**Structured output**: All Gemini responses use [JSON schema enforcement](https://ai.google.dev/gemini-api/docs/structured-output) to ensure parseable actions (vote, accuse, defend, etc.).

### Camera Integration (ESP32-P4-EYE on Orca Port)

- Camera is **plugged into the FREE-WILi's Orca port** (not host USB)
- Accessed via `wileye_take_picture()` / `wileye_start_recording_video()` commands through the FREE-WILi serial API
- Captures frames of human players during discussion
- Frames sent to Gemini Vision API for:
  - **Facial reaction analysis** — informs AI agent reasoning
  - **Speaker identification** — "who is currently talking?" based on lip movement / gestures
  - **Player position mapping** — associates physical seating with game player IDs

### Speech Recognition & Human Player Identification

During open discussion, the system must identify *which* human is speaking:

| Method | How It Works | Priority |
|--------|-------------|----------|
| **Visual (camera)** | Gemini Vision analyzes frames to detect lip movement, gestures, head orientation → maps to player position in U-formation | MVP |
| **Audio (FREE-WILi mic)** | FREE-WILi's onboard mic captures speech → sent to Gemini/Whisper for transcription | MVP |
| **Speaker diarization** | If multiple humans talk, use audio direction or camera to disambiguate who said what | Stretch |
| **Voice enrollment** | At game start, each human says their name → voice profile created for later matching | Stretch |

> **Data flow**: FREE-WILi mic captures audio → sent to host via USB → host calls speech-to-text API → transcription + speaker ID returned to FREE-WILi → injected into all AI agents' game history context.

## System Limitations & Notes

- **FREE-WILi WiFi capability**: While the base FREE-WILi boards use Sub-GHz, this project successfully integrates the **Bottlenose WiFi & BT Orca** module. The device now connects directly to external hotspots (e.g., mobile "Wifi" hotspot) using the `e\w` serial command via the `main.py` setup flow.
- **On-Device Script Storage**: Scripts like `demo_launcher.py` and `main.py` are now persisted on the internal filesystem (`DEMO.PY`, `MAFIA.PY`) as functionality milestones.
- **Latency**: Audio and Display latency depends on serial transfer speeds, optimized by using binary chunking in the `freewili` library.

---

## Play Modes

| Mode | Description | Priority |
|------|-------------|----------|
| **AI-only** | All 9 players are AI agents. For testing and demo. | MVP |
| **Mixed (human + AI)** | 2 humans + 7 AI agents. Core experience. | MVP |
| **Human-only** | All human players, FREE-WILi acts as automated moderator only | Nice-to-have |

---

## Moderator Control Panel

A localhost web UI served from the host laptop.

### Standard Features
- View game log (public events)
- View current phase and alive players
- Manual role assignment override

### Debug Mode (password: "Debug")
- Audit any agent's private thoughts / persona history
- Edit agent personalities and parameters
- Simulate additional FREE-WILi wristbands (for testing without physical bands)
- Save/load personality archives (stored on FREE-WILi, mirrored to host)
- Switch back to standard mode via button

---

## MVP vs. Stretch Goals

### MVP (Must Have)
- [x] AI-only Mafia game running end-to-end
- [x] FREE-WILi display shows game state, agent faces, and text
- [x] FREE-WILi speaker outputs AI agent voices (ElevenLabs TTS)
- [x] FREE-WILi buttons navigate launcher menu (Multi-mode support)
- [x] On-device script persistence (Sync to device milestone)
- [x] Hotspot connectivity via Bottlenose WiFi module
- [x] Gemini API drives agent reasoning with structured JSON output
- [x] Basic moderator panel (localhost)
- [x] Wristband color signaling for role assignment

### Stretch Goals
- [ ] Mixed human+AI mode with microphone transcription
- [ ] Camera-based facial reaction analysis via Gemini Vision
- [ ] ElevenAgents live conversational voice mode (real-time back-and-forth)
- [ ] Personality persistence and archive system
- [ ] Debug panel with agent thought auditing
- [ ] Human-only mode (FREE-WILi as pure moderator)
- [ ] Human-only mode2 (FREE-WILi orchestrates some game rules, but is controled by human moderator)
- [ ] Additional games beyond Mafia
- [ ] **Standalone Hardware Mode**: Entire engine running natively on the FREE-WiLi RP2040 + Bottlenose WiFi module (bypassing the host computer).

### Standalone Hardware Mode (Technical Sketch)
To eventually achieve a fully untethered "Standalone Mode" running exclusively on the FREE-WiLi hardware without a host laptop:
1. **Network Layer**: The Bottlenose WiFi module would manage raw HTTPS TCP sockets natively instead of relying on the host. 
2. **Text Generation**: The embedded firmware would make `POST` requests directly to the Gemini REST API endpoints, parsing the resultant JSON locally using a lightweight C/C++ library (like ArduinoJson or MicroPython's `json`).
3. **Turn-Based Text Override**: Because streaming and decoding real-time ElevenLabs TTS audio objects over SSL requires more RAM buffers than standard microcontrollers possess, this mode would likely downgrade to a **"Text-Only" Turn-Based RPG format**, forcing players to read the physical screen instead of listening to the speaker, maximizing memory overhead for the LLM context histories.
4. **Stripped UI**: The Flask moderator control panel would be abandoned in favor of pure on-device button coordination.

---

## Mafia Ruleset Reference

> Full ruleset preserved below for implementation fidelity.

### Win Conditions
- **Town wins**: All Mafia members eliminated.
- **Mafia wins**: Living Mafia ≥ living Town.

### Roles
- **Townsperson** (Town): No night ability. Votes during Day.
- **Mafia** (Mafia): Collectively choose one player to eliminate at Night.
- **Doctor** (Town): Saves one player per Night. Cannot choose same player twice in a row.
- **Detective** (Town): Investigates one player per Night (Mafia yes/no).

### Phase Cycle (starts with Night 1)

**Night:**
1. Mafia selects elimination target
2. Doctor selects save target
3. Detective investigates one player

**Day:**
1. Moderator reveals night outcome
2. Discussion period
3. Player nominates another (must be seconded)
4. Accused gets 30–60 seconds to defend
5. Vote: strict majority (>50% living) → execution + role reveal

**Edge Cases:**
- No majority reached → collective vote to "Sleep" (no elimination)
- Dead players cannot speak or participate
- After execution or sleep vote → immediately transition to Night
## Current System State (March 28, 2026 - Final Stability Phase)

The project has reached a high-stability milestone with full end-to-end AI-only gameplay on the FREE-WiLi hardware.

### Audio Pipeline (The "Golden" Settings)
*   **Sample Rate**: Consistent **8,000Hz (8kHz)** mono. While lower fidelity, this is the maximum stable throughput for the FREE-WiLi's serial-to-DAC buffer without stuttering.
*   **Digital Gain**: **1.8x boost** applied via a **math.tanh soft-limiter**. This prevents digital clipping clicks (clipping the wave top) by gracefully "squishing" loud syllables.
*   **Anti-Pop/Click Suppression**: 
    *   Added **150ms of zero-padding** to the start/end of every clip.
    *   Applied **20ms amplitude fades** to stop the hardware speaker from "snapping" during power-on/off.
*   **Interrupt Protection**: The `GameAnnouncer` now calculates audio duration and **blocks** Python execution during playback to prevent UART file-transfer interrupts from starving the audio CPU.

### AI Reasoning & Model Fallback
*   **Universal Quota Management**: Implemented a global `MODELS_FALLBACK` chain (Gemini 2.5 → Gemini 2.0 → Gemini Flash → Gemma 3).
*   **Global Sync**: If any single agent hits a 429 Rate Limit, they update a global index, causing all other agents to "fast-forward" to the newest working model instantly.
*   **Gemma Compatibility Layer**: 
    *   **History Injection**: Since Gemma doesn't support the `system_instruction` API parameter, the engine now injects prompts into the conversation `history`.
    *   **JSON Steering**: Added organic JSON templates and a markdown-block (` ```json `) stripper to ensure structured data parsing on models without native JSON-mode.

### Hardware UI & Stability
*   **Flattened Menu**: Replaced the nested menu tree with a single, fast-access `MAFIA MENU` launch screen.
*   **Visual Feedback**: AI characters now display their **ASCII Art Portraits** on the FREE-WiLi screen during the Night Phase while they are "thinking," providing clear state feedback.
*   **Auto-Cleanup**: Added a `psutil` routine that automatically kills rogue/suspended Python processes on startup, preventing "Port already in use" and serial lock errors.

---

## Final Project Milestones met:
- [x] **No-Click Audio**: Clean narrator and character speech.
- [x] **Rate Limit Resilience**: Seamless hopping between 4 different LLM backends.
- [x] **Hardware UX**: Responsive buttons, clear ASCII graphics, and intuitive menus.
- [x] **Serial Reliability**: Zero bus starvation during playback.

### Advanced Hardware & API Optimizations

### 1. The "WilEye RAM-Hack" (PSRAM Expansion)
The FREE-WiLi's RP2040 is constrained by 264KB of RAM, but the **WilEye Camera Module** includes **8MB of external PSRAM**. 
- **Optimization**: By reducing camera resolution, we can repurpose 'spare' PSRAM as a massive dynamic buffer for LLM context history and audio streaming. 
- **Standalone Feasibility**: This 8MB buffer is the key to making the game run without a laptop by allowing the device to cache several minutes of audio and deep conversation histories.

### 2. Narrator "Cold Storage" (Latency Reduction)
- **Problem**: Calling ElevenLabs for every "Night 1 falls..." line adds 2-3 seconds of network latency.
- **Solution**: Pre-synthesize all standard game phase transitions (Night Start, Day Start, Vote Start) into 8kHz WAV files stored in `src/assets/sfx/`.
- **Logic**: The `GameAnnouncer` will check for a local file (e.g., `narrator_night_1.wav`) before calling the remote API.

### 3. The "Chorus" Batching Mode
- **Optimization**: Instead of 9 individual agent calls, the system can combine all AI "thoughts" into a single, structured JSON prompt.
- **Benefit**: Reduces API round-trips from 9 to 1, virtually eliminating 429 "Rate Limit" errors during the hackathon.

---

## 📅 Project History & Milestones

### Milestone: The WilEye RAM-Hack (March 28, 2026)
*   **The Problem**: The RP2040 and ESP32 sub-modules were experiencing buffer overflows during concurrent Camera and Audio Flash-writes.
*   **The Brown-Out Discovery (Critical)**: When the WilEye is stressed to 1080p and attempting heavy I/O, it pulls enough instantaneous current to "brown out" the Bottlenose (WiFi) ESP32 chip on the shared power rail, dropping network connectivity.
*   **The Hack**: Discovered that setting the WilEye (ESP32-S3) resolution to **QVGA (320x240)** or lower via the `e\c\y 0` command reduces both power draw and memory pressure. It frees up ~7MB of PSRAM otherwise reserved for the 1080p frame buffer.
*   **The Fix**: Repurposed this 'spare' PSRAM as a massive filesystem cache and LLM conversation buffer. The lower power draw keeps the WiFi chip stable.
*   **Trade-off**: Camera quality reduced by 4x, but system stability increased by 10x. This is the **required** 'Gold Master' configuration for any Standalone WiFi usage.

### Next Steps for Future Iterations:
1.  **WiFi Standalone**: Migrate the API relay logic onto the Bottlenose ESP32 module itself.
2.  **Voice Diarization**: Implement local human-voice thresholding for the registration phase.
3.  **Radio Expansion**: Fully implement the 433MHz "wristband shuffle" for 2+ humans.
