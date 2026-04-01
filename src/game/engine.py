"""Main game engine orchestrating state, agents, announcer, and display."""
import time
import random
import os
import struct
import wave

from freewili import FreeWili
from freewili.types import AudioData, ButtonColor, EventType
from .state import GameState, Player, Role, GamePhase
from .agents import AIAgent
from .announcer import GameAnnouncer
from . import display
from .speech import SpeechTranscriber



class MafiaEngine:
    def __init__(self, fw: FreeWili):
        self.fw = fw
        self.state = GameState()
        self.announcer = GameAnnouncer(self.fw)
        self.transcriber = SpeechTranscriber()
        self.agents: dict[str, AIAgent] = {}
        
    def setup_game(self, players: list[Player]):
        """Reset engine state and construct AI agents for the new roster."""
        self.state.players = players
        self.state.phase = GamePhase.LOBBY
        self.state.turn = 0
        self.state.game_log.clear()
        
        # Init agents
        mafia_names = [p.name for p in players if p.role == Role.MAFIA]
        for p in players:
            if p.is_ai:
                self.agents[p.name] = AIAgent(p, mafia_allies=mafia_names if p.role == Role.MAFIA else None)
        
        display.render_main_display(self.fw, self.state, "Game Initialized")
        self.state.log("Game initialized with {} players".format(len(players)))

        # Wristband assignment (DISABLED FOR DEMO)
        """
        human_players = [p for p in players if not p.is_ai]
        if human_players:
            COLORS = ["Red", "Blue", "Green", "Yellow", "Purple", "Cyan", "White"]
            ...
        """
        self.state.log("Skipping wristband setup.")

    def run_registration_phase(self):
        """Register human players without camera or wristband dependencies."""
        human_players = [p for p in self.state.players if not p.is_ai]
        if not human_players:
            return

        self.state.phase = GamePhase.REGISTRATION
        self.state.log("Starting Registration Phase")
        
        self.announcer.speak("Welcome, humans. Please step forward one by one to register your identity.")
        time.sleep(2)

        for p in human_players:
            display.render_main_display(self.fw, self.state, f"Registering: {p.name}")
            self.announcer.speak(f"{p.name}, get ready to say your name and a short sentence.")
            time.sleep(1)
            p.face_id = ""
            self.state.log(f"Skipping camera capture for {p.name}")
            
            # Record audio snippet for voice diarization
            self.announcer.speak("Now, please say your name and a short sentence.")
            display.render_main_display(self.fw, self.state, f"{p.name}: Speaking...")
            time.sleep(1) # wait for them to start
            
            # Record 3 seconds to device
            # Note: We need a way to trigger recording from main CPU
            # if the SDK supports it. Assuming a placeholder for now.
            try:
                # if hasattr(self.fw, 'record_audio'):
                #    self.fw.record_audio(f"voice_{p.name}.wav", 3.0)
                pass
            except Exception:
                pass
                
            p.voice_profile_id = f"voice_{p.name}.wav"
            self.state.log(f"Recorded voice sample for {p.name}")
            
            display.flash_leds(self.fw, 0, 25, 0, count=1) # Confirm
            time.sleep(1)

        # ROLE REVEAL (FORCED MAFIA FOR DEMO)
        for p in human_players:
            p.role = Role.MAFIA
            display.render_main_display(self.fw, self.state, "PRIVATE REVEAL: YOU ARE MAFIA. Press GREEN to hide.")
            # Wait for Green Button to dismiss
            while True:
                btns = self.fw.read_all_buttons().expect("Buttons fail")
                if btns.get(ButtonColor.Green, False):
                    break
                time.sleep(0.1)
            display.render_main_display(self.fw, self.state, "Role Hidden.")
            time.sleep(1)

        self.state.log("Skipping group camera scan.")
        
        self.announcer.speak("Registration complete. Let the games begin.")
        display.render_main_display(self.fw, self.state, "Ready to Play")
        time.sleep(2)

    def run_intro_phase(self):
        """Allow each player to introduce themselves."""
        self.state.phase = GamePhase.LOBBY
        self.state.log("Starting Introduction Phase")
        self.announcer.speak("Before we begin, let everyone introduce themselves.")
        time.sleep(1)

        for p in self.state.players:
            display.render_main_display(self.fw, self.state, f"Intro: {p.name}", active_player=p)
            if p.is_ai:
                intro_msg = f"Hello, I am {p.name}. {p.personality}"
                self.state.log(f"{p.name}: {intro_msg}")
                self.announcer.speak(intro_msg, p.voice_id)
            else:
                self.announcer.speak(f"{p.name}, please introduce yourself to the group.")
                stmt = self._get_human_speech(p, "Introduce yourself")
                if stmt:
                    self.state.log(f"{p.name} (Human): {stmt}")
            time.sleep(0.5)

    def _get_human_speech(self, p: Player, prompt_msg: str) -> str:
        """Capture a single push-to-talk turn and return the transcript text."""
        # --- SIMULATION FALLBACK ---
        # If we have a proof file locally, we can skip the hardware loop to test transcription
        if os.path.exists("final_captured_proof.wav"):
            print("[SIMULATION] Using final_captured_proof.wav for human speech.")
            time.sleep(1.0)
            return self.transcriber.transcribe("final_captured_proof.wav")

        display.render_main_display(self.fw, self.state, f"HOLD [GREEN]: {prompt_msg}", active_player=p)
        captured_audio = self._capture_push_to_talk_audio()

        display.clear_leds(self.fw)
        print("[Speech] Finalizing...")
        time.sleep(0.2)
        
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in p.name.lower())
        local_wav = f"/tmp/temp_human_{safe_name}.wav"
        if os.path.exists(local_wav): 
            try: os.remove(local_wav)
            except: pass

        if not captured_audio:
            return "[Recording failed or silent]"

        try:
            self._write_captured_wav(local_wav, captured_audio)
        except Exception as e:
            print(f"[Speech Error] writing wav: {e}")
            return "[Recording failed or silent]"

        if os.path.getsize(local_wav) == 0:
            return "[Recording failed or silent]"

        transcript = self.transcriber.transcribe(local_wav)
        if not transcript or transcript == "[Error transcribing]":
            return "[Transcription error]"
        return transcript

    def _capture_push_to_talk_audio(self, max_duration_sec: float = 5.0) -> list[list[int]]:
        """Stream raw mic samples while GREEN is held on the device."""
        while True:
            btns = self.fw.read_all_buttons().expect("Buttons fail")
            if btns.get(ButtonColor.Green, False):
                break
            time.sleep(0.05)

        for i in range(7):
            self.fw.set_board_leds(i, 20, 20, 20)

        captured_audio: list[list[int]] = []

        def event_handler(event_type, _frame, data):
            if event_type == EventType.Audio and isinstance(data, AudioData):
                captured_audio.append(data.data)

        self.fw.set_event_callback(event_handler)
        try:
            self.fw.enable_audio_events(True).expect("Audio events fail")
        except Exception as exc:
            print(f"[Speech Error] enable_audio_events: {exc}")
            self.fw.set_event_callback(None)
            return []

        print("[Speech] Recording from DISPLAY audio events...")
        start_rec = time.time()
        while time.time() - start_rec < max_duration_sec:
            try:
                self.fw.process_events()
            except Exception as exc:
                print(f"[Speech Error] process_events: {exc}")
            btns = self.fw.read_all_buttons().expect("Buttons fail")
            if not btns.get(ButtonColor.Green, False):
                break
            if time.time() - start_rec < 0.35:
                captured_audio.clear()
            time.sleep(0.02)

        try:
            self.fw.enable_audio_events(False).expect("Disable audio events fail")
        except Exception:
            pass
        self.fw.set_event_callback(None)
        return captured_audio

    @staticmethod
    def _write_captured_wav(local_wav: str, captured_audio: list[list[int]]) -> None:
        """Persist captured audio-event chunks to a mono 8 kHz WAV."""
        with wave.open(local_wav, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            for chunk in captured_audio:
                audio_bytes = b"".join(struct.pack("<h", sample) for sample in chunk)
                wav_file.writeframes(audio_bytes)

    def run_night_phase(self):
        self.state.phase = GamePhase.NIGHT
        self.state.turn += 1
        self.state.night_actions.mafia_target = None
        self.state.night_actions.doctor_save = None
        
        display.render_main_display(self.fw, self.state, "Night falls...")
        self.announcer.announce_phase("night", self.state.turn)
        time.sleep(1)
        
        mafia_votes = {}
        context = f"Night {self.state.turn}. Alive players: {', '.join(p.name for p in self.state.living_players())}"
        
        # 1. Mafia Action & Deliberation
        self.announcer.speak("Mafia, wake up. Conspire with your partners.")
        time.sleep(1)
        
        # Human Mafia Turn
        for p in self.state.mafia_players():
            if not p.is_ai:
                display.set_role_leds(self.fw, p.role)
                stmt = self._get_human_speech(p, "Conspire with partner")
                if stmt:
                    self.state.log(f"{p.name} (Mafia/Human): {stmt}")
                    # AI Mafia reaction
                    mafia_partners = [x for x in self.state.mafia_players() if x.is_ai]
                    for partner in mafia_partners:
                        display.render_main_display(self.fw, self.state, "Thinking...", active_player=partner)
                        res = self.agents[partner.name].react_to_event(f"Partner {p.name} said: {stmt}")
                        reply = res.get("public_statement", "")
                        if reply:
                            self.state.log(f"{partner.name} (Mafia/AI): {reply}")
                            display.render_main_display(self.fw, self.state, f"'{reply}'", active_player=partner)
                            self.announcer.speak(reply, partner.voice_id)
                display.clear_leds(self.fw)

        for p in self.state.mafia_players():
            if not p.is_ai: continue
            display.set_role_leds(self.fw, p.role)
            display.render_main_display(self.fw, self.state, "Thinking...", active_player=p)
            result = self.agents[p.name].night_action(context)
            self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
            action = result.get("action", {})
            if action.get("type") == "kill":
                target = action.get("target")
                if target: mafia_votes[target] = mafia_votes.get(target, 0) + 1
            time.sleep(1)
        display.clear_leds(self.fw)
        
        # 2. Detective Action
        self.announcer.speak("Detective, wake up and choose someone to investigate.")
        time.sleep(1)
        for p in [x for x in self.state.living_players() if x.role == Role.DETECTIVE]:
            if not p.is_ai: continue
            display.set_role_leds(self.fw, p.role)
            display.render_main_display(self.fw, self.state, "Investigating suspects...", active_player=p)
            result = self.agents[p.name].night_action(context)
            self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
            action = result.get("action", {})
            if action.get("type") == "investigate":
                investigate_target = action.get("target")
                t_player = self.state.get_player(investigate_target)
                is_mafia = t_player and t_player.role == Role.MAFIA
                self.state.night_actions.detective_result = is_mafia
                self.state.log(f"Detective {p.name} investigated {investigate_target}. Result: {is_mafia}", public=False)
            time.sleep(1)
        display.clear_leds(self.fw)
        
        # 3. Doctor Action
        self.announcer.speak("Doctor, wake up and choose someone to save.")
        time.sleep(1)
        for p in [x for x in self.state.living_players() if x.role == Role.DOCTOR]:
            if not p.is_ai: continue
            display.set_role_leds(self.fw, p.role)
            display.render_main_display(self.fw, self.state, "Choosing who to save...", active_player=p)
            result = self.agents[p.name].night_action(context)
            self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
            action = result.get("action", {})
            if action.get("type") == "save":
                self.state.night_actions.doctor_save = action.get("target")
            time.sleep(1)
        display.clear_leds(self.fw)
        
        # 4. Townsfolk Actions (Background thoughts)
        for p in self.state.town_players():
            if p.role in (Role.DOCTOR, Role.DETECTIVE) or not p.is_ai: continue
            display.render_main_display(self.fw, self.state, "Sleeping...", active_player=p)
            result = self.agents[p.name].night_action(context)
            self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
            
        if mafia_votes:
            # Simple majority or random tiebreak
            self.state.night_actions.mafia_target = sorted(mafia_votes.items(), key=lambda x: x[1], reverse=True)[0][0]

    def resolve_night(self):
        victim_name = self.state.night_actions.mafia_target
        saved_name = self.state.night_actions.doctor_save
        
        self.state.phase = GamePhase.DAY_DISCUSSION
        # Update display immediately before narrator blocks with audio
        display.render_main_display(self.fw, self.state)
        self.announcer.announce_phase("day_discussion", self.state.turn)
        
        if victim_name and victim_name.lower() != str(saved_name).lower():
            victim = self.state.get_player(victim_name)
            if victim and victim.alive:
                victim.alive = False
                self.state.log(f"Tragedy! {victim.name} was killed in the night.")
                self.announcer.announce_death(victim.name, victim.role.value)
            else:
                self.announcer.announce_no_death()
        else:
            self.state.log("No one died in the night.")
            self.announcer.announce_no_death()

    def run_day_discussion(self, rounds: int = 5):
        """Run the daytime discussion rounds before the separate voting phase."""
        context = f"Day {self.state.turn} begins. Players alive: {', '.join(p.name for p in self.state.living_players())}"
        
        # Reset turns for the day
        self.state.reset_daily_talk_counts()
        
        for r_idx in range(rounds):
            self.state.log(f"--- Round {r_idx + 1} of Discussion ---")
            speakers = self.state.living_players()
            random.shuffle(speakers)
            
            for p in speakers:
                # Check talk budget
                if p.talk_count >= 5:
                    continue

                if not p.is_ai:
                    display.set_role_leds(self.fw, p.role)
                    # Human turn using PTT
                    statement = self._get_human_speech(p, f"Discussion ({p.talk_count+1}/5)")
                    p.talk_count += 1
                    
                    if statement:
                        self.state.log(f"{p.name} (Human): {statement}")
                        display.render_main_display(self.fw, self.state, f"'{statement}'", active_player=p)
                        self.announcer.speak(statement)
                    time.sleep(1)
                    display.clear_leds(self.fw)
                    continue
                    
                # AI turn
                display.render_main_display(self.fw, self.state, f"Composing statement...", active_player=p)
                agent = self.agents[p.name]
                
                # Collect human transcripts for AI context
                human_transcript = "\n".join([f"{e.message}" for e in self.state.game_log if "Human" in e.message])
                result = agent.day_discussion(context, transcript=human_transcript)
                
                self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
                statement = result.get('public_statement', '')
                self.state.log(f"{p.name}: {statement}")
                p.talk_count += 1
                
                if statement:
                    display.set_role_leds(self.fw, p.role)
                    display.render_main_display(self.fw, self.state, f"'{statement}'", active_player=p)
                    self.announcer.speak(statement, p.voice_id)
                time.sleep(1)
                display.clear_leds(self.fw)
                
        # Run visual countdown to indicate discussion ending
        self.announcer.speak("Time is running out. Ten seconds remain.")
        display.run_led_countdown(self.fw, 10)

    def run_voting(self):
        self.state.phase = GamePhase.DAY_VOTE
        self.announcer.announce_phase("day_vote", self.state.turn)
        display.render_main_display(self.fw, self.state, "Voting Phase")
        
        self.state.votes.clear()
        alive_names = [p.name for p in self.state.living_players()]
        context = f"Voting Phase. You must vote. Options: {', '.join(alive_names)}"
        
        for p in self.state.living_players():
            if not p.is_ai:
                continue
            
            agent = self.agents[p.name]
            result = agent.day_vote(context, alive_names)
            target = result.get("action", {}).get("target")
            
            if target and self.state.get_player(target):
                self.state.votes[p.name] = target
                self.state.log(f"{p.name} voted for {target}")
                display.render_main_display(self.fw, self.state, f"I vote for {target}", active_player=p)
                self.announcer.speak(f"I vote for {target}", p.voice_id)
            else:
                self.state.log(f"{p.name} abstained.")
                display.render_main_display(self.fw, self.state, "I abstain.", active_player=p)
                self.announcer.speak("I abstain.", p.voice_id)
                
            time.sleep(1)
            
        # Tally
        vote_counts = {}
        for target in self.state.votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1
            
        if vote_counts:
            highest_votes = max(vote_counts.values())
            tied = [t for t, c in vote_counts.items() if c == highest_votes]
            
            if len(tied) == 1:
                eliminated = self.state.get_player(tied[0])
                if eliminated:
                    eliminated.alive = False
                    self.state.log(f"{eliminated.name} was voted out.")
                    self.announcer.announce_eliminated(eliminated.name, eliminated.role.value)
            else:
                self.state.log("The vote was tied. No one is eliminated.")
                self.announcer.speak("The vote is tied. No one is eliminated today.")
        else:
            self.state.log("No votes cast.")

    def run_game_loop(self):
        # Initial role announcements (private logic, we skip audio for town so we don't leak)
        self.announcer.speak("The game begins.")
        
        while True:
            winner = self.state.check_win_condition()
            if winner:
                self.state.phase = GamePhase.GAME_OVER
                self.state.winner = winner
                self.state.log(f"GAME OVER! {winner} wins!")
                self.announcer.announce_game_over(winner)
                display.render_main_display(self.fw, self.state, f"Winner: {winner}")
                
                # Flash correct side's colors
                display.set_role_leds(self.fw, Role.TOWN if winner == "Town" else Role.MAFIA)
                time.sleep(5)
                display.clear_leds(self.fw)
                break
                
            self.run_night_phase()
            self.resolve_night()
            
            winner = self.state.check_win_condition()
            if winner: continue
            
            self.run_day_discussion(rounds=1)
            self.run_voting()
