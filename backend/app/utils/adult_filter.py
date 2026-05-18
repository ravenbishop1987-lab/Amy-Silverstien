import re

ADULT_LANGUAGE_PATTERNS = [
    r"\b(adult|18\+|nsfw|explicit|naughty|dirty|spicy|erotic|sexual|sensual|intimate)\b",
    r"\b(sex|sexy|sext|sexting|horny|aroused|turned on|turn me on|lust|desire|fantasy|fantasies)\b",
    r"\b(nudes?|naked|undress|strip|striptease|lingerie|thong|panties|bra)\b",
    r"\b(onlyfans|fanvue|porn|porno|xxx|camgirl|cam boy|webcam|escort|hookup|hook up)\b",
    r"\b(fuck|fucking|fuck me|suck|lick|ride|grind|moan|dirty talk|send pics|send nudes)\b",
    r"\b(blowjob|handjob|anal|oral|orgasm|climax|cum|cumming|ejaculate|dick|cock|penis|pussy|vagina|clit|boobs?|breasts?|tits?|ass|butt)\b",
    r"\b(master|mistress|slave|submissive|sub|dom|dominant|domme|bdsm|kink|kinky|fetish|spank|choke|collar|leash|roleplay|role play)\b",
    r"\b(sugar daddy|sugar baby|feet pics|foot fetish|lap dance|thirst trap)\b",
]


def is_adult_language(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9+]+", " ", text.lower()).strip()
    compact = re.sub(r"\s+", "", normalized)
    return (
        any(re.search(pattern, normalized, re.IGNORECASE) for pattern in ADULT_LANGUAGE_PATTERNS)
        or re.search(r"\b(master\s*bait(?:e|ing)?|mastur\s*bat(?:e|ing|ion)?|jerk\s*off|jacking\s*off)\b", normalized, re.IGNORECASE) is not None
        or re.search(r"(masterbait|masterbating|masturbat|jerkoff|jackingoff)", compact, re.IGNORECASE) is not None
    )
