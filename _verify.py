import os
P = r'c:\vscode\SMART-~2\app\features\user_panel\views.py'
c = open(P, 'r', encoding='utf-8').read()
# Fix: else: followed by empty line then if not _response...
# Need to add response_text = _build_ai_quota_fallback_response(account, user_text)
old = '        else:\n\n        if not _response_matches_current_request(\n            account,\n            chat_session,\n            user_text,\n            response_text,\n            intent_name,\n            \'fallback\',\n            analysis=request_analysis,\n        ):'
new = '        else:\n            response_text = _build_ai_quota_fallback_response(account, user_text)\n\n        if not _response_matches_current_request(\n            account,\n            chat_session,\n            user_text,\n            response_text,\n            intent_name,\n            \'fallback\',\n            analysis=request_analysis,\n        ):'
if old in c:
    c = c.replace(old, new)
    open(P, 'w', encoding='utf-8').write(c)
    print("FIXED: Added missing fallback response!")
else:
    print("Pattern not found")
    idx = c.find('        else:')
    print(repr(c[idx:idx+250]))
