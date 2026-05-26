import re
from typing import List


def normalize_chat_text(text: str) -> str:
    if text is None:
        return ''
    normalized = text.strip().lower()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r"[^\w\s'-]+", '', normalized, flags=re.UNICODE)
    return normalized


def tokenize_chat_text(text: str) -> List[str]:
    normalized = normalize_chat_text(text)
    if not normalized:
        return []
    return re.findall(r"[\w'-]+", normalized, flags=re.UNICODE)
