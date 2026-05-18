from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserProfile, SubscriptionTier
from app.services.elevenlabs_service import elevenlabs_service
from app.services.whisper_service import whisper_service
from app.services import speaker_service
from app.utils.auth import get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_ENROLL_BYTES = 10 * 1024 * 1024  # 10 MB

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


@router.post("/enroll")
async def enroll_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a voiceprint for the current user. Send 8-15 seconds of clear speech."""
    if not speaker_service.is_available():
        raise HTTPException(status_code=503, detail="Voice recognition not available. Install resemblyzer and pydub.")

    content = await audio.read()
    if len(content) > MAX_ENROLL_BYTES:
        raise HTTPException(status_code=400, detail="Audio too large (max 10MB)")
    if len(content) < 8000:
        raise HTTPException(status_code=400, detail="Audio too short — record at least 8 seconds of speech")

    try:
        embedding = await speaker_service.extract_embedding(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process audio: {exc}")

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    profile = result.scalar_one_or_none()
    if profile:
        profile.voice_embedding = embedding
        profile.voice_enrolled_at = datetime.utcnow()
    else:
        profile = UserProfile(
            user_id=current_user.user_id,
            voice_embedding=embedding,
            voice_enrolled_at=datetime.utcnow(),
        )
        db.add(profile)

    await db.commit()
    return {"enrolled": True, "enrolled_at": profile.voice_enrolled_at}


@router.post("/verify")
async def verify_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare audio to the stored voiceprint. Returns similarity score and match result."""
    if not speaker_service.is_available():
        raise HTTPException(status_code=503, detail="Voice recognition not available. Install resemblyzer and pydub.")

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    profile = result.scalar_one_or_none()
    if not profile or not profile.voice_embedding:
        raise HTTPException(status_code=400, detail="No voice enrolled. Go to Settings → Voice Identity to enroll first.")

    content = await audio.read()
    if len(content) > MAX_ENROLL_BYTES:
        raise HTTPException(status_code=400, detail="Audio too large (max 10MB)")

    try:
        embedding = await speaker_service.extract_embedding(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process audio: {exc}")

    similarity = speaker_service.cosine_similarity(embedding, profile.voice_embedding)
    verified = speaker_service.is_same_speaker(embedding, profile.voice_embedding)

    return {
        "verified": verified,
        "similarity": round(similarity, 3),
        "enrolled_at": profile.voice_enrolled_at,
    }


@router.delete("/enroll", status_code=204)
async def delete_voice_enrollment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the stored voiceprint."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    profile = result.scalar_one_or_none()
    if profile:
        profile.voice_embedding = None
        profile.voice_enrolled_at = None
        await db.commit()
