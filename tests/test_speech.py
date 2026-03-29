import importlib
import os
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch


speech_module = importlib.import_module("src.game.speech")
SpeechTranscriber = speech_module.SpeechTranscriber


class SpeechTranscriberTests(unittest.TestCase):
    def build_client(self, responses):
        client = MagicMock()
        client.files.upload.return_value = types.SimpleNamespace(
            name="files/test-audio",
            uri="gs://test-audio",
            mime_type="audio/wav",
        )
        client.files.delete.return_value = None
        client.models.generate_content.side_effect = responses
        return client

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False)
    @patch.object(speech_module.genai, "Client")
    def test_transcriber_configures_client_timeout(self, mock_client_cls):
        mock_client_cls.return_value = self.build_client([types.SimpleNamespace(text="ignored")])

        SpeechTranscriber()

        _, kwargs = mock_client_cls.call_args
        self.assertEqual(kwargs["api_key"], "test-key")
        self.assertEqual(kwargs["http_options"].timeout, speech_module.DEFAULT_HTTP_TIMEOUT_MS)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False)
    @patch.object(speech_module.genai, "Client")
    def test_transcribe_sends_uploaded_audio_as_file_part(self, mock_client_cls):
        client = self.build_client([types.SimpleNamespace(text="hello from audio")])
        mock_client_cls.return_value = client
        transcriber = SpeechTranscriber()

        with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
            transcript = transcriber.transcribe(wav_file.name)

        self.assertEqual(transcript, "hello from audio")
        _, kwargs = client.models.generate_content.call_args
        self.assertEqual(kwargs["model"], speech_module.MODELS_FALLBACK[0])
        self.assertEqual(kwargs["config"].system_instruction, speech_module.TRANSCRIPTION_SYSTEM_INSTRUCTION)
        self.assertEqual(kwargs["config"].response_mime_type, "text/plain")
        self.assertEqual(len(kwargs["contents"]), 1)
        self.assertEqual(kwargs["contents"][0].file_data.file_uri, "gs://test-audio")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False)
    @patch.object(speech_module.genai, "Client")
    def test_transcribe_falls_back_after_prompt_echo(self, mock_client_cls):
        client = self.build_client(
            [
                types.SimpleNamespace(
                    text="Speaker 1: Please provide a complete and accurate transcription of the audio."
                ),
                types.SimpleNamespace(text="actual player intro"),
            ]
        )
        mock_client_cls.return_value = client
        transcriber = SpeechTranscriber()

        with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
            transcript = transcriber.transcribe(wav_file.name)

        self.assertEqual(transcript, "actual player intro")
        self.assertEqual(client.models.generate_content.call_count, 2)
        first_call = client.models.generate_content.call_args_list[0].kwargs
        second_call = client.models.generate_content.call_args_list[1].kwargs
        self.assertEqual(first_call["model"], speech_module.MODELS_FALLBACK[0])
        self.assertEqual(second_call["model"], speech_module.MODELS_FALLBACK[1])

    def test_is_recoverable_error_treats_timeouts_as_retryable(self):
        self.assertTrue(SpeechTranscriber._is_recoverable_error("Request timed out"))
        self.assertTrue(SpeechTranscriber._is_recoverable_error("Gateway timeout"))


if __name__ == "__main__":
    unittest.main()
