import io
import asyncio
import logging
from functools import lru_cache
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Resemblyzer is optional — graceful degradation if not installed
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    from pydub import AudioSegment
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False
    logger.warning("resemblyzer/pydub not installed — voice recognition unavailable")


@lru_cache(maxsize=1)
def _get_encoder():
    return VoiceEncoder()


def _extract_embedding_sync(audio_bytes: bytes) -> list[float]:
    """CPU-bound — run via run_in_executor."""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    # Resemblyzer needs 16 kHz mono PCM
    audio = audio.set_channels(1).set_frame_rate(16000)
    wav_buf = io.BytesIO()
    audio.export(wav_buf, format="wav")
    wav_buf.seek(0)
    wav = preprocess_wav(wav_buf)
    embedding = _get_encoder().embed_utterance(wav)
    return embedding.tolist()


async def extract_embedding(audio_bytes: bytes) -> list[float]:
    if not _AVAILABLE:
        raise RuntimeError("Voice recognition requires resemblyzer and pydub. Run: pip install resemblyzer pydub")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_embedding_sync, audio_bytes)


def cosine_similarity(e1: list[float], e2: list[float]) -> float:
    a, b = np.array(e1), np.array(e2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def is_same_speaker(e1: list[float], e2: list[float], threshold: float = 0.75) -> bool:
    return cosine_similarity(e1, e2) >= threshold


def is_available() -> bool:
    return _AVAILABLE
