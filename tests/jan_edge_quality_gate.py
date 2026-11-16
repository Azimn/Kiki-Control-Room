"""Structural gate for public-safe Jan smoke output, not historical identity."""
import re

THINKING = re.compile(r'</?think\b[^>]*>', re.IGNORECASE)
PLANNING = re.compile(
    r'(?:^|\n)\s*(?:okay\s*,?\s*)?(?:so\s*,?\s*)?'
    r'(?:i\s+need\s+to\s+(?:answer|respond|craft|compose|write|figure\s+out\s+how\s+to\s+answer|figure\s+out\s+a\s+way)\b'
    r'|the\s+(?:user|response|prompt)\s+(?:asks|wants|should|says)\b'
    r'|(?:let\s+me|i\s+should)\s+(?:craft|formulate)\s+(?:a|the)\s+(?:reply|answer|response)\b)',
    re.IGNORECASE,
)


def classify_answer(reply, finish_reason):
    """Return structural eligibility only; never infer character authenticity."""
    text = reply if isinstance(reply, str) else ''
    marker = bool(THINKING.search(text))
    planning = bool(PLANNING.search(text))
    complete = bool(text.strip()) and finish_reason == 'stop' and not (marker or planning)
    return {
        'complete_user_answer': complete,
        'has_thinking_marker': marker,
        'has_unmarked_planning': planning,
        'finish_reason_stop': finish_reason == 'stop',
    }
