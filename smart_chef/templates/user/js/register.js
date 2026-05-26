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

async function submitRegister(payload) {
  // Luôn xóa lỗi cũ trước khi gửi để tránh hiển thị thông báo cũ.
  clearError();
  try {
    const res = await fetch('/auth/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      },
      body: JSON.stringify(payload),
    });
    const data = await readJsonResponse(res, '/auth/register/');
    if (!res.ok || !data.ok) {
      // Backend trả lý do lỗi dạng dễ đọc trong trường error.
      showError(data.error || 'Không thể đăng ký');
      return;
    }
    // Backend tự tạo session sau đăng ký thành công.
    window.location.href = '/';
  } catch (error) {
    showError('Lỗi kết nối: ' + error.message);
  }
}

document.getElementById('register-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  // Kiểm tra phía client để tránh gọi API không cần thiết.
  if (username.length < 3) {
    showError('Tên tài khoản tối thiểu 3 ký tự');
    return;
  }
  if (password.length < 8) {
    showError('Mật khẩu tối thiểu 8 ký tự');
    return;
  }
  if (password !== confirmPassword) {
    showError('Mật khẩu xác nhận không khớp');
    return;
  }
  await submitRegister({
    username,
    password,
  });
});

// Check for error in URL (from allauth redirect)
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.has('error')) {
  showError('Lỗi xác thực: ' + (urlParams.get('error') || 'Không xác định'));
}

