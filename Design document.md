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

- **FREE-WILi WiFi capability**: The FREE-WILi board (Black/Red versions) includes Sub-GHz and 2.4GHz radios (e.g., CC1101, CC1352P7) intended for protocol research (Zigbee, Thread), but *does not* have a standard built-in WiFi module for direct internet access. Therefore, the architecture relies on the Host Laptop acting as an API proxy over USB serial to reach the Gemini and ElevenLabs APIs.
- Audio and Display latency depends on serial transfer speeds.

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
- [x] FREE-WILi buttons navigate launcher menu
- [x] Gemini API drives agent reasoning with structured JSON output
- [x] Basic moderator panel (localhost)
- [x] Wristband color signaling for role assignment

### Stretch Goals
- [ ] Mixed human+AI mode with microphone transcription
- [ ] Camera-based facial reaction analysis via Gemini Vision
- [ ] ElevenAgents live conversational voice mode (real-time back-and-forth)
- [ ] Personality persistence and archive system
- [ ] Debug panel with agent thought auditing
- [ ] Additional game modes beyond Mafia
- [ ] Human-only mode (FREE-WILi as pure moderator)

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