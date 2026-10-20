"""
Unit tests for Piper TTS service and endpoints.
"""

import pytest
from app.services.tts_service import tts_service, clean_text_for_tts


def test_clean_text_for_tts():
    raw = """
    # Industrial Report
    This is an **important** test of `Piper TTS` (en_US-lessac-medium).
    ```python
    print("Ignore this code block")
    ```
    - Check item 1
    - Check item 2
    """
    cleaned = clean_text_for_tts(raw)
    assert "Ignore this code block" not in cleaned
    assert "Code block omitted" in cleaned
    assert "important" in cleaned
    assert "Check item 1" in cleaned


def test_piper_tts_synthesis():
    wav_bytes = tts_service.synthesize_wav("Sovereign AI on-premise text to speech.")
    assert isinstance(wav_bytes, bytes)
    assert len(wav_bytes) > 1000
    # WAV header magic check (RIFF ... WAVE)
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]


def test_split_into_chunks():
    long_text = "Sentence one is here. Sentence two follows it nicely! Sentence three is also present? Finally sentence four."
    chunks = tts_service.split_into_chunks(long_text)
    assert len(chunks) >= 2
    assert "Sentence one is here" in chunks[0]
