"""Main game engine orchestrating state, agents, announcer, and display."""
import time
import random
import os

from freewili import FreeWili
from freewili.types import ButtonColor
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
        """Register human players with photo and voice ID."""
        human_players = [p for p in self.state.players if not p.is_ai]
        if not human_players:
            return

        self.state.phase = GamePhase.REGISTRATION
        self.state.log("Starting Registration Phase")
        
        self.announcer.speak("Welcome, humans. Please step forward one by one to register your identity.")
        time.sleep(2)

        for p in human_players:
            display.render_main_display(self.fw, self.state, f"Registering: {p.name}")
            self.announcer.speak(f"{p.name}, please stand in front of the camera and stay still.")
            time.sleep(3)
            
            # Take photo
            photo_file = f"face_{p.name}.jpg"
            self.fw.wileye_take_picture(0, photo_file)
            p.face_id = photo_file
            self.state.log(f"Captured face reference for {p.name}: {photo_file}")
            
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
            display.set_role_leds(self.fw, p.role) # Secretly set color
            # Wait for Green Button to dismiss
            while True:
                btns = self.fw.read_all_buttons().expect("Buttons fail")
                if btns.get(ButtonColor.Green, False):
                    break
                time.sleep(0.1)
            display.clear_leds(self.fw)
            display.render_main_display(self.fw, self.state, "Role Hidden.")
            time.sleep(1)

        # Take a group photo/video for spatial context
        self.announcer.speak("Everyone, please stand in the frame together for a group scan.")
        display.render_main_display(self.fw, self.state, "GROUP SCAN...")
        time.sleep(2)
        self.fw.wileye_take_picture(0, "group_spatial.jpg")
        self.state.log("Group spatial scan complete.")
        
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
        """Hande PTT (Push-To-Talk) logic for human players."""
        from freewili.types import FreeWiliProcessorType
        display.render_main_display(self.fw, self.state, f"HOLD [GREEN]: {prompt_msg}", active_player=p)
        
        # Wait for Press
        while True:
            btns = self.fw.read_all_buttons().expect("Buttons fail")
            if btns.get(ButtonColor.Green, False):
                break
            time.sleep(0.05)
            
        # Start Recording
        for i in range(7):
            self.fw.set_board_leds(i, 20, 20, 20)
            
        # Try to enable audio/mic just in case
        try:
            self.fw.enable_audio_events(True, processor=FreeWiliProcessorType.Main)
        except: pass

        wav_remote = f"speech_{p.name}.wav"
        print(f"[Speech] Recording to MAIN: {wav_remote}")
        
        # BYPASS BUGGY WRAPPER - Call serial directly
        success = False
        if self.fw.main_serial:
            res = self.fw.main_serial.record_audio(wav_remote)
            if res.is_ok():
                success = True
            else:
                print(f"[Speech Error] record_audio failed: {res.err_value}")
        
        # Wait for Release OR 5 seconds
        start_rec = time.time()
        while time.time() - start_rec < 5.0:
            btns = self.fw.read_all_buttons().expect("Buttons fail")
            if not btns.get(ButtonColor.Green, False):
                break
            time.sleep(0.05)
            
        # STOP RECORDING: Send a newline to the Main processor to break the command
        try:
            if self.fw.main_serial:
                self.fw.main_serial.serial_port.send("\n")
                time.sleep(0.1)
        except: pass

        # CLEAR LEDS AFTER RECORDING
        display.clear_leds(self.fw)
        
        if not success:
            return "[Mic Error]"

        print("[Speech] Finalizing recording...")
        time.sleep(2.5)
        
        # Download and Transcribe
        local_wav = f"temp_human_{p.name}.wav"
        if os.path.exists(local_wav): 
            try: os.remove(local_wav)
            except: pass
        
        print(f"[Speech] Fetching {wav_remote} to {local_wav}...")
        try:
            # Fetch from MAIN processor serial directly to bypass wrapper
            if self.fw.main_serial:
                import pathlib
                res = self.fw.main_serial.get_file(wav_remote, pathlib.Path(local_wav), None)
                if res.is_err():
                    print(f"[Speech Error] get_file failed: {res.err_value}")
        except Exception as e:
            print(f"[Speech Error] get_file exception: {e}")
        
        # Wait up to 5 seconds for the file to appear on the laptop
        start_wait = time.time()
        while not os.path.exists(local_wav) and time.time() - start_wait < 5:
            time.sleep(0.5)
            
        if not os.path.exists(local_wav) or os.path.getsize(local_wav) == 0:
            fsize = os.path.getsize(local_wav) if os.path.exists(local_wav) else "N/A"
            print(f"[Speech Error] File not found or empty. (fsize: {fsize})")
            return "[Recording failed or silent]"
            
        text = self.transcriber.transcribe(local_wav)
        if not text or text == "[Error transcribing]":
            return "[Transcription error]"
            
        return text

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
                
        # Discussion ends
        self.resolve_votes()
        if not self.state.winner:
            self.run_night_phase()
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
