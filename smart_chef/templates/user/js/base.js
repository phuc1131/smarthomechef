const logoutBtn = document.getElementById('logout-btn');
function _getCsrfFromCookie() {
  return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
}

if (logoutBtn) {
  logoutBtn.addEventListener('click', async () => {
    try {
      // Đăng xuất dùng session nên chỉ cần gọi POST để xóa session trên server.
      await fetch('/auth/logout/', {
        method: 'POST',
        headers: { 'X-CSRFToken': _getCsrfFromCookie() },
        credentials: 'same-origin',
      });

      // Also logout from allauth if available
      try {
        await fetch('/accounts/logout/', {
          method: 'POST',
          headers: { 'X-CSRFToken': _getCsrfFromCookie() },
          credentials: 'same-origin',
        });
      } catch (e) {
        // allauth logout might not be available, ignore
      }

      window.location.href = '/dang-nhap/';
    } catch (e) {
      console.error('Logout error:', e);
      window.location.href = '/dang-nhap/';
    }
  });
}

