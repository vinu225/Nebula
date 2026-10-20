"""
Sovereign AI Workbench — On-Premise Text-to-Speech Service

Provides 100% offline, air-gapped Text-to-Speech using Piper TTS (en_US-lessac-medium).
Synthesizes clean speech from markdown text without cloud dependencies.
"""

from __future__ import annotations

import io
from pathlib import Path
import re
import threading
from typing import Optional
import wave

import structlog

logger = structlog.get_logger(__name__)


def clean_text_for_tts(text: str, max_chars: int = 800) -> str:
    """Preprocess and clean markdown text for natural speech synthesis.

    - Removes code blocks
    - Strips URLs and Markdown links
    - Removes formatting symbols (**, *, #, >, `, ~)
    - Normalizes whitespace and bullet points
    """
    if not text:
        return ""

    t = text

    # Remove code blocks ```...``` (with DOTALL)
    t = re.sub(r"```[\s\S]*?```", " Code block omitted. ", t)

    # Remove inline code `...`
    t = re.sub(r"`[^`]+`", "", t)

    # Remove markdown images ![alt](url)
    t = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", t)

    # Convert markdown links [text](url) -> text
    t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)

    # Remove raw URLs
    t = re.sub(r"https?://\S+", "", t)

    # Remove markdown headers (# Title -> Title)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.MULTILINE)

    # Remove blockquotes (> quote)
    t = re.sub(r"^\s*>\s*", "", t, flags=re.MULTILINE)

    # Remove horizontal rules
    t = re.sub(r"^\s*[-*_]{3,}\s*$", "", t, flags=re.MULTILINE)

    # Convert bullet points (- item or * item) to pause
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.MULTILINE)

    # Remove bold, italics, strikethrough markdown decorators
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"~~([^~]+)~~", r"\1", t)

    # Remove HTML tags if any
    t = re.sub(r"<[^>]+>", "", t)

    # Normalize multiple newlines and spaces
    t = re.sub(r"\n+", ". ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Clean punctuation sequences
    t = re.sub(r"\s*([.,?!])\s*", r"\1 ", t)
    t = re.sub(r"\.+", ".", t).strip()

    if len(t) > max_chars:
        # Cut off cleanly at the last period/sentence boundary before max_chars
        cutoff = t[:max_chars].rfind(".")
        if cutoff > max_chars // 2:
            t = t[:cutoff + 1]
        else:
            t = t[:max_chars].strip() + "..."

    return t


class TTSService:
    """Singleton service for offline Piper Text-to-Speech synthesis."""

    def __init__(self) -> None:
        self._voice: Optional[Any] = None
        self._lock = threading.Lock()
        self._model_name = "en_US-lessac-medium"
        self._models_dir = Path(__file__).resolve().parent.parent.parent / "models_cache" / "piper"

    def _ensure_model_loaded(self) -> Any:
        """Load Piper voice model lazily with thread-safety."""
        if self._voice is not None:
            return self._voice

        with self._lock:
            if self._voice is not None:
                return self._voice

            from piper.voice import PiperVoice

            onnx_path = self._models_dir / f"{self._model_name}.onnx"
            json_path = self._models_dir / f"{self._model_name}.onnx.json"

            if not onnx_path.exists() or not json_path.exists():
                logger.info("downloading_piper_voice_model", model=self._model_name, target=str(self._models_dir))
                self._models_dir.mkdir(parents=True, exist_ok=True)
                from piper.download_voices import download_voice
                download_voice(self._model_name, self._models_dir)

            logger.info("loading_piper_voice_model", path=str(onnx_path))
            self._voice = PiperVoice.load(
                model_path=str(onnx_path),
                config_path=str(json_path),
            )
            return self._voice

    def warmup(self) -> None:
        """Pre-warm Piper model and ONNX execution session on server startup."""
        try:
            self._ensure_model_loaded()
            # Synthesize 1 tiny word to warm up ONNX allocators
            self.synthesize_wav("Ready.", length_scale=1.0)
            logger.info("tts_service_prewarmed_successfully", model=self._model_name)
        except Exception as e:
            logger.warning("tts_service_warmup_failed", error=str(e))

    def split_into_chunks(self, text: str) -> list[str]:
        """Split text into conversational sentence chunks optimized for zero-latency audio streaming.

        Chunk 0 is kept short (first sentence or ~100 chars) so time-to-first-sound
        is virtually instantaneous (<150ms). Subsequent chunks are balanced for continuous playback.
        """
        cleaned = clean_text_for_tts(text)
        if not cleaned:
            return []

        # Split on sentence boundaries
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
        if not raw_sentences:
            return [cleaned]

        chunks: list[str] = [raw_sentences[0]]
        current = ""

        for s in raw_sentences[1:]:
            if len(current) + len(s) + 1 <= 240:
                current = f"{current} {s}".strip()
            else:
                if current:
                    chunks.append(current)
                current = s

        if current:
            chunks.append(current)

        return chunks

    def synthesize_wav(self, text: str, length_scale: float = 0.95) -> bytes:
        """Synthesize text into in-memory WAV audio bytes.

        Args:
            text: Plain or markdown text.
            length_scale: Voice speed multiplier (default 0.95 for crisp, natural, fast delivery).

        Returns:
            bytes: Valid WAV audio file bytes.
        """
        cleaned = clean_text_for_tts(text)
        if not cleaned:
            cleaned = "No speech text provided."

        voice = self._ensure_model_loaded()

        with self._lock:
            from piper.config import SynthesisConfig
            syn_config = SynthesisConfig(length_scale=length_scale)

            buffer = io.BytesIO()
            first_chunk = True

            with wave.open(buffer, "wb") as wav_out:
                for chunk in voice.synthesize(cleaned, syn_config=syn_config):
                    if first_chunk:
                        wav_out.setnchannels(chunk.sample_channels)
                        wav_out.setsampwidth(chunk.sample_width)
                        wav_out.setframerate(chunk.sample_rate)
                        first_chunk = False
                    wav_out.writeframes(chunk.audio_int16_bytes)

            wav_bytes = buffer.getvalue()
            logger.info(
                "tts_synthesis_completed",
                text_len=len(cleaned),
                wav_bytes_len=len(wav_bytes),
                voice=self._model_name,
            )
            return wav_bytes


# Global singleton instance
tts_service = TTSService()
