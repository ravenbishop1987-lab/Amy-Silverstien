import io
import asyncio
import logging
import numpy as np

logger = logging.getLogger(__name__)

try:
    import librosa
    import av as _av  # noqa: F401 — presence check only
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False
    logger.warning("librosa/av not installed — voice recognition unavailable. Run: pip install librosa av")


def _load_audio_sync(audio_bytes: bytes) -> np.ndarray:
    """Decode any audio format to 16 kHz mono float32 using PyAV (bundled FFmpeg)."""
    import av
    container = av.open(io.BytesIO(audio_bytes))
    stream = next(s for s in container.streams if s.type == "audio")

    samples = []
    resampler = av.audio.resampler.AudioResampler(format="fltp", layout="mono", rate=16000)
    for frame in container.decode(stream):
        for rf in resampler.resample(frame):
            samples.append(rf.to_ndarray()[0])

    container.close()
    if not samples:
        raise ValueError("No audio data decoded")
    return np.concatenate(samples).astype(np.float32)


def _extract_embedding_sync(audio_bytes: bytes) -> list[float]:
    """Extract a speaker embedding from raw audio bytes (CPU-bound)."""
    y = _load_audio_sync(audio_bytes)

    # 40 MFCCs + delta + delta-delta → 120 features, averaged over time
    mfcc = librosa.feature.mfcc(y=y, sr=16000, n_mfcc=40)
    delta = librosa.feature.delta(mfcc)
    delta2 = librosa.feature.delta(mfcc, order=2)
    features = np.concatenate([mfcc, delta, delta2], axis=0)  # (120, T)

    mean = features.mean(axis=1)
    std = features.std(axis=1) + 1e-8
    embedding = np.concatenate([mean, std])  # 240-dim

    # L2 normalise so cosine similarity == dot product
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding.tolist()


async def extract_embedding(audio_bytes: bytes) -> list[float]:
    if not _AVAILABLE:
        raise RuntimeError("Voice recognition requires librosa and av. Run: pip install librosa av")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_embedding_sync, audio_bytes)


def cosine_similarity(e1: list[float], e2: list[float]) -> float:
    a, b = np.array(e1), np.array(e2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def is_same_speaker(e1: list[float], e2: list[float], threshold: float = 0.75) -> bool:
    return cosine_similarity(e1, e2) >= threshold


def is_available() -> bool:
    return _AVAILABLE
