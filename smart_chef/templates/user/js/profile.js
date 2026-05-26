function getCsrf() {
  return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
}

window.saveProfile = async function saveProfile() {
  // Gom toàn bộ dữ liệu form profile để backend xử lý upsert trong một lần.
  const data = {
    name: document.getElementById('p-name').value,
    age: document.getElementById('p-age').value || null,
    weight: document.getElementById('p-weight').value || null,
    height: document.getElementById('p-height').value || null,
    gender: document.getElementById('p-gender').value,
    daily_calorie_target: document.getElementById('p-calorie').value || null,
    health_goal: document.getElementById('p-goal').value,
    activity_level: document.getElementById('p-activity').value,
    medical_conditions: document.getElementById('p-conditions').value,
    dietary_preferences: document.getElementById('p-diet').value,
  };

  const res = await fetch('/api/profile/save/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify(data),
  });

  if (res.ok) {
    const status = document.getElementById('save-status');
    status.style.display = 'inline';
    // Trì hoãn ngắn để người dùng kịp thấy trạng thái lưu thành công.
    setTimeout(() => {
      location.reload();
    }, 1200);
  }
};


window.showDeleteAccountModal = function showDeleteAccountModal() {
  const modalEl = document.getElementById('deleteAccountModal')
  if (!modalEl) return
  const modal = new bootstrap.Modal(modalEl)
  document.getElementById('delete-password').value = ''
  document.getElementById('delete-error').style.display = 'none'
  modal.show()
}

window.confirmDeleteAccount = async function confirmDeleteAccount() {
  const pwdField = document.getElementById('delete-password')
  const pwd = pwdField ? (pwdField.value || null) : null
  const btn = document.getElementById('confirm-delete-btn')
  btn.disabled = true
  btn.innerHTML = 'Đang xóa...'

  try {
    const res = await fetch('/api/accounts/delete/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ password: pwd }),
    })

    const data = await res.json().catch(() => ({}))
    if (res.ok && data.ok) {
      // Redirect to login or homepage after account deactivation
      window.location = '/dang-nhap/?deleted=1'
      return
    }

    const errEl = document.getElementById('delete-error')
    errEl.style.display = 'block'
    errEl.textContent = data.error || 'Không thể xóa tài khoản. Vui lòng thử lại.'
  } catch (e) {
    const errEl = document.getElementById('delete-error')
    errEl.style.display = 'block'
    errEl.textContent = 'Lỗi kết nối. Vui lòng thử lại.'
  } finally {
    btn.disabled = false
    btn.innerHTML = 'Xác nhận xóa'
  }
}

