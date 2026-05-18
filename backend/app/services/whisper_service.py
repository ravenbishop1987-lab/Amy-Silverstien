import io
from openai import AsyncOpenAI
from app.config import settings


class WhisperService:
    """Transcribes voice input to text using OpenAI Whisper."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Convert audio bytes to text. Accepts webm, mp4, wav, mp3, m4a."""
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en",
            response_format="text",
        )
        return response.strip()


whisper_service = WhisperService()
