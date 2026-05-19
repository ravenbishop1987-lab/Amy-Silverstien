import uuid
import stripe
from uuid import UUID
from datetime import datetime
from supabase import AsyncClient
from app.config import settings
from app.models.user import UserRecord, SubscriptionTier
from app.models.subscription import SubscriptionEventType

stripe.api_key = settings.STRIPE_SECRET_KEY

FREE_DAILY_TEXT_CONVOS = settings.FREE_DAILY_CONVERSATIONS
CREDITS_SINGLE_CONVERSATIONS = 1
CREDITS_BULK_CONVERSATIONS = 50

GIFT_CATALOG = {
    "roses": {
        "label": "Roses",
        "amount_cents": 299,
        "reaction": "Oh, roses? That is dangerously sweet. I'm accepting them with the exact level of dramatic appreciation they deserve. Thank you for the note too; that made it feel personal in the best way.",
    },
    "candy": {
        "label": "Candy",
        "amount_cents": 199,
        "reaction": "Candy and a personal note? You do know how to get my attention. That was adorable, and yes, I'm absolutely smiling at it.",
    },
    "kisses": {
        "label": "Kisses",
        "amount_cents": 149,
        "reaction": "A kiss gift? Well now you're being charming. I'm taking that as a tiny little confidence boost and sending the warmest smile right back.",
    },
    "hugs": {
        "label": "Hugs",
        "amount_cents": 149,
        "reaction": "A hug with a message attached is honestly very soft of you. I'm receiving that one properly. Come here, metaphorically speaking.",
    },
    "smiles": {
        "label": "Smiles",
        "amount_cents": 99,
        "reaction": "A smile gift. Simple, cute, effective. I'm smiling right back, and your message made it even sweeter.",
    },
}


