const trendData = JSON.parse(document.getElementById('trend-data').textContent);
const ctx = document.getElementById('trendChart').getContext('2d');

// Biểu đồ hiển thị calories trực tiếp và scale protein (x10) để dễ nhìn cột.
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: trendData.map((d) => d.date),
    datasets: [
      {
        label: 'Calories (kcal)',
        data: trendData.map((d) => d.calories),
        backgroundColor: '#a5d6a7',
        borderRadius: 6,
      },
      {
        label: 'Protein (g×10)',
        data: trendData.map((d) => d.protein * 10),
        backgroundColor: '#90caf9',
        borderRadius: 6,
      },
    ],
  },
  options: {
    responsive: true,
    plugins: { legend: { position: 'top' } },
    scales: { y: { beginAtZero: true, grid: { color: '#f0f4f0' } } },
  },
});

function getCsrf() {
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

window.searchFoods = async function searchFoods(q) {
  // Backend trả về danh sách gọn cho ô tìm kiếm trong modal.
  const res = await fetch('/api/foods/search/?q=' + encodeURIComponent(q));
  let data = null;
  try {
    data = await readJsonResponse(res, '/api/foods/search/');
  } catch (error) {
    data = [];
  }
  const searchError = res.headers.get('X-Food-Search-Error');
  const sel = document.getElementById('log-food');
  if (!Array.isArray(data) || data.length === 0) {
    const msg = searchError || 'Không tìm thấy món phù hợp';
    sel.innerHTML = `<option value="">${msg}</option>`;
    return;
  }
  sel.innerHTML = data
    .map(
      (f) =>
        `<option value="${f.id}" data-cal="${f.calories}" data-serving="${f.serving_size}">${f.name} — ${Math.round(f.calories)} kcal</option>`
    )
    .join('');
};

window.updateCalPreview = function updateCalPreview() {
  // Ước tính kcal theo thời gian thực: calories món chọn * số khẩu phần.
  const sel = document.getElementById('log-food');
  const opt = sel.selectedOptions[0];
  if (!opt) return;
  const cal = parseFloat(opt.dataset.cal) * parseFloat(document.getElementById('log-servings').value || 1);
  const preview = document.getElementById('cal-preview');
  preview.style.display = 'block';
  preview.innerHTML = `<i class="bi bi-fire me-1"></i>≈ <strong>${Math.round(cal)} kcal</strong>  ${
    opt.dataset.serving ? '· ' + opt.dataset.serving : ''
  }`;
};

window.logFood = async function logFood() {
  const sel = document.getElementById('log-food');
  if (!sel.value) {
    alert('Vui lòng chọn món ăn');
    return;
  }

  const res = await fetch('/api/nutrition/log/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify({
      food_id: sel.value,
      date: document.getElementById('log-date').value,
      meal_type: document.getElementById('log-meal-type').value,
      servings: document.getElementById('log-servings').value,
    }),
  });

  // Reload để cập nhật thẻ tổng quan và danh sách bữa ăn theo dữ liệu server.
  if (res.ok) {
    location.reload();
    return;
  }

  try {
    const data = await readJsonResponse(res, '/api/nutrition/log/');
    alert(data.error || data.message || 'Có lỗi xảy ra.');
  } catch {
    alert('Có lỗi xảy ra.');
  }
};

window.deleteLog = async function deleteLog(id) {
  if (!confirm('Xóa bữa ăn này?')) return;
  await fetch(`/api/nutrition/delete/${id}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrf() },
  });
  location.reload();
};
