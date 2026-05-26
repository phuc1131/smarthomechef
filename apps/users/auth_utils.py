from django.contrib.auth.hashers import check_password, identify_hasher, make_password


def _normalize_stored_pw(pw: str) -> str:
    """Chuẩn hóa một số dạng thường gặp của giá trị mật khẩu trong DB.

    - Loại bỏ trắng hai đầu.
    - Bỏ dấu nháy đơn/nháy kép nếu toàn bộ chuỗi được quote.
    - Nếu có dạng bytes literal like "b'...'", sẽ cố gắng tách phần bên trong.
    """
    if pw is None:
        return ''
    s = pw.strip()
    if (s.startswith("\'") and s.endswith("\'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    if s.startswith("b'") and s.endswith("'"):
        s = s[2:-1]
    if s.startswith('b"') and s.endswith('"'):
        s = s[2:-1]
    return s


def verify_account_password(account, raw_password, *, upgrade_plaintext=True):
    stored_password = (getattr(account, 'password_hash', '') or '')
    stored_password = _normalize_stored_pw(stored_password)
    if not stored_password:
        return False

    # Thử dùng check_password (hỗ trợ các hasher chuẩn của Django)
    try:
        if check_password(raw_password, stored_password):
            return True
    except (ValueError, TypeError):
        # Một số giá trị lưu trữ có thể không hợp lệ với identify_hasher/check_password
        # tiếp tục xuống phần so sánh thô
        pass

    # So sánh thô (đối với trường hợp mật khẩu được lưu plaintext trong DB)
    if raw_password == stored_password:
        # Nếu stored_password không phải hash chuẩn, nâng cấp nó sang hash an toàn
        try:
            identify_hasher(stored_password)
        except Exception:
            if upgrade_plaintext:
                account.password_hash = make_password(raw_password)
                try:
                    account.save(update_fields=['password_hash'])
                except Exception:
                    # Không bắt được lỗi lưu; vẫn coi mật khẩu đúng
                    pass
        return True

    return False