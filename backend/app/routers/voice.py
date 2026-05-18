from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from app.models.user import User, SubscriptionTier
from app.services.elevenlabs_service import elevenlabs_service
from app.services.whisper_service import whisper_service
from app.utils.auth import get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25MB Whisper limit


def _require_voice_access(user: User):
    if user.subscription_tier == SubscriptionTier.free:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "voice_not_available",
                "message": "Voice is available on credits or premium plans. Upgrade to hear Amy!",
            },
        )


class SynthesizeRequest(BaseModel):
    text: str
    stream: bool = True


@router.post("/synthesize")
async def synthesize_voice(
    data: SynthesizeRequest,
    current_user: User = Depends(get_current_user),
):
    _require_voice_access(current_user)

    if len(data.text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")

    if data.stream:
        async def audio_generator():
            async for chunk in elevenlabs_service.stream_synthesis(data.text):
                yield chunk

        return StreamingResponse(audio_generator(), media_type="audio/mpeg")

    audio_bytes = await elevenlabs_service.synthesize(data.text)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=410,
        detail="Server-side voice transcription is disabled. The app uses browser speech recognition so adult redirects happen before any LLM transcription.",
    )
    content = await audio.read()
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")

    filename = audio.filename or "audio.webm"
    text = await whisper_service.transcribe(content, filename)
    return {"text": text, "filename": filename}
