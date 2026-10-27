"""Offline regression coverage for GitHub issue #1."""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from src.game.dialogue import run_mafia_dialogue
from src.game.state import GamePhase, GameState, Player, Role


def load_isolated_engine():
    """Import the real engine with SDK/service imports replaced by test shims."""
    freewili = types.ModuleType("freewili")
    freewili.FreeWili = type("FreeWili", (), {})
    fw_types = types.ModuleType("freewili.types")
    fw_types.ButtonColor = type("ButtonColor", (), {"Green": "green", "Red": "red"})
    fw_types.EventType = type("EventType", (), {"Audio": "audio"})
    fw_types.AudioData = type("AudioData", (), {})
    agents = types.ModuleType("src.game.agents")
    agents.AIAgent = type("AIAgent", (), {})
    announcer = types.ModuleType("src.game.announcer")
    announcer.GameAnnouncer = type("GameAnnouncer", (), {})
    speech = types.ModuleType("src.game.speech")
    speech.SpeechTranscriber = type("SpeechTranscriber", (), {})
    display = types.ModuleType("src.game.display")
    for name in (
        "render_main_display", "set_role_leds", "clear_leds",
        "run_led_countdown", "flash_leds"
    ):
        setattr(display, name, Mock())

    module_name = "src.game._issue1_isolated_engine"
    engine_path = Path(__file__).resolve().parents[1] / "src/game/engine.py"
    spec = importlib.util.spec_from_file_location(module_name, engine_path)
    module = importlib.util.module_from_spec(spec)
    shims = {
        "freewili": freewili,
        "freewili.types": fw_types,
        "src.game.agents": agents,
        "src.game.announcer": announcer,
        "src.game.speech": speech,
        "src.game.display": display,
    }
    with patch.dict(sys.modules, shims):
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)
    return module, display


class DialogueTests(unittest.TestCase):
    def test_repeats_up_to_maximum(self):
        capture = Mock(side_effect=["first", "second", "third", "fourth"])
        replies = Mock()
        self.assertEqual(run_mafia_dialogue(capture, replies, max_turns=3), 3)
        self.assertEqual([c.args[0] for c in replies.call_args_list], ["first", "second", "third"])
        self.assertEqual(capture.call_count, 3)

    def test_red_ends_without_forcing_another_turn(self):
        capture = Mock(side_effect=["first", None, "unreachable"])
        replies = Mock()
        self.assertEqual(run_mafia_dialogue(capture, replies), 1)
        self.assertEqual(capture.call_count, 2)
        replies.assert_called_once_with("first")

    def test_failed_transcriptions_do_not_reach_ai(self):
        replies = Mock()
        count = run_mafia_dialogue(
            Mock(side_effect=["[Recording failed or silent]", "[Silence]", "actual reply"]),
            replies,
        )
        self.assertEqual(count, 1)
        replies.assert_called_once_with("actual reply")

    def test_rejects_invalid_budget(self):
        with self.assertRaises(ValueError):
            run_mafia_dialogue(Mock(), Mock(), max_turns=0)


class VisibilityTests(unittest.TestCase):
    def test_only_public_daytime_human_speech_is_shared(self):
        state = GameState()
        state.phase = GamePhase.NIGHT
        state.log("User (Mafia/Human): SECRET", public=False)
        state.log("User (Mafia/Human): MISCLASSIFIED PUBLIC")
        state.phase = GamePhase.DAY_DISCUSSION
        state.log("User (Human): Public discussion")
        state.log("Detective/Thought: private", public=False)
        state.log("User (Human): Hidden statement", public=False)
        self.assertEqual(state.public_day_human_transcript(), "User (Human): Public discussion")


class EngineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.module, self.display = load_isolated_engine()
        self.engine = object.__new__(self.module.MafiaEngine)
        self.engine.fw = MagicMock()
        self.engine.announcer = MagicMock()
        self.engine.state = GameState(players=[
            Player("User", Role.MAFIA, is_ai=False),
            Player("Ally", Role.MAFIA, is_ai=True, voice_id="ally"),
            Player("Detective", Role.DETECTIVE, is_ai=True),
            Player("Villager", Role.TOWN, is_ai=True),
        ])
        self.engine.agents = {
            name: MagicMock() for name in ("Ally", "Detective", "Villager")
        }
        for agent in self.engine.agents.values():
            agent.night_action.return_value = {"action": {"type": "none", "target": ""}, "private_thought": ""}
            agent.day_discussion.return_value = {"public_statement": "public", "private_thought": ""}
        self.engine.agents["Ally"].react_to_event.return_value = {"public_statement": "secret reply"}

    def test_two_mafia_exchanges_remain_private_and_do_not_reach_detective(self):
        self.engine._get_human_speech = Mock(side_effect=["secret one", "secret two", None])
        with patch.object(self.module.time, "sleep"), patch.object(self.module.random, "shuffle"):
            self.engine.run_night_phase()

        self.assertEqual(self.engine.agents["Ally"].react_to_event.call_count, 2)
        self.assertEqual(self.engine._get_human_speech.call_count, 3)
        self.assertTrue(all(c.kwargs["allow_skip"] for c in self.engine._get_human_speech.call_args_list))
        mafia_lines = [e for e in self.engine.state.game_log if "(Mafia/" in e.message]
        self.assertEqual(len(mafia_lines), 4)
        self.assertTrue(all(not e.public for e in mafia_lines))

        self.engine.state.phase = GamePhase.DAY_DISCUSSION
        self.engine._get_human_speech = Mock(return_value="I suspect Villager")
        with patch.object(self.module.time, "sleep"), patch.object(self.module.random, "shuffle"):
            self.engine.run_day_discussion(rounds=1)

        detective_call = self.engine.agents["Detective"].day_discussion.call_args
        self.assertEqual(detective_call.kwargs["transcript"], "User (Human): I suspect Villager")
        self.assertNotIn("secret", detective_call.kwargs["transcript"])

    def test_red_cancels_recording_before_enabling_audio_events(self):
        self.engine.fw.read_all_buttons.return_value.expect.return_value = {
            "green": False, "red": True
        }
        self.assertIsNone(self.engine._capture_push_to_talk_audio(allow_skip=True))
        self.engine.fw.enable_audio_events.assert_not_called()


if __name__ == "__main__":
    unittest.main()
