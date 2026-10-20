"""
Sovereign AI Workbench — Voice Transcription Service

Provides on-premise, air-gapped speech-to-text using Faster-Whisper Large-v3-Turbo.
Utilizes CUDA acceleration with automatic CPU int8 fallback for 100% reliability.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)


def _register_nvidia_dll_paths() -> None:
    """Register nvidia CUDA DLL directories on Windows if installed."""
    if sys.platform != "win32":
        return

    # Check site-packages for nvidia libraries
    site_packages_dirs = [p for p in sys.path if "site-packages" in p]
    prefix_site = Path(sys.prefix) / "Lib" / "site-packages"
    if prefix_site.exists() and str(prefix_site) not in site_packages_dirs:
        site_packages_dirs.append(str(prefix_site))

    for sp in site_packages_dirs:
        nvidia_root = Path(sp) / "nvidia"
        if nvidia_root.exists():
            for sub in ["cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"]:
                bin_dir = nvidia_root / sub / "bin"
                if bin_dir.exists():
                    try:
                        os.add_dll_directory(str(bin_dir))
                        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                        logger.debug("added_nvidia_dll_directory", path=str(bin_dir))
                    except Exception:
                        pass


# Register DLL paths early
_register_nvidia_dll_paths()


class TranscriptionService:
    """Singleton service for speech-to-text using Faster-Whisper Large-v3-Turbo."""

    def __init__(self) -> None:
        self._model: Any = None
        self._device: str = "cpu"
        self._compute_type: str = "int8"
        self._model_path: str = ""

    def _resolve_model_path(self) -> str:
        """Resolve local cached model snapshot or default identifier."""
        hf_cache = Path(
            os.path.expanduser(
                "~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots"
            )
        )
        if hf_cache.exists():
            snapshots = [p for p in hf_cache.iterdir() if p.is_dir()]
            if snapshots:
                selected = sorted(snapshots, key=lambda p: p.stat().st_mtime, reverse=True)[0]
                logger.info("whisper_local_snapshot_found", path=str(selected))
                return str(selected)

        hf_cache_general = Path(
            os.path.expanduser(
                "~/.cache/huggingface/hub/models--deepdml--faster-whisper-large-v3-turbo/snapshots"
            )
        )
        if hf_cache_general.exists():
            snapshots = [p for p in hf_cache_general.iterdir() if p.is_dir()]
            if snapshots:
                selected = sorted(snapshots, key=lambda p: p.stat().st_mtime, reverse=True)[0]
                return str(selected)

        return "mobiuslabsgmbh/faster-whisper-large-v3-turbo"

    def _load_cpu_model(self, model_path: str) -> Any:
        """Initialize model on CPU using int8 quantization."""
        from faster_whisper import WhisperModel

        logger.info("loading_whisper_cpu_int8", model_path=model_path)
        self._model = WhisperModel(model_path, device="cpu", compute_type="int8")
        self._device = "cpu"
        self._compute_type = "int8"
        logger.info("whisper_cpu_ready", device=self._device, compute_type=self._compute_type)
        return self._model

    def get_model(self) -> Any:
        """Lazily load the WhisperModel instance with CUDA or CPU fallback."""
        if self._model is not None:
            return self._model

        _register_nvidia_dll_paths()
        from faster_whisper import WhisperModel

        model_path = self._resolve_model_path()
        self._model_path = model_path

        # Try CUDA float16 if possible
        try:
            logger.info("loading_whisper_cuda", model_path=model_path)
            self._model = WhisperModel(model_path, device="cuda", compute_type="float16")
            self._device = "cuda"
            self._compute_type = "float16"
            logger.info("whisper_cuda_ready", device=self._device, compute_type=self._compute_type)
            return self._model
        except Exception as cuda_err:
            logger.warning("whisper_cuda_init_failed_falling_back_to_cpu", error=str(cuda_err))

        return self._load_cpu_model(model_path)

    def transcribe(
        self,
        audio_file_path: str | Path,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> dict[str, Any]:
        """Transcribe an audio file (.mp3, .wav, .m4a, .mp4, .webm, .ogg) into text."""
        model = self.get_model()
        audio_path_str = str(audio_file_path)

        logger.info("transcribing_audio", file=audio_path_str, device=self._device, language=language)

        try:
            segments, info = model.transcribe(
                audio_path_str,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            segment_texts = [segment.text.strip() for segment in segments]
            detected_lang = info.language
            detected_prob = round(info.language_probability, 3)
            duration = round(info.duration, 2)
        except Exception as exec_err:
            # If CUDA runtime error occurs (e.g. cublas DLL missing or OOM), fallback to CPU immediately
            if self._device == "cuda":
                logger.warning("cuda_transcribe_runtime_error_switching_to_cpu", error=str(exec_err))
                model = self._load_cpu_model(self._model_path or self._resolve_model_path())
                segments, info = model.transcribe(
                    audio_path_str,
                    language=language,
                    beam_size=beam_size,
                    vad_filter=vad_filter,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                segment_texts = [segment.text.strip() for segment in segments]
                detected_lang = info.language
                detected_prob = round(info.language_probability, 3)
                duration = round(info.duration, 2)
            else:
                logger.error("transcription_fatal_error", error=str(exec_err))
                raise exec_err

        full_text = " ".join(segment_texts).strip()

        logger.info(
            "transcription_completed",
            language=detected_lang,
            duration=duration,
            text_length=len(full_text),
            device=self._device,
        )

        return {
            "text": full_text,
            "language": detected_lang,
            "language_probability": detected_prob,
            "duration": duration,
            "device": self._device.upper(),
            "model": "Faster-Whisper Large-v3-Turbo",
        }


# Global singleton instance
transcription_service = TranscriptionService()
