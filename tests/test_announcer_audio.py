import importlib
import os
import struct
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch


mock_fw_module = types.ModuleType("freewili")
mock_fw_types_module = types.ModuleType("freewili.types")


class MockFreeWili:
    pass


class MockProcessorType:
    Display = "display"


mock_fw_module.FreeWili = MockFreeWili
mock_fw_types_module.FreeWiliProcessorType = MockProcessorType

sys.modules["freewili"] = mock_fw_module
sys.modules["freewili.types"] = mock_fw_types_module

announcer_module = importlib.import_module("src.game.announcer")
audio_module = importlib.import_module("src.game.audio")
GameAnnouncer = announcer_module.GameAnnouncer
TMP_TTS_PATH = announcer_module.TMP_TTS_PATH


class FakeResult:
    def expect(self, _message):
        return self


class GameAnnouncerAudioTests(unittest.TestCase):
    def build_fw(self):
        fw = MagicMock()
        fw.send_file.return_value = FakeResult()
        fw.play_audio_file.return_value = FakeResult()
        fw.stop_audio.return_value = None
        return fw

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=False)
    @patch.object(announcer_module, "ElevenLabs")
    def test_build_playback_samples_uses_golden_padding_and_fades(self, mock_elevenlabs):
        mock_elevenlabs.return_value = MagicMock()
        announcer = GameAnnouncer(self.build_fw())

        pcm_samples = [20000] * 160
        samples = announcer._build_playback_samples(struct.pack("160h", *pcm_samples))

        self.assertEqual(announcer.sample_rate, 8000)
        self.assertEqual(announcer.gain, 1.8)
        self.assertEqual(len(samples), 1200 + 80 + 1200)
        self.assertTrue(all(sample == 0 for sample in samples[:1200]))
        self.assertEqual(samples[1200], 0)
        self.assertEqual(samples[-1201], 0)
        self.assertLessEqual(max(abs(sample) for sample in samples), 32767)

    @patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=False)
    @patch.object(announcer_module, "ElevenLabs")
    def test_speak_rotates_filenames_and_writes_8khz_wav(self, mock_elevenlabs):
        fake_client = MagicMock()
        fake_client.text_to_speech.convert.return_value = [struct.pack("400h", *([1000] * 400))]
        mock_elevenlabs.return_value = fake_client
        fw = self.build_fw()
        announcer = GameAnnouncer(fw)

        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_tts_path = Path(temp_dir) / "tmp_tts_latest.wav"
            with patch.object(announcer_module, "TMP_TTS_PATH", tmp_tts_path), patch.object(audio_module.time, "sleep") as sleep_mock:
                announcer.speak("first line")
                announcer.speak("second line")

            self.assertEqual(
                [call.args[1] for call in fw.send_file.call_args_list],
                ["/sounds/tts_b.wav", "/sounds/tts_a.wav"],
            )
            self.assertEqual(
                [call.args[0] for call in fw.play_audio_file.call_args_list],
                ["tts_b.wav", "tts_a.wav"],
            )

            with wave.open(str(tmp_tts_path), "rb") as wav_file:
                self.assertEqual(wav_file.getframerate(), 8000)
                self.assertEqual(wav_file.getnchannels(), 1)

            sleep_values = [call.args[0] for call in sleep_mock.call_args_list]
            self.assertEqual(sleep_values.count(1.2), 2)
            self.assertTrue(any(value > 0.5 for value in sleep_values))


if __name__ == "__main__":
    unittest.main()
