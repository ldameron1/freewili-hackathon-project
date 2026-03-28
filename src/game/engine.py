"""Main game engine orchestrating state, agents, announcer, and display."""
import time
import random

from freewili import FreeWili
from .state import GameState, Player, Role, GamePhase
from .agents import AIAgent
from .announcer import GameAnnouncer
from . import display


class MafiaEngine:
    def __init__(self, fw: FreeWili):
        self.fw = fw
        self.state = GameState()
        self.announcer = GameAnnouncer(self.fw)
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

    def run_night_phase(self):
        self.state.phase = GamePhase.NIGHT
        self.state.turn += 1
        self.state.night_actions.mafia_target = None
        self.state.night_actions.doctor_save = None
        
        display.render_main_display(self.fw, self.state, "Night falls...")
        self.announcer.announce_phase("night", self.state.turn)
        
        # Build context for agents
        context = f"Night {self.state.turn}. Alive players: {', '.join(p.name for p in self.state.living_players())}"
        
        mafia_votes = {}
        target = None
        
        # Process actions
        for p in self.state.living_players():
            if not p.is_ai:
                continue
                
            agent = self.agents[p.name]
            # Role colors on device for dramatic effect
            display.set_role_leds(self.fw, p.role)
            
            result = agent.night_action(context)
            self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
            
            action = result.get("action", {})
            if action.get("type") == "kill" and p.role == Role.MAFIA:
                target = action.get("target")
                if target: mafia_votes[target] = mafia_votes.get(target, 0) + 1
            elif action.get("type") == "save" and p.role == Role.DOCTOR:
                self.state.night_actions.doctor_save = action.get("target")
            elif action.get("type") == "investigate" and p.role == Role.DETECTIVE:
                investigate_target = action.get("target")
                t_player = self.state.get_player(investigate_target)
                is_mafia = t_player and t_player.role == Role.MAFIA
                self.state.night_actions.detective_result = is_mafia
                self.state.log(f"Detective {p.name} investigated {investigate_target}. Result: {is_mafia}", public=False)
                
            time.sleep(1) # Dramatic pause
            
        display.clear_leds(self.fw)
        
        if mafia_votes:
            # Simple majority or random tiebreak
            self.state.night_actions.mafia_target = sorted(mafia_votes.items(), key=lambda x: x[1], reverse=True)[0][0]

    def resolve_night(self):
        victim_name = self.state.night_actions.mafia_target
        saved_name = self.state.night_actions.doctor_save
        
        self.state.phase = GamePhase.DAY_DISCUSSION
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
            
        display.render_main_display(self.fw, self.state)

    def run_day_discussion(self, rounds: int = 1):
        context = f"Day {self.state.turn} begins. Players alive: {', '.join(p.name for p in self.state.living_players())}"
        
        for _ in range(rounds):
            speakers = self.state.living_players()
            random.shuffle(speakers)
            
            for p in speakers:
                if not p.is_ai:
                    continue
                    
                display.render_main_display(self.fw, self.state, f"{p.name} is speaking...")
                agent = self.agents[p.name]
                result = agent.day_discussion(context)
                
                self.state.log(f"[{p.name}/Thought] {result.get('private_thought')}", public=False)
                statement = result.get('public_statement', '')
                self.state.log(f"{p.name}: {statement}")
                
                if statement:
                    display.render_main_display(self.fw, self.state, f"{p.name}: '{statement}'")
                    self.announcer.speak(statement, p.voice_id)
                time.sleep(2)
                
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
                self.announcer.speak(f"I vote for {target}", p.voice_id)
            else:
                self.state.log(f"{p.name} abstained.")
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
