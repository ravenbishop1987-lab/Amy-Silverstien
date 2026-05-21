import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord, SubscriptionTier
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationSummary, MoodUpdate
from app.config import settings
from app.services.claude_service import claude_service
from app.services.memory_service import build_memory_context, save_extracted_memories
from app.utils.adult_filter import is_adult_language
from app.utils.auth import get_current_user, get_current_user_ws
from app.utils.rate_limiter import cache_delete

_FORGET_SIGNALS = (
    "don't remember",
    "dont remember",
    "forget this",
    "forget that",
    "don't save",
    "dont save",
    "don't store",
    "dont store",
    "keep this between us",
    "off the record",
    "don't bring this up",
    "dont bring this up",
    "please forget",
    "never mention",
    "stop remembering",
    "erase that",
    "delete that",
    "wipe that",
)


def _has_forget_intent(text: str) -> bool:
    lower = text.lower()
    return any(signal in lower for signal in _FORGET_SIGNALS)


router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _check_conversation_limit(user: UserRecord, supa: AsyncClient) -> bool:
    """Returns True if user can start a new conversation, raises 403 if not."""
    if user.subscription_tier in (SubscriptionTier.premium, SubscriptionTier.credits):
        return True

    uid = str(user.user_id)
    vc_r = await supa.table("voice_credits").select("*").eq("user_id", uid).limit(1).execute()
    vc = vc_r.data[0] if vc_r and vc_r.data else None
    if not vc:
        return True

    today = datetime.utcnow().date()
    last_reset = None
    if vc.get("last_reset_date"):
        from dateutil.parser import parse as parse_dt
        last_reset = parse_dt(vc["last_reset_date"]).date()

    if last_reset and last_reset < today:
        vc["text_conversations_remaining"] = 3
        await supa.table("voice_credits").update({
            "text_conversations_remaining": 3,
            "last_reset_date": datetime.utcnow().isoformat(),
        }).eq("user_id", uid).execute()

    if vc["text_conversations_remaining"] <= 0:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "daily_limit_reached",
                "message": "You've used your 3 free conversations for today. Upgrade to keep chatting with Amy!",
            },
        )

    await supa.table("voice_credits").update({
        "text_conversations_remaining": vc["text_conversations_remaining"] - 1,
    }).eq("user_id", uid).execute()
    return True


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    result = await supa.table("conversations").select("*").eq("user_id", str(current_user.user_id)).order("date_started", desc=True).range(skip, skip + limit - 1).execute()
    return [
        ConversationSummary(
            conversation_id=c["conversation_id"],
            title=c.get("title"),
            date_started=c["date_started"],
            date_ended=c.get("date_ended"),
            message_count=len(c.get("messages") or []),
            topics_discussed=c.get("topics_discussed") or [],
            user_mood_before=c.get("user_mood_before"),
            user_mood_after=c.get("user_mood_after"),
        )
        for c in (result.data or [])
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    result = await supa.table("conversations").select("*").eq("conversation_id", conversation_id).eq("user_id", str(current_user.user_id)).limit(1).execute()
    if not (result and result.data):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.data[0]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    await _check_conversation_limit(current_user, supa)
    now = datetime.utcnow().isoformat()
    convo_id = str(uuid.uuid4())
    row = {
        "conversation_id": convo_id,
        "user_id": str(current_user.user_id),
        "title": data.title,
        "messages": [],
        "topics_discussed": [],
        "key_insights": [],
        "user_mood_before": data.user_mood_before,
        "date_started": now,
        "created_at": now,
    }
    result = await supa.table("conversations").insert(row).execute()
    return result.data[0] if result.data else row


@router.patch("/{conversation_id}/mood", response_model=ConversationResponse)
async def update_mood(
    conversation_id: str,
    data: MoodUpdate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    existing = await supa.table("conversations").select("conversation_id").eq("conversation_id", conversation_id).eq("user_id", str(current_user.user_id)).limit(1).execute()
    if not (existing and existing.data):
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = await supa.table("conversations").update({"user_mood_after": data.mood_after}).eq("conversation_id", conversation_id).execute()
    return result.data[0] if result and result.data else existing.data[0]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    existing = await supa.table("conversations").select("conversation_id").eq("conversation_id", conversation_id).eq("user_id", str(current_user.user_id)).limit(1).execute()
    if not (existing and existing.data):
        raise HTTPException(status_code=404, detail="Conversation not found")
    await supa.table("conversations").delete().eq("conversation_id", conversation_id).execute()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time streaming chat.

    Client sends:  {"type": "message", "content": "...", "conversation_id": "..."}
    Server sends:  {"type": "token", "content": "..."} (streaming)
                   {"type": "done", "conversation_id": "...", "full_response": "..."}
                   {"type": "error", "message": "..."}
    """
    await websocket.accept()
    supa = await get_supabase()

    user = await get_current_user_ws(token, supa)
    if not user:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close(code=4001)
        return

    conversation_id: str | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") != "message":
                continue

            user_message = msg.get("content", "").strip()
            conversation_id_str = msg.get("conversation_id")

            if not user_message:
                continue

            if is_adult_language(user_message):
                await websocket.send_json({
                    "type": "redirect",
                    "url": settings.FANVUE_URL,
                    "message": "That conversation belongs on Fanvue.",
                })
                await websocket.close(code=1008)
                return

            uid = str(user.user_id)

            # Load existing conversation or create a new one
            convo_messages: list = []
            convo_title: str | None = None

            if conversation_id_str:
                conv_r = await supa.table("conversations").select("*").eq("conversation_id", conversation_id_str).eq("user_id", uid).limit(1).execute()
                if conv_r and conv_r.data:
                    conv_data = conv_r.data[0]
                    conversation_id = conversation_id_str
                    convo_messages = conv_data.get("messages") or []
                    convo_title = conv_data.get("title")

            if not conversation_id:
                await _check_conversation_limit(user, supa)
                now = datetime.utcnow().isoformat()
                conversation_id = str(uuid.uuid4())
                await supa.table("conversations").insert({
                    "conversation_id": conversation_id,
                    "user_id": uid,
                    "messages": [],
                    "topics_discussed": [],
                    "key_insights": [],
                    "date_started": now,
                    "created_at": now,
                }).execute()

            # Build memory context and stream response
            memory_context = await build_memory_context(user.user_id, supa)

            full_response = ""
            stream_error: Exception | None = None
            try:
                async for token_chunk in claude_service.stream_response(
                    user_message=user_message,
                    conversation_history=convo_messages,
                    memory_context=memory_context,
                ):
                    full_response += token_chunk
                    await websocket.send_json({"type": "token", "content": token_chunk})
            except Exception as e:
                stream_error = e

            if stream_error and not full_response:
                await websocket.send_json({"type": "error", "message": "Amy ran into a hiccup — please try again."})
                continue

            # Append messages
            new_messages = list(convo_messages)
            new_messages.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat(),
                "voice_used": msg.get("voice_used", False),
            })
            new_messages.append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.utcnow().isoformat(),
                "voice_used": False,
            })

            update_data: dict = {"messages": new_messages}

            # Auto-generate title after first exchange
            if len(convo_messages) == 0 and not convo_title:
                try:
                    update_data["title"] = await claude_service.generate_conversation_title(new_messages)
                except Exception:
                    pass

            await supa.table("conversations").update(update_data).eq("conversation_id", conversation_id).execute()

            await websocket.send_json({
                "type": "done",
                "conversation_id": conversation_id,
                "full_response": full_response,
            })

            # Memory handling
            if _has_forget_intent(user_message):
                await supa.table("memory_extracts").delete().eq("user_id", uid).eq("source_conversation_id", conversation_id).execute()
                await cache_delete(f"memory_context:{uid}")
            else:
                try:
                    memories = await claude_service.extract_memories(new_messages[-8:])
                    if memories:
                        await save_extracted_memories(user.user_id, conversation_id, memories, supa)
                except Exception:
                    pass

    except WebSocketDisconnect:
        if conversation_id:
            await supa.table("conversations").update({
                "date_ended": datetime.utcnow().isoformat(),
            }).eq("conversation_id", conversation_id).is_("date_ended", "null").execute()
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
