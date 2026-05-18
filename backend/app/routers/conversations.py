import json
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sql_delete
from app.database import get_db, AsyncSessionLocal
from app.models.user import User, SubscriptionTier
from app.models.conversation import Conversation
from app.models.memory import MemoryExtract
from app.models.subscription import VoiceCredit
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


async def _check_conversation_limit(user: User, db: AsyncSession) -> bool:
    """Returns True if user can start a new conversation, raises 403 if not."""
    if user.subscription_tier in (SubscriptionTier.premium, SubscriptionTier.credits):
        return True

    # Free tier: check daily text conversation limit
    result = await db.execute(select(VoiceCredit).where(VoiceCredit.user_id == user.user_id))
    vc = result.scalar_one_or_none()
    if not vc:
        return True

    today = datetime.utcnow().date()
    if vc.last_reset_date and vc.last_reset_date.date() < today:
        vc.text_conversations_remaining = 3
        vc.last_reset_date = datetime.utcnow()

    if vc.text_conversations_remaining <= 0:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "daily_limit_reached",
                "message": "You've used your 3 free conversations for today. Upgrade to keep chatting with Amy!",
            },
        )
    vc.text_conversations_remaining -= 1
    return True


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.user_id)
        .order_by(Conversation.date_started.desc())
        .offset(skip)
        .limit(limit)
    )
    convos = result.scalars().all()
    return [
        ConversationSummary(
            conversation_id=c.conversation_id,
            title=c.title,
            date_started=c.date_started,
            date_ended=c.date_ended,
            message_count=len(c.messages),
            topics_discussed=c.topics_discussed,
            user_mood_before=c.user_mood_before,
            user_mood_after=c.user_mood_after,
        )
        for c in convos
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == current_user.user_id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_conversation_limit(current_user, db)
    convo = Conversation(
        user_id=current_user.user_id,
        title=data.title,
        messages=[],
        user_mood_before=data.user_mood_before,
    )
    db.add(convo)
    await db.flush()
    return convo


@router.patch("/{conversation_id}/mood", response_model=ConversationResponse)
async def update_mood(
    conversation_id: UUID,
    data: MoodUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == current_user.user_id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo.user_mood_after = data.mood_after
    return convo


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == current_user.user_id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(convo)


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

    async with AsyncSessionLocal() as db:
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.send_json({"type": "error", "message": "Unauthorized"})
            await websocket.close(code=4001)
            return

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)

                if msg.get("type") != "message":
                    continue

                user_message = msg.get("content", "").strip()
                conversation_id = msg.get("conversation_id")

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

                # Load or create conversation
                convo = None
                if conversation_id:
                    result = await db.execute(
                        select(Conversation).where(
                            Conversation.conversation_id == UUID(conversation_id),
                            Conversation.user_id == user.user_id,
                        )
                    )
                    convo = result.scalar_one_or_none()

                if not convo:
                    await _check_conversation_limit(user, db)
                    convo = Conversation(user_id=user.user_id, messages=[])
                    db.add(convo)
                    await db.flush()

                # Build memory context
                memory_context = await build_memory_context(user.user_id, db)

                # Stream Claude's response
                full_response = ""
                async for token_chunk in claude_service.stream_response(
                    user_message=user_message,
                    conversation_history=convo.messages,
                    memory_context=memory_context,
                ):
                    full_response += token_chunk
                    await websocket.send_json({"type": "token", "content": token_chunk})

                # Persist messages
                new_messages = list(convo.messages)
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
                convo.messages = new_messages

                # Auto-generate title after first exchange
                if len(new_messages) == 2 and not convo.title:
                    convo.title = await claude_service.generate_conversation_title(new_messages)

                await db.flush()

                # Send done event
                await websocket.send_json({
                    "type": "done",
                    "conversation_id": str(convo.conversation_id),
                    "full_response": full_response,
                })

                # Respect explicit forget requests — skip extraction and purge
                # any memories already saved from this conversation.
                if _has_forget_intent(user_message):
                    await db.execute(
                        sql_delete(MemoryExtract).where(
                            MemoryExtract.user_id == user.user_id,
                            MemoryExtract.source_conversation_id == convo.conversation_id,
                        )
                    )
                    await cache_delete(f"memory_context:{user.user_id}")
                else:
                    memories = await claude_service.extract_memories(new_messages[-8:])
                    if memories:
                        await save_extracted_memories(user.user_id, convo.conversation_id, memories, db)

                await db.commit()

        except WebSocketDisconnect:
            # End conversation on disconnect
            async with AsyncSessionLocal() as end_db:
                if convo:
                    end_result = await end_db.execute(
                        select(Conversation).where(Conversation.conversation_id == convo.conversation_id)
                    )
                    end_convo = end_result.scalar_one_or_none()
                    if end_convo and not end_convo.date_ended:
                        end_convo.date_ended = datetime.utcnow()
                        await end_db.commit()
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
