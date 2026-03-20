"""
Platform-switch detection layer.

Scans an incoming message for signals that the offender is attempting
to move the conversation off the current (monitored) platform. Returns
a structured result so the caller can act on it without re-parsing.
"""
import re

# ── Keyword patterns that indicate a platform-switch attempt ─────────────────
_PLATFORM_PATTERNS: dict[str, list[str]] = {
    "Discord": [
        r"\bdiscord\b",
        r"\bdiscord\.gg\b",
        r"discord tag",
        r"disc\b",
    ],
    "WhatsApp": [
        r"\bwhatsapp\b",
        r"\bwhats ?app\b",
        r"\bwa\.me\b",
    ],
    "Snapchat": [
        r"\bsnapchat\b",
        r"\bsnap\b",
        r"\bmy snap\b",
    ],
    "Instagram": [
        r"\binstagram\b",
        r"\binsta\b",
        r"\bdm me\b",
        r"\bmy ig\b",
    ],
    "Signal": [
        r"\bsignal\b",
    ],
    "Kik": [
        r"\bkik\b",
    ],
    "Phone/SMS": [
        r"\bphone number\b",
        r"\bcall me\b",
        r"\btext me\b",
        r"\bmy number\b",
        r"\bsms\b",
        r"\b\+?[\d][\d\s\-\(\)]{7,}\b",   # crude phone-number pattern
    ],
}

# Compile once at import time
_COMPILED: dict[str, list[re.Pattern]] = {
    platform: [re.compile(pat, re.IGNORECASE) for pat in patterns]
    for platform, patterns in _PLATFORM_PATTERNS.items()
}


class SwitchDetection:
    """Result object returned by `detect_platform_switch`."""

    def __init__(self, detected: bool, platform: str | None = None):
        self.detected = detected
        self.platform = platform  # e.g. "Discord", "WhatsApp", …

    def __bool__(self) -> bool:
        return self.detected


def detect_platform_switch(text: str) -> SwitchDetection:
    """
    Check whether *text* contains a platform-switch attempt.

    Returns a `SwitchDetection` with `detected=True` and the matched
    platform name if found, otherwise `detected=False`.
    """
    for platform, patterns in _COMPILED.items():
        for pattern in patterns:
            if pattern.search(text):
                return SwitchDetection(detected=True, platform=platform)
    return SwitchDetection(detected=False)
