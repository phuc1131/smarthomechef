from apps.users.auth_backend import AllAuthAccountBridge


def auth_context(request):
    """Context processor để cung cấp current_user info cho templates"""
    user_id = request.session.get('user_id')
    user_name = (request.session.get('user_name', '') or '').strip()
    user_email = (request.session.get('user_email', '') or '').strip()
    
    # Check session-based auth first
    is_logged_in = bool(user_id)
    
    # If not logged in via session, check allauth
    if not is_logged_in and request.user.is_authenticated:
        try:
            account = AllAuthAccountBridge.sync_account_from_user(request.user)
            user_id = account.id
            user_name = account.username
            user_email = account.email
            is_logged_in = True
            # Set session for consistency
            request.session['user_id'] = account.id
            request.session['user_name'] = account.username
            request.session['user_email'] = account.email
        except Exception as e:
            print(f"Error syncing allauth user in context processor: {e}")
    
    # Guest nếu không login hoặc username bắt đầu với 'guest_'
    is_guest = (not is_logged_in) or str(user_name).strip().lower().startswith('guest_')
    display_name = user_name if is_logged_in and user_name else 'Tài khoản'
    
    return {
        'current_user': {
            'logged_in': is_logged_in,
            'is_guest': is_guest,
            'name': user_name,
            'display_name': display_name,
            'email': user_email,
            'id': user_id,
        },
    }
