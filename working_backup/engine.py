"""Main game engine orchestrating state, agents, announcer, and display."""
import time
import random
import os
import pathlib

from freewili import FreeWili
from freewili.types import ButtonColor, FreeWiliProcessorType
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
            
            # Record audio snippet
            self.announcer.speak("Now, please say your name and a short sentence.")
            stmt = self._get_human_speech(p, "Registration")
            p.voice_profile_id = f"voice_{p.name}.wav"
            self.state.log(f"Recorded voice sample for {p.name}: {stmt}")
            
            display.flash_leds(self.fw, 0, 25, 0, count=1) 
            time.sleep(1)

        # ROLE REVEAL
        for p in human_players:
            p.role = Role.MAFIA
            display.render_main_display(self.fw, self.state, "PRIVATE REVEAL: YOU ARE MAFIA. Press GREEN to hide.")
            display.set_role_leds(self.fw, p.role)
            while True:
                try:
                    btns = self.fw.read_all_buttons().expect("Buttons fail")
                    if btns.get(ButtonColor.Green, False): break
                except: pass
                time.sleep(0.1)
            display.clear_leds(self.fw)
            display.render_main_display(self.fw, self.state, "Role Hidden.")
            time.sleep(1)

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
                    self.state.log(f"Player {p.name} (Human): {stmt}")
            time.sleep(0.5)

    def _get_human_speech(self, p: Player, prompt_msg: str) -> str:
        """Hande PTT (Push-To-Talk) logic for human players using MAIN CPU mic."""
        display.render_main_display(self.fw, self.state, f"HOLD [GREEN]: {prompt_msg}", active_player=p)
        
        # Wait for Press
        while True:
            try:
                btns = self.fw.read_all_buttons().expect("Buttons fail")
                if btns.get(ButtonColor.Green, False): break
            except: pass
            time.sleep(0.05)
            
        # Start LEDs
        for i in range(7):
            self.fw.set_board_leds(i, 20, 20, 20)
            
        wav_remote = f"speech_{p.name}.wav"
        print(f"[Speech] Recording to MAIN: {wav_remote}")
        
        # BYPASS BUGGY WRAPPER - Call serial directly (AS SEEN IN 11:30 PM COMMIT)
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
            try:
                btns = self.fw.read_all_buttons().expect("Buttons fail")
                if not btns.get(ButtonColor.Green, False): break
            except: pass
            time.sleep(0.05)
            
        # STOP RECORDING
        try:
            if self.fw.main_serial:
                self.fw.main_serial.serial_port.send("\n")
                time.sleep(0.1)
        except: pass

        display.clear_leds(self.fw)
        if not success: return "[Mic Error]"

        print("[Speech] Finalizing recording...")
        time.sleep(2.5)
        
        local_wav = f"temp_human_{p.name}.wav"
        if os.path.exists(local_wav): 
            try: os.remove(local_wav)
            except: pass
        
        print(f"[Speech] Fetching {wav_remote} to {local_wav}...")
        try:
            if self.fw.main_serial:
                import pathlib
                res = self.fw.main_serial.get_file(wav_remote, pathlib.Path(local_wav), None)
                if res.is_err():
                    print(f"[Speech Error] get_file failed: {res.err_value}")
        except Exception as e:
            print(f"[Speech Error] get_file exception: {e}")
        
        start_wait = time.time()
        while not os.path.exists(local_wav) and time.time() - start_wait < 5:
            time.sleep(0.5)
            
        if not os.path.exists(local_wav) or os.path.getsize(local_wav) == 0:
            print(f"[Speech Error] File empty.")
            return "[Silence]"
            
        return self.transcriber.transcribe(local_wav)

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
        
        self.announcer.speak("Mafia, wake up. Conspire with your partners.")
        time.sleep(1)
        
        # Human Mafia Turn
        for p in self.state.mafia_players():
            if not p.is_ai:
                display.set_role_leds(self.fw, p.role)
                stmt = self._get_human_speech(p, "Conspire with partner")
                if stmt:
                    self.state.log(f"Player {p.name} (Mafia/Human): {stmt}")
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
        
        # 4. Townsfolk Actions
        for p in self.state.town_players():
            if p.role in (Role.DOCTOR, Role.DETECTIVE) or not p.is_ai: continue
            display.render_main_display(self.fw, self.state, "Sleeping...", active_player=p)
            result = self.agents[p.name].night_action(context)
            self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
            
        if mafia_votes:
            self.state.night_actions.mafia_target = sorted(mafia_votes.items(), key=lambda x: x[1], reverse=True)[0][0]

    def resolve_night(self):
        victim_name = self.state.night_actions.mafia_target
        saved_name = self.state.night_actions.doctor_save
        
        self.state.phase = GamePhase.DAY_DISCUSSION
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

    def run_day_discussion(self, rounds: int = 1):
        context = f"Day {self.state.turn} begins. Players alive: {', '.join(p.name for p in self.state.living_players())}"
        self.state.reset_daily_talk_counts()
        
        for r_idx in range(rounds):
            speakers = self.state.living_players()
            random.shuffle(speakers)
            for p in speakers:
                if not p.is_ai:
                    display.set_role_leds(self.fw, p.role)
                    statement = self._get_human_speech(p, f"Discussion")
                    if statement:
                        self.state.log(f"Player {p.name} (Human): {statement}")
                        display.render_main_display(self.fw, self.state, f"'{statement}'", active_player=p)
                        self.announcer.speak(statement)
                    display.clear_leds(self.fw)
                    continue
                    
                display.render_main_display(self.fw, self.state, f"Thinking...", active_player=p)
                human_transcript = "\n".join([f"{e.message}" for e in self.state.game_log if "Human" in e.message])
                result = self.agents[p.name].day_discussion(context, transcript=human_transcript)
                self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
                statement = result.get('public_statement', '')
                self.state.log(f"{p.name}: {statement}")
                if statement:
                    display.set_role_leds(self.fw, p.role)
                    display.render_main_display(self.fw, self.state, f"'{statement}'", active_player=p)
                    self.announcer.speak(statement, p.voice_id)
                display.clear_leds(self.fw)

    def run_voting(self):
        self.state.phase = GamePhase.DAY_VOTE
        self.announcer.announce_phase("day_vote", self.state.turn)
        display.render_main_display(self.fw, self.state, "Voting Phase")
        
        self.state.votes.clear()
        alive_names = [p.name for p in self.state.living_players()]
        context = f"Voting Phase. You must vote. Options: {', '.join(alive_names)}"
        
        for p in self.state.living_players():
            if not p.is_ai:
                # Human vote simplified
                stmt = self._get_human_speech(p, "Cast your vote")
                for name in alive_names:
                    if name.lower() in stmt.lower():
                        self.state.votes[p.name] = name
                        break
                continue
            
            result = self.agents[p.name].day_vote(context, alive_names)
            target = result.get("action", {}).get("target")
            if target and self.state.get_player(target):
                self.state.votes[p.name] = target
                display.render_main_display(self.fw, self.state, f"I vote for {target}", active_player=p)
                self.announcer.speak(f"I vote for {target}", p.voice_id)
            time.sleep(1)
            
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
                self.announcer.speak("The vote is tied. No one is eliminated today.")

    def run_game_loop(self):
        self.announcer.speak("The game begins.")
        while True:
            winner = self.state.check_win_condition()
            if winner:
                self.state.log(f"GAME OVER! {winner} wins!")
                self.announcer.announce_game_over(winner)
                display.render_main_display(self.fw, self.state, f"{winner} WINS!")
                time.sleep(5)
                break
            self.run_night_phase()
            self.resolve_night()
            winner = self.state.check_win_condition()
            if winner: continue
            self.run_day_discussion(rounds=1)
            self.run_voting()
