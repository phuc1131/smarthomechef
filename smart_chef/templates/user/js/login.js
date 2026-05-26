const errorBox = document.getElementById('error-box');

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('d-none');
}

function clearError() {
  errorBox.textContent = '';
  errorBox.classList.add('d-none');
}

function getCsrf() {
  const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
  if (tokenInput) return tokenInput.value;
  return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
}

async function readJsonResponse(res, endpointLabel) {
  const raw = await res.text();
  let data = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = null;
  }
  if (!data) {
    const preview = (raw || '').trim().slice(0, 120).replace(/\s+/g, ' ');
    throw new Error(`${endpointLabel} returned ${res.status} ${res.statusText} and HTML/invalid JSON: ${preview || '(empty response)'}`);
  }
  return data;
}

async function submitLogin(payload) {
  // Xóa lỗi cũ trước mỗi lần gửi để tránh hiển thị sai trạng thái.
  clearError();
  
  try {
    const res = await fetch('/auth/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      },
      body: JSON.stringify(payload),
    });
    const data = await readJsonResponse(res, '/auth/login/');
    if (!res.ok || !data.ok) {
      // Khi đăng nhập lỗi, server trả thông điệp chi tiết trong trường error.
      showError(data.error || 'Không thể đăng nhập');
      return;
    }
    // Đăng nhập thành công thì chuyển về trang chính.
    window.location.href = '/';
  } catch (error) {
    showError('Lỗi kết nối: ' + error.message);
  }
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  // Luồng đăng nhập bằng tên tài khoản/mật khẩu (không dùng email).
  await submitLogin({
    username: document.getElementById('username').value.trim(),
    password: document.getElementById('password').value,
  });
});

// Check for error in URL (from allauth redirect)
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.has('error')) {
  showError('Lỗi xác thực: ' + (urlParams.get('error') || 'Không xác định'));
}

