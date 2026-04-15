# model.py

import io
import logging
import numpy as np
import edge_tts
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from google import genai
from google.genai import types
from faster_whisper import WhisperModel

from utils import build_system_prompt, humanize_tts

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """
    Wraps Gemini (LLM), Faster-Whisper (STT), and Edge-TTS (TTS)
    into a single stateful session object.
    """

    # Whisper is expensive to load — share one instance across all sessions
    _whisper: WhisperModel | None = None

    def __init__(self, api_key: str, mode: dict, mode_name: str):
        # ── Gemini ────────────────────────────────────
        self.client = genai.Client(api_key=api_key)
        self.mode = mode
        self.mode_name = mode_name
        self.chat = self._create_chat()

        # ── Whisper (shared / lazy-loaded) ────────────
        if VoiceAssistant._whisper is None:
            logger.info("Loading Whisper model…")
            VoiceAssistant._whisper = WhisperModel(
                "tiny",
                compute_type="int8",
            )

        # ── TTS config ────────────────────────────────
        self.voice = "en-GB-RyanNeural"
        self.tts_rate = "+15%"

        # ── Local conversation log ─────────────────────
        self.local_history: list[dict] = []

    # ── Gemini chat factory ───────────────────────────
    def _create_chat(self):
        return self.client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(self.mode_name),
                temperature=self.mode["temperature"],
                top_p=self.mode["top_p"],
                top_k=self.mode["top_k"],
                max_output_tokens=self.mode["max_output_tokens"],
            ),
        )

    # ── Mode switch (recreates chat with new config) ──
    def update_mode(self, mode: dict, mode_name: str) -> None:
        if mode_name == self.mode_name:
            return  # nothing to do — avoid unnecessary chat resets
        self.mode = mode
        self.mode_name = mode_name
        self.chat = self._create_chat()
        logger.info("Mode switched to '%s'", mode_name)

    # ── LLM ───────────────────────────────────────────
    def ask_llm(self, text: str) -> str:
        """Send text to Gemini and return the assistant reply."""
        if not text or not text.strip():
            return "I didn't catch that. Could you please repeat?"

        try:
            response = self.chat.send_message(text)
            reply = response.text or ""
            self.local_history.append({"user": text, "assistant": reply})
            return reply

        except Exception as e:
            logger.error("Gemini error: %s", e)
            return "Sorry, I had trouble processing that. Please try again."

    # ── Reset ─────────────────────────────────────────
    def reset_history(self) -> None:
        """Start a fresh conversation (new Gemini chat)."""
        self.chat = self._create_chat()
        self.local_history.clear()

    # ── STT ───────────────────────────────────────────
    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Convert raw audio bytes (any format pydub supports) → text.
        Returns an empty string if transcription fails.
        """
        if not audio_bytes:
            return ""

        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        except CouldntDecodeError as e:
            logger.error("Audio decode failed: %s", e)
            raise ValueError("Unsupported or corrupt audio format.") from e

        # Normalise for Whisper: mono, 16 kHz
        audio = audio.set_channels(1).set_frame_rate(16000)
        samples = (
            np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0
        )

        segments, info = VoiceAssistant._whisper.transcribe(
            samples,
            beam_size=3,         
            temperature=0.0,
            vad_filter=True,     
            language="en",       
        )

        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.debug("Transcribed (%s, %.1fs): %s", info.language, info.duration, text)
        return text

    # ── TTS ───────────────────────────────────────────
    async def text_to_speech(self, text: str) -> bytes:
        """Convert AI reply text → WAV audio bytes."""
        clean = humanize_tts(text)
        if not clean:
            return b""

        communicate = edge_tts.Communicate(clean, self.voice, rate=self.tts_rate)

        mp3_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_chunks.append(chunk["data"])

        if not mp3_chunks:
            logger.warning("Edge-TTS returned no audio chunks.")
            return b""

        audio = AudioSegment.from_file(
            io.BytesIO(b"".join(mp3_chunks)), format="mp3"
        )

        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        return wav_io.getvalue()
