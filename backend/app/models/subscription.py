import enum


class SubscriptionEventType(str, enum.Enum):
    started = "subscription_started"
    upgraded = "upgraded"
    downgraded = "downgraded"
    canceled = "canceled"
    renewed = "renewed"
    payment_failed = "payment_failed"
