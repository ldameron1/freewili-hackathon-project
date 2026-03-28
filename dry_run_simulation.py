
import unittest
from unittest.mock import MagicMock, patch
import time
import sys
from types import ModuleType

# 1. Create a fake freewili module with all needed classes/enums
mock_fw_mod = ModuleType("freewili")
mock_fw_types_mod = ModuleType("freewili.types")

class MockFreeWili:
    @staticmethod
    def find_first():
        return MagicMock()
    @staticmethod
    def find_all():
        return []

class MockProcessorType:
    Main = 1
    Display = 2

mock_fw_mod.FreeWili = MockFreeWili
mock_fw_types_mod.FreeWiliProcessorType = MockProcessorType

# Inject into sys.modules
sys.modules["freewili"] = mock_fw_mod
sys.modules["freewili.types"] = mock_fw_types_mod

# 2. Now import the engine
from src.game.engine import MafiaEngine
from src.game.state import GameState, Player, Role, GamePhase, DEFAULT_VOICES

class DryRunSimulation:
    def __init__(self):
        self.fw = MagicMock()
        # Mock result objects for .expect() calls
        ok_res = MagicMock()
        ok_res.is_ok.return_value = True
        ok_res.expect.return_value = {} # for buttons
        ok_res.unwrap.return_value = "Success"
        
        self.fw.open.return_value = ok_res
        self.fw.read_all_buttons.return_value = ok_res
        self.fw.show_text_display.return_value = ok_res
        self.fw.play_audio_tone.return_value = ok_res
        self.fw.wileye_take_picture.return_value = ok_res
        self.fw.send_file.return_value = ok_res
        self.fw.play_audio_file.return_value = ok_res
        self.fw.set_board_leds.return_value = ok_res

    @patch('src.game.engine.GameAnnouncer')
    @patch('src.game.engine.AIAgent')
    @patch('src.game.display.render_main_display')
    @patch('src.game.display.set_role_leds')
    @patch('src.game.display.clear_leds')
    @patch('src.game.display.run_led_countdown')
    @patch('src.game.display.flash_leds')
    def run(self, mock_flash, mock_countdown, mock_clear_leds, mock_set_role_leds, mock_render, mock_agent, mock_announcer):
        print("--- Starting Dry Run Simulation ---")
        
        # Setup engine
        engine = MafiaEngine(self.fw)
        
        # 1. Setup Game
        print("\n[STEP 1] Setting up game...")
        players = [
            Player(name="User", role=Role.TOWN, is_ai=False),
            Player(name="Alice", role=Role.MAFIA, is_ai=True, voice_id=DEFAULT_VOICES[0]),
            Player(name="Bob", role=Role.MAFIA, is_ai=True, voice_id=DEFAULT_VOICES[1]),
            Player(name="Charlie", role=Role.DOCTOR, is_ai=True, voice_id=DEFAULT_VOICES[2]),
            Player(name="Dave", role=Role.DETECTIVE, is_ai=True, voice_id=DEFAULT_VOICES[3]),
        ]
        
        # Mock agent behavior
        mock_agent_inst = MagicMock()
        mock_agent.return_value = mock_agent_inst
        mock_agent_inst.night_action.return_value = {
            "private_thought": "I am doing my job.",
            "public_statement": "",
            "action": {"type": "kill", "target": "User"},
            "emotion": "calm"
        }
        
        engine.setup_game(players)
        print(f"Game Phase: {engine.state.phase.value}")
        
        # 2. Registration Phase
        print("\n[STEP 2] Running Registration Phase...")
        with patch('time.sleep', return_value=None):
            engine.run_registration_phase()
        
        print(f"Game Phase: {engine.state.phase.value}")
        print(f"User Face ID: {engine.state.get_player('User').face_id}")
        
        # 3. Night Phase
        print("\n[STEP 3] Running Night Phase...")
        with patch('time.sleep', return_value=None):
            engine.run_night_phase()
            
        print(f"Game Phase: {engine.state.phase.value}")
        print(f"Turn: {engine.state.turn}")
        print(f"Mafia Target: {engine.state.night_actions.mafia_target}")
        
        print("\n--- Dry Run Successful ---")
        for entry in engine.state.game_log:
            print(f"LOG: {entry.message}")

if __name__ == "__main__":
    sim = DryRunSimulation()
    sim.run()
