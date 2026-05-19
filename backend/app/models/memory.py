import enum


class EventType(str, enum.Enum):
    breakup = "breakup"
    rejection = "rejection"
    trauma = "trauma"
    milestone = "milestone"
    achievement = "achievement"


class PatternName(str, enum.Enum):
    overthinks = "overthinks"
    avoids_conflict = "avoids_conflict"
    anxious_attachment = "anxious_attachment"
    people_pleasing = "people_pleasing"
    self_sabotage = "self_sabotage"
    other = "other"


class GoalCategory(str, enum.Enum):
    confidence = "confidence"
    boundaries = "boundaries"
    vulnerability = "vulnerability"
    communication = "communication"
    other = "other"


class MemoryType(str, enum.Enum):
    trauma = "trauma"
    pattern = "pattern"
    goal = "goal"
    sensitivity = "sensitivity"
    win = "win"
    insight = "insight"
