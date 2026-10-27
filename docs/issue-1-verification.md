# Issue #1: verification when hardware and API access are available

Branch: fix/issue-1-mafia-dialogue-privacy
Issue: https://github.com/ldameron1/freewili-hackathon-project/issues/1

## Can run without Gemini, ElevenLabs, or hardware

From the repository root, run:
    python -m unittest discover -s tests -p test_issue_1.py -v

The isolated tests check multiple Mafia conversation turns, RED-to-exit behavior,
private night logging, and that the detective receives only public daytime
human transcripts. They use mocked hardware and service clients.

## FREE-WILi testing without ElevenLabs credits

With a device attached, play the bundled narrator file without calling TTS:
    python tests/test_cached_audio_playback.py --repeats 3

Check whether any replay slows down or loses pitch. The program prints the
WAV's declared sample rate and expected duration. The host's elapsed time
includes deliberate blocking waits: it is NOT the audible playback duration.
Measure the audible duration separately (for example, by recording the speaker).
If it glitches, also inspect the USB cable and display-processor connection.

The current default audio configuration is 8 kHz, mono, 16-bit PCM. Do not
change resampling or file header rates without confirming the device behavior.

## With API access restored

1. Run the game in debug mode (human Mafia + AI Mafia partner).
2. Speak twice at night, waiting for a partner reply after each statement.
   Press RED at the next prompt to finish the exchange.
3. Verify that both responses were captured, and that no fourth turn is
   requested after the limit of three.
4. Use a unique secret phrase at night. During the day, verify that the
   detective's submitted prompt does not contain it, even when it appears
   in the moderator-only log. Only daytime public human speech belongs in
   the shared prompt.
5. Generate several TTS lines with the live announcer and compare each
   playback's pitch and duration with the locally generated WAV. Distinguish
   slow sound from pauses caused by upload, API latency, and SDK calls.

Do not close issue #1 until the real device and live-provider cases pass.
