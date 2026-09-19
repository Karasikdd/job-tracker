from enum import Enum


class Status(str, Enum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


class ReminderKind(str, Enum):
    interview = "interview"
    follow_up = "follow_up"
    custom = "custom"


class ReminderStatus(str, Enum):
    scheduled = "scheduled"
    fired = "fired"
    cancelled = "cancelled"


class EmailDeliveryStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"