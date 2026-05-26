const plansByDate = JSON.parse(document.getElementById('plans-by-date-data').textContent);
const mealColorsEl = document.getElementById('meal-type-colors-data');
const mealColors = mealColorsEl ? JSON.parse(mealColorsEl.textContent) : {};

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

function renderPlans() {
  // Vẽ các badge thực đơn vào đúng ô ngày trên lịch.
  Object.entries(plansByDate).forEach(([dateKey, plans]) => {
    const el = document.getElementById('day-' + dateKey);
    if (!el) return;
    plans.forEach((p) => {
      const span = document.createElement('span');
      span.className = 'plan-badge ' + (mealColors[p.meal_type] || 'bg-secondary text-white');
      span.textContent = p.food;
      span.title = `${p.meal_type}: ${p.food}`;
      el.appendChild(span);
    });
  });
}

window.openAddForDate = function openAddForDate(dateStr) {
  // Điền sẵn ngày được chọn để giảm thao tác nhập tay trong modal.
  document.getElementById('plan-date').value = dateStr;
  new bootstrap.Modal(document.getElementById('addPlanModal')).show();
};

const allFoodOptions = Array.from(document.getElementById('plan-food').options).map((o) => ({
  value: o.value,
  text: o.text,
}));

window.filterPlanFoods = async function filterPlanFoods(q) {
  // Ưu tiên gọi API để tìm món mới ngoài CSDL cục bộ và tự động cache về server.
  const sel = document.getElementById('plan-food');
  const keyword = (q || '').trim();

  if (!keyword) {
    sel.innerHTML = allFoodOptions.map((o) => `<option value="${o.value}">${o.text}</option>`).join('');
    return;
  }

  try {
    const res = await fetch('/api/foods/search/?q=' + encodeURIComponent(keyword));
    if (!res.ok) {
      throw new Error('Search request failed');
    }
    const data = await readJsonResponse(res, '/api/foods/search/');
    const searchError = res.headers.get('X-Food-Search-Error');

    if (!Array.isArray(data) || data.length === 0) {
      const msg = searchError || 'Không tìm thấy món phù hợp';
      sel.innerHTML = `<option value="">${msg}</option>`;
      return;
    }

    sel.innerHTML = data
      .map(
        (f) =>
          `<option value="${f.id}">${f.name} (${Math.round(Number(f.calories || 0))} kcal)</option>`
      )
      .join('');
  } catch {
    // Fallback local để không làm hỏng UX nếu API gặp lỗi tạm thời.
    const lq = keyword.toLowerCase();
    const fallback = allFoodOptions.filter((o) => o.text.toLowerCase().includes(lq));
    sel.innerHTML = fallback.length
      ? fallback.map((o) => `<option value="${o.value}">${o.text}</option>`).join('')
      : '<option value="">Không tìm thấy món phù hợp</option>';
  }
};

window.addPlan = async function addPlan() {
  const data = {
    date: document.getElementById('plan-date').value,
    meal_type: document.getElementById('plan-meal-type').value,
    food_id: document.getElementById('plan-food').value,
    servings: document.getElementById('plan-servings').value,
    notes: document.getElementById('plan-notes').value,
  };

  if (!data.food_id) {
    alert('Vui lòng chọn món ăn');
    return;
  }

  const res = await fetch('/api/meal-plan/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify(data),
  });

  // Reload để lịch hiển thị đúng dữ liệu mới nhất từ server.
  if (res.ok) {
    location.reload();
    return;
  }

  try {
    const data = await readJsonResponse(res, '/api/meal-plan/add/');
    alert(data.error || data.message || 'Có lỗi xảy ra.');
  } catch {
    alert('Có lỗi xảy ra.');
  }
};

renderPlans();
