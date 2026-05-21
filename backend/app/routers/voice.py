from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord, SubscriptionTier
from app.services.elevenlabs_service import elevenlabs_service
from app.services.whisper_service import whisper_service
from app.services import speaker_service
from app.utils.auth import get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_ENROLL_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_AUDIO_BYTES = 25 * 1024 * 1024   # 25 MB Whisper limit


def _require_voice_access(user: UserRecord):
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
    current_user: UserRecord = Depends(get_current_user),
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
    current_user: UserRecord = Depends(get_current_user),
):
    raise HTTPException(
        status_code=410,
        detail="Server-side voice transcription is disabled. The app uses browser speech recognition.",
    )


@router.post("/enroll")
async def enroll_voice(
    audio: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    """Save a voiceprint for the current user. Send 8-15 seconds of clear speech."""
    if not speaker_service.is_available():
        raise HTTPException(status_code=503, detail="Voice recognition not available.")

    content = await audio.read()
    if len(content) > MAX_ENROLL_BYTES:
        raise HTTPException(status_code=400, detail="Audio too large (max 10MB)")
    if len(content) < 8000:
        raise HTTPException(status_code=400, detail="Audio too short — record at least 8 seconds of speech")

    try:
        embedding = await speaker_service.extract_embedding(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process audio: {exc}")

    uid = str(current_user.user_id)
    enrolled_at = datetime.utcnow().isoformat()

    existing = await supa.table("user_profiles").select("profile_id").eq("user_id", uid).limit(1).execute()
    if existing and existing.data:
        await supa.table("user_profiles").update({
            "voice_embedding": embedding,
            "voice_enrolled_at": enrolled_at,
        }).eq("user_id", uid).execute()
    else:
        import uuid as _uuid
        await supa.table("user_profiles").insert({
            "profile_id": str(_uuid.uuid4()),
            "user_id": uid,
            "voice_embedding": embedding,
            "voice_enrolled_at": enrolled_at,
        }).execute()

    return {"enrolled": True, "enrolled_at": enrolled_at}


@router.post("/verify")
async def verify_voice(
    audio: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    """Compare audio to the stored voiceprint."""
    if not speaker_service.is_available():
        raise HTTPException(status_code=503, detail="Voice recognition not available.")

    uid = str(current_user.user_id)
    profile_r = await supa.table("user_profiles").select("voice_embedding,voice_enrolled_at").eq("user_id", uid).limit(1).execute()
    profile = profile_r.data[0] if profile_r and profile_r.data else None

    if not profile or not profile.get("voice_embedding"):
        raise HTTPException(status_code=400, detail="No voice enrolled. Go to Settings → Voice Identity to enroll first.")

    content = await audio.read()
    if len(content) > MAX_ENROLL_BYTES:
        raise HTTPException(status_code=400, detail="Audio too large (max 10MB)")

    try:
        embedding = await speaker_service.extract_embedding(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process audio: {exc}")

    similarity = speaker_service.cosine_similarity(embedding, profile["voice_embedding"])
    verified = speaker_service.is_same_speaker(embedding, profile["voice_embedding"])

    return {
        "verified": verified,
        "similarity": round(similarity, 3),
        "enrolled_at": profile.get("voice_enrolled_at"),
    }


@router.delete("/enroll", status_code=204)
async def delete_voice_enrollment(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("user_profiles").select("profile_id").eq("user_id", uid).limit(1).execute()
    if existing and existing.data:
        await supa.table("user_profiles").update({
            "voice_embedding": None,
            "voice_enrolled_at": None,
        }).eq("user_id", uid).execute()
