const modelLabels = window.ADMIN_DASHBOARD_DATA.modelLabels;
const modelCounts = window.ADMIN_DASHBOARD_DATA.modelCounts;
const topModelLabels = window.ADMIN_DASHBOARD_DATA.topModelLabels;
const topModelCounts = window.ADMIN_DASHBOARD_DATA.topModelCounts;
const trendLabels = window.ADMIN_DASHBOARD_DATA.trendLabels;
const trendChat = window.ADMIN_DASHBOARD_DATA.trendChat;
const trendMeal = window.ADMIN_DASHBOARD_DATA.trendMeal;
const trendNutrition = window.ADMIN_DASHBOARD_DATA.trendNutrition;
const intentLabels = window.ADMIN_DASHBOARD_DATA.intentLabels;
const intentCounts = window.ADMIN_DASHBOARD_DATA.intentCounts;

new Chart(document.getElementById('modelChart'), {
  type: 'bar',
  data: {
    labels: modelLabels,
    datasets: [{
      label: 'Rows',
      data: modelCounts,
      backgroundColor: '#1f7a8c',
      borderRadius: 8,
    }],
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { maxRotation: 65, minRotation: 20 } },
      y: { beginAtZero: true },
    },
  },
});

new Chart(document.getElementById('topModelChart'), {
  type: 'bar',
  data: {
    labels: topModelLabels.length ? topModelLabels : ['No data'],
    datasets: [{
      label: 'Top models',
      data: topModelCounts.length ? topModelCounts : [0],
      backgroundColor: ['#0ea5e9', '#22c55e', '#f59e0b', '#a855f7', '#ef4444'],
      borderRadius: 8,
    }],
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true } },
  },
});

new Chart(document.getElementById('trendChart'), {
  type: 'line',
  data: {
    labels: trendLabels,
    datasets: [
      { label: 'Chat messages', data: trendChat, borderColor: '#0ea5e9', backgroundColor: 'rgba(14,165,233,.15)', tension: 0.3, fill: true },
      { label: 'Meal plans', data: trendMeal, borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,.12)', tension: 0.3, fill: true },
      { label: 'Nutrition logs', data: trendNutrition, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.14)', tension: 0.3, fill: true },
    ],
  },
  options: {
    responsive: true,
    scales: { y: { beginAtZero: true } },
  },
});

new Chart(document.getElementById('intentChart'), {
  type: 'doughnut',
  data: {
    labels: intentLabels.length ? intentLabels : ['No data'],
    datasets: [{
      data: intentCounts.length ? intentCounts : [1],
      backgroundColor: ['#0ea5e9', '#22c55e', '#f59e0b', '#a855f7', '#ef4444', '#14b8a6', '#64748b', '#8b5cf6'],
    }],
  },
  options: {
    responsive: true,
    plugins: { legend: { position: 'bottom' } },
  },
});

const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');

function runSearch() {
  const q = searchInput.value.trim();
  const url = new URL(window.location.href);
  if (q) {
    url.searchParams.set('q', q);
  } else {
    url.searchParams.delete('q');
  }
  window.location.href = url.toString();
}

searchBtn?.addEventListener('click', runSearch);
searchInput?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    runSearch();
  }
});
