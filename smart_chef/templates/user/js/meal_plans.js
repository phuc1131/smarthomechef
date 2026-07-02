const plansByDate = JSON.parse(document.getElementById('plans-by-date-data').textContent);
const mealColorsEl = document.getElementById('meal-type-colors-data');
const mealColors = mealColorsEl ? JSON.parse(mealColorsEl.textContent) : {};
const followedDaysData = JSON.parse(document.getElementById('followed-days-data').textContent);
const followedDays = new Set(followedDaysData);

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
    throw new Error(endpointLabel + ' returned ' + res.status + ' ' + res.statusText + ' and HTML/invalid JSON: ' + (preview || '(empty response)'));
  }
  return data;
}

function updatePlanCalPreview() {
  const sel = document.getElementById('plan-food');
  const opt = sel ? sel.selectedOptions[0] : null;
  const preview = document.getElementById('plan-cal-preview');
  if (!preview) return;
  if (!opt || !opt.value) {
    preview.style.display = 'none';
    preview.innerHTML = '';
    return;
  }
  const cal = parseFloat(opt.dataset.cal || 0);
  const servings = parseFloat(document.getElementById('plan-servings').value || 1);
  preview.style.display = 'block';
  preview.innerHTML = '<i class="bi bi-fire me-1"></i>≈ <strong>' + Math.round(cal * servings) + ' kcal</strong>';
}

function renderPlans() {
  Object.entries(plansByDate).forEach(([dateKey, plans]) => {
    const el = document.getElementById('day-' + dateKey);
    if (!el) return;
    plans.forEach((p) => {
      const span = document.createElement('span');
      span.className = 'plan-badge ' + (mealColors[p.meal_type] || 'bg-secondary text-white');
      span.textContent = p.food;
      span.title = p.meal_type + ': ' + p.food;
      el.appendChild(span);
    });
  });
}


function updateFollowCheckmarks() {
  document.querySelectorAll('.follow-checkmark').forEach((el) => {
    const date = el.dataset.date;
    if (followedDays.has(date)) {
      el.style.display = 'inline';
      el.querySelector('i').className = 'bi bi-check-circle-fill text-success';
      el.title = 'Da theo thuc don (click de bo)';
    } else if (plansByDate[date] && plansByDate[date].length > 0) {
      el.style.display = 'inline';
      el.querySelector('i').className = 'bi bi-circle text-secondary';
      el.title = 'Theo doi thuc don (click de ghi nhan da an)';
    } else {
      el.style.display = 'none';
    }
  });
}

window.openAddForDate = function openAddForDate(dateStr) {
  document.getElementById('plan-date').value = dateStr;
  new bootstrap.Modal(document.getElementById('addPlanModal')).show();
};

const allFoodOptions = Array.from(document.getElementById('plan-food').options).map((o) => ({
  value: o.value,
  text: o.text,
}));

window.filterPlanFoods = async function filterPlanFoods(q) {
  const sel = document.getElementById('plan-food');
  const keyword = (q || '').trim();
  if (!keyword) {
    sel.innerHTML = allFoodOptions.map((o) => '<option value="' + o.value + '">' + o.text + '</option>').join('');
    return;
    updatePlanCalPreview();
  }
  try {
    const res = await fetch('/api/foods/search/?q=' + encodeURIComponent(keyword));
    if (!res.ok) throw new Error('Search request failed');
    const data = await readJsonResponse(res, '/api/foods/search/');
    const searchError = res.headers.get('X-Food-Search-Error');
    if (!Array.isArray(data) || data.length === 0) {
      sel.innerHTML = '<option value="">' + (searchError || 'Khong tim thay mon phu hop') + '</option>';
      updatePlanCalPreview();
      updatePlanCalPreview();
      return;
    }
    sel.innerHTML = data.map((f) => '<option value="' + f.id + '" data-cal="' + (Number(f.calories || 0)) + '" data-serving="">' + f.name + ' (' + Math.round(Number(f.calories || 0)) + ' kcal)</option>').join('');
    updatePlanCalPreview();
  } catch {
    const lq = keyword.toLowerCase();
    const fallback = allFoodOptions.filter((o) => o.text.toLowerCase().includes(lq));
    sel.innerHTML = fallback.length
      ? fallback.map((o) => '<option value="' + o.value + '">' + o.text + '</option>').join('')
      : '<option value="">Khong tim thay mon phu hop</option>';
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
    alert('Vui long chon mon an');
    return;
  }
  const res = await fetch('/api/meal-plan/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify(data),
  });
  if (res.ok) {
    location.reload();
    return;
  }
  try {
    const data = await readJsonResponse(res, '/api/meal-plan/add/');
    alert(data.error || data.message || 'Co loi xay ra.');
  } catch {
    alert('Co loi xay ra.');
  }
};

window.toggleFollowDay = async function toggleFollowDay(dateStr) {
  const currentlyFollowed = followedDays.has(dateStr);
  const newFollowState = !currentlyFollowed;
  try {
    const res = await fetch('/thuc-don/theo-doi-ngay/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ date: dateStr, follow: newFollowState }),
    });
    const data = await readJsonResponse(res, '/thuc-don/theo-doi-ngay/');
    if (data.ok) {
      if (newFollowState) {
        followedDays.add(dateStr);
      } else {
        followedDays.delete(dateStr);
      }
      updateFollowCheckmarks();
    } else {
      alert(data.error || 'Co loi xay ra');
    }
  } catch (err) {
    alert('Co loi xay ra: ' + err.message);
  }
};

renderPlans();
updateFollowCheckmarks();