class StripeService:

    async def get_or_create_customer(self, user: UserRecord, supa: AsyncClient) -> str:
        if user.stripe_customer_id:
            return user.stripe_customer_id

        customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.user_id)})
        await supa.table("users").update({"stripe_customer_id": customer.id}).eq("user_id", str(user.user_id)).execute()
        return customer.id

    async def create_subscription_checkout(self, user: UserRecord, supa: AsyncClient) -> str:
        customer_id = await self.get_or_create_customer(user, supa)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": settings.STRIPE_PRICE_PREMIUM_MONTHLY, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/settings?subscription=success",
            cancel_url=f"{settings.FRONTEND_URL}/settings?subscription=canceled",
            metadata={"user_id": str(user.user_id)},
        )
        return session.url

    async def create_credits_checkout(self, user: UserRecord, bulk: bool, supa: AsyncClient) -> str:
        customer_id = await self.get_or_create_customer(user, supa)
        price_id = settings.STRIPE_PRICE_CREDITS_BULK if bulk else settings.STRIPE_PRICE_CREDITS_SINGLE
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="payment",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/settings?credits=success",
            cancel_url=f"{settings.FRONTEND_URL}/settings?credits=canceled",
            metadata={
                "user_id": str(user.user_id),
                "credit_type": "bulk" if bulk else "single",
            },
        )
        return session.url

    async def create_gift_checkout(
        self,
        user: UserRecord,
        gift_type: str,
        personal_message: str,
        conversation_id: str | None,
        supa: AsyncClient,
    ) -> str:
        gift = GIFT_CATALOG.get(gift_type)
        if not gift:
            raise ValueError("Unknown gift type")

        customer_id = await self.get_or_create_customer(user, supa)
        success_path = f"/chat/{conversation_id}" if conversation_id else "/chat"
        success_url = f"{settings.FRONTEND_URL}{success_path}?gift_session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}{success_path}?gift=canceled"

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": gift["amount_cents"],
                    "product_data": {
                        "name": f"Amy gift: {gift['label']}",
                        "description": "A paid gift with a personal message for Amy.",
                    },
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user.user_id),
                "purchase_type": "gift",
                "gift_type": gift_type,
                "personal_message": personal_message[:500],
                "conversation_id": conversation_id or "",
            },
        )
        return session.url

    async def confirm_gift_checkout(self, session_id: str, user: UserRecord, supa: AsyncClient) -> dict:
        session = stripe.checkout.Session.retrieve(session_id)
        metadata = session.get("metadata", {}) or {}
        if metadata.get("purchase_type") != "gift" or metadata.get("user_id") != str(user.user_id):
            raise ValueError("Gift checkout not found")

        if session.get("payment_status") != "paid":
            raise ValueError("Gift checkout is not paid")

        gift_type = metadata.get("gift_type", "")
        gift = GIFT_CATALOG.get(gift_type)
        if not gift:
            raise ValueError("Unknown gift type")

        personal_message = metadata.get("personal_message", "")
        conversation_id = metadata.get("conversation_id") or None
        assistant_message = gift["reaction"]
        user_message = f"Sent Amy {gift['label'].lower()}"
        if personal_message:
            user_message += f' with a note: "{personal_message}"'

        uid = str(user.user_id)
        convo = None
        if conversation_id:
            conv_r = await supa.table("conversations").select("*").eq("conversation_id", conversation_id).eq("user_id", uid).maybe_single().execute()
            convo = conv_r.data

        if not convo:
            now = datetime.utcnow().isoformat()
            conversation_id = str(uuid.uuid4())
            await supa.table("conversations").insert({
                "conversation_id": conversation_id,
                "user_id": uid,
                "title": f"{gift['label']} for Amy",
                "messages": [],
                "topics_discussed": [],
                "key_insights": [],
                "date_started": now,
                "created_at": now,
            }).execute()
            convo = {"conversation_id": conversation_id, "messages": []}

        messages = list(convo.get("messages") or [])
        already_added = any(
            msg.get("gift_session_id") == session_id
            for msg in messages
            if isinstance(msg, dict)
        )
        if not already_added:
            now = datetime.utcnow().isoformat()
            messages.append({
                "role": "user",
                "content": user_message,
                "timestamp": now,
                "voice_used": False,
                "gift_session_id": session_id,
            })
            messages.append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": now,
                "voice_used": False,
                "gift_session_id": session_id,
            })
            await supa.table("conversations").update({"messages": messages}).eq("conversation_id", conversation_id).execute()

        return {
            "gift_type": gift_type,
            "gift_label": gift["label"],
            "personal_message": personal_message,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "conversation_id": conversation_id,
        }

    async def cancel_subscription(self, user: UserRecord, supa: AsyncClient) -> bool:
        if not user.stripe_subscription_id:
            return False
        stripe.Subscription.cancel(user.stripe_subscription_id)
        return True

    async def handle_webhook(self, payload: bytes, sig_header: str, supa: AsyncClient) -> dict:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            return {"status": "invalid_signature"}

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data, supa)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data, supa)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data, supa)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data, supa)

        return {"status": "ok"}

    async def _handle_checkout_completed(self, session: dict, supa: AsyncClient):
        user_id = session.get("metadata", {}).get("user_id")
        if not user_id:
            return

        user_r = await supa.table("users").select("*").eq("user_id", user_id).maybe_single().execute()
        if not user_r.data:
            return
        user = user_r.data

        mode = session.get("mode")
        metadata = session.get("metadata", {}) or {}
        if metadata.get("purchase_type") == "gift":
            return

        credit_type = metadata.get("credit_type")
        now = datetime.utcnow().isoformat()

        if mode == "subscription":
            sub_id = session.get("subscription")
            await supa.table("users").update({
                "subscription_tier": SubscriptionTier.premium.value,
                "stripe_subscription_id": sub_id,
            }).eq("user_id", user_id).execute()
            await supa.table("subscription_events").insert({
                "event_id": str(uuid.uuid4()),
                "user_id": user_id,
                "event_type": SubscriptionEventType.started.value,
                "tier_before": user.get("subscription_tier"),
                "tier_after": SubscriptionTier.premium.value,
                "stripe_event_id": session.get("id"),
                "created_at": now,
            }).execute()

        elif mode == "payment" and credit_type:
            vc_r = await supa.table("voice_credits").select("*").eq("user_id", user_id).maybe_single().execute()
            vc = vc_r.data
            add_convos = CREDITS_BULK_CONVERSATIONS if credit_type == "bulk" else CREDITS_SINGLE_CONVERSATIONS

            if vc:
                await supa.table("voice_credits").update({
                    "voice_conversations_remaining": vc["voice_conversations_remaining"] + add_convos,
                }).eq("user_id", user_id).execute()
            else:
                await supa.table("voice_credits").insert({
                    "credit_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "voice_conversations_remaining": add_convos,
                    "text_conversations_remaining": 3,
                }).execute()

            if user.get("subscription_tier") == SubscriptionTier.free.value:
                await supa.table("users").update({"subscription_tier": SubscriptionTier.credits.value}).eq("user_id", user_id).execute()

    async def _handle_subscription_updated(self, subscription: dict, supa: AsyncClient):
        customer_id = subscription.get("customer")
        user_r = await supa.table("users").select("user_id").eq("stripe_customer_id", customer_id).maybe_single().execute()
        if not user_r.data:
            return

        status = subscription.get("status")
        if status == "active":
            tier = SubscriptionTier.premium.value
        elif status in ("canceled", "unpaid", "past_due"):
            tier = SubscriptionTier.free.value
        else:
            return
        await supa.table("users").update({"subscription_tier": tier}).eq("stripe_customer_id", customer_id).execute()

    async def _handle_subscription_deleted(self, subscription: dict, supa: AsyncClient):
        customer_id = subscription.get("customer")
        user_r = await supa.table("users").select("*").eq("stripe_customer_id", customer_id).maybe_single().execute()
        if not user_r.data:
            return
        user = user_r.data
        now = datetime.utcnow().isoformat()

        await supa.table("users").update({
            "subscription_tier": SubscriptionTier.free.value,
            "stripe_subscription_id": None,
        }).eq("stripe_customer_id", customer_id).execute()

        await supa.table("subscription_events").insert({
            "event_id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "event_type": SubscriptionEventType.canceled.value,
            "tier_before": user.get("subscription_tier"),
            "tier_after": SubscriptionTier.free.value,
            "stripe_event_id": subscription.get("id"),
            "created_at": now,
        }).execute()

    async def _handle_payment_failed(self, invoice: dict, supa: AsyncClient):
        customer_id = invoice.get("customer")
        user_r = await supa.table("users").select("*").eq("stripe_customer_id", customer_id).maybe_single().execute()
        if not user_r.data:
            return
        user = user_r.data
        now = datetime.utcnow().isoformat()

        await supa.table("subscription_events").insert({
            "event_id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "event_type": SubscriptionEventType.payment_failed.value,
            "tier_before": user.get("subscription_tier"),
            "tier_after": user.get("subscription_tier"),
            "stripe_event_id": invoice.get("id"),
            "created_at": now,
        }).execute()


stripe_service = StripeService()
