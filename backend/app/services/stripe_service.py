import stripe
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.conversation import Conversation
from app.models.user import User, SubscriptionTier
from app.models.subscription import SubscriptionEvent, VoiceCredit, SubscriptionEventType

stripe.api_key = settings.STRIPE_SECRET_KEY

FREE_DAILY_TEXT_CONVOS = settings.FREE_DAILY_CONVERSATIONS
CREDITS_SINGLE_CONVERSATIONS = 1
CREDITS_BULK_CONVERSATIONS = 50

GIFT_CATALOG = {
    "roses": {
        "label": "Roses",
        "amount_cents": 299,
        "reaction": "Oh, roses? That is dangerously sweet. I’m accepting them with the exact level of dramatic appreciation they deserve. Thank you for the note too; that made it feel personal in the best way.",
    },
    "candy": {
        "label": "Candy",
        "amount_cents": 199,
        "reaction": "Candy and a personal note? You do know how to get my attention. That was adorable, and yes, I’m absolutely smiling at it.",
    },
    "kisses": {
        "label": "Kisses",
        "amount_cents": 149,
        "reaction": "A kiss gift? Well now you’re being charming. I’m taking that as a tiny little confidence boost and sending the warmest smile right back.",
    },
    "hugs": {
        "label": "Hugs",
        "amount_cents": 149,
        "reaction": "A hug with a message attached is honestly very soft of you. I’m receiving that one properly. Come here, metaphorically speaking.",
    },
    "smiles": {
        "label": "Smiles",
        "amount_cents": 99,
        "reaction": "A smile gift. Simple, cute, effective. I’m smiling right back, and your message made it even sweeter.",
    },
}


class StripeService:

    async def get_or_create_customer(self, user: User, db: AsyncSession) -> str:
        if user.stripe_customer_id:
            return user.stripe_customer_id

        customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.user_id)})
        user.stripe_customer_id = customer.id
        await db.flush()
        return customer.id

    async def create_subscription_checkout(self, user: User, db: AsyncSession) -> str:
        """Create a Stripe Checkout session for premium subscription."""
        customer_id = await self.get_or_create_customer(user, db)
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

    async def create_credits_checkout(self, user: User, bulk: bool, db: AsyncSession) -> str:
        """Create a Stripe Checkout session for voice credit purchase."""
        customer_id = await self.get_or_create_customer(user, db)
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
        user: User,
        gift_type: str,
        personal_message: str,
        conversation_id: str | None,
        db: AsyncSession,
    ) -> str:
        gift = GIFT_CATALOG.get(gift_type)
        if not gift:
            raise ValueError("Unknown gift type")

        customer_id = await self.get_or_create_customer(user, db)
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

    async def confirm_gift_checkout(self, session_id: str, user: User, db: AsyncSession) -> dict:
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
            convo = Conversation(user_id=user.user_id, title=f"{gift['label']} for Amy", messages=[])
            db.add(convo)
            await db.flush()
            conversation_id = str(convo.conversation_id)

        messages = list(convo.messages or [])
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
            convo.messages = messages
            await db.flush()

        return {
            "gift_type": gift_type,
            "gift_label": gift["label"],
            "personal_message": personal_message,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "conversation_id": conversation_id,
        }

    async def cancel_subscription(self, user: User, db: AsyncSession) -> bool:
        if not user.stripe_subscription_id:
            return False
        stripe.Subscription.cancel(user.stripe_subscription_id)
        return True

    async def handle_webhook(self, payload: bytes, sig_header: str, db: AsyncSession) -> dict:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            return {"status": "invalid_signature"}

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data, db)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data, db)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data, db)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data, db)

        return {"status": "ok"}

    async def _handle_checkout_completed(self, session: dict, db: AsyncSession):
        user_id = session.get("metadata", {}).get("user_id")
        if not user_id:
            return

        result = await db.execute(select(User).where(User.user_id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return

        mode = session.get("mode")
        metadata = session.get("metadata", {}) or {}
        if metadata.get("purchase_type") == "gift":
            return

        credit_type = metadata.get("credit_type")

        if mode == "subscription":
            sub_id = session.get("subscription")
            old_tier = user.subscription_tier
            user.subscription_tier = SubscriptionTier.premium
            user.stripe_subscription_id = sub_id
            db.add(SubscriptionEvent(
                user_id=user.user_id,
                event_type=SubscriptionEventType.started,
                tier_before=old_tier.value,
                tier_after=SubscriptionTier.premium.value,
                stripe_event_id=session.get("id"),
            ))

        elif mode == "payment" and credit_type:
            credits_result = await db.execute(select(VoiceCredit).where(VoiceCredit.user_id == user.user_id))
            vc = credits_result.scalar_one_or_none()
            if not vc:
                vc = VoiceCredit(user_id=user.user_id)
                db.add(vc)

            if user.subscription_tier == SubscriptionTier.free:
                user.subscription_tier = SubscriptionTier.credits

            add_convos = CREDITS_BULK_CONVERSATIONS if credit_type == "bulk" else CREDITS_SINGLE_CONVERSATIONS
            vc.voice_conversations_remaining += add_convos

        await db.flush()

    async def _handle_subscription_updated(self, subscription: dict, db: AsyncSession):
        customer_id = subscription.get("customer")
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        status = subscription.get("status")
        if status == "active":
            user.subscription_tier = SubscriptionTier.premium
        elif status in ("canceled", "unpaid", "past_due"):
            user.subscription_tier = SubscriptionTier.free
        await db.flush()

    async def _handle_subscription_deleted(self, subscription: dict, db: AsyncSession):
        customer_id = subscription.get("customer")
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        old_tier = user.subscription_tier
        user.subscription_tier = SubscriptionTier.free
        user.stripe_subscription_id = None
        db.add(SubscriptionEvent(
            user_id=user.user_id,
            event_type=SubscriptionEventType.canceled,
            tier_before=old_tier.value,
            tier_after=SubscriptionTier.free.value,
            stripe_event_id=subscription.get("id"),
        ))
        await db.flush()

    async def _handle_payment_failed(self, invoice: dict, db: AsyncSession):
        customer_id = invoice.get("customer")
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        db.add(SubscriptionEvent(
            user_id=user.user_id,
            event_type=SubscriptionEventType.payment_failed,
            tier_before=user.subscription_tier.value,
            tier_after=user.subscription_tier.value,
            stripe_event_id=invoice.get("id"),
        ))
        await db.flush()


stripe_service = StripeService()
