from typing import Any, Dict, Optional


def append_health_feedback(response_text: str, account: Any = None, user_text: Optional[str] = None) -> str:
    if response_text is None:
        response_text = ''
    return response_text


def build_health_feedback(account: Any = None, user_text: Optional[str] = None) -> Dict[str, Any]:
    return {
        'message': '',
        'user_text': user_text or '',
        'account_id': getattr(account, 'id', None),
    }
