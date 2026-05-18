import httpx
from app.config import settings

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsService:
    """
    Synthesizes Amy's voice responses using ElevenLabs.
    Set ELEVENLABS_VOICE_ID in .env to Amy's cloned/selected voice.
    """

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        self.headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}

    async def synthesize(self, text: str) -> bytes:
        """Convert text to Amy's voice audio. Returns raw MP3 bytes."""
        if not self.api_key or not self.voice_id:
            raise ValueError("ElevenLabs API key or Voice ID not configured")

        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{self.voice_id}"
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": True,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.content

    async def stream_synthesis(self, text: str):
        """Stream audio chunks as they're generated (lower latency)."""
        if not self.api_key or not self.voice_id:
            raise ValueError("ElevenLabs API key or Voice ID not configured")

        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{self.voice_id}/stream"
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url, json=payload, headers=self.headers) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    yield chunk


elevenlabs_service = ElevenLabsService()
