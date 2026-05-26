document.getElementById('clearFile')?.addEventListener('click', function () {
  document.getElementById('csvFile').value = '';
});

document.getElementById('importForm')?.addEventListener('submit', function () {
  const submitBtn = this.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Đang upload...';
});
