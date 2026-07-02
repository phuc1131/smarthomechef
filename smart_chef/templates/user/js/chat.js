if (window.marked && typeof window.marked.setOptions === 'function') {
  window.marked.setOptions({ breaks: true, gfm: true });
}

const messagesDiv = document.getElementById('chat-messages');
const typing = document.getElementById('typing-indicator');
const emptyState = document.getElementById('empty-state');
// Tin nhắn ban đầu được template nhúng vào bằng json_script.
const initialMessages = JSON.parse(document.getElementById('initial-messages-data').textContent);

function scrollBottom() {
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function renderMsg(role, content) {
  const isUser = role === 'user';
  const wrap = document.createElement('div');
  wrap.className = `d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'} mb-2`;
  if (!isUser) {
    // Tin nhắn trợ lý hỗ trợ render markdown, nhưng vẫn fallback nếu CDN markdown lỗi.
    const assistantText = typeof content === 'string' ? content : String(content ?? '');
    let html = assistantText
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>');
    try {
      if (window.marked && typeof window.marked.parse === 'function') {
        html = window.marked.parse(assistantText);
      }
    } catch (e) {
      console.error('Markdown render failed:', e);
    }
    wrap.innerHTML = `
      <div class="me-2 mt-1" style="width:28px;height:28px;border-radius:50%;background:#e8f5e9;display:flex;align-items:center;justify-content:center;flex-shrink:0">
        <i class="bi bi-robot text-success" style="font-size:.75rem"></i>
      </div>
      <div class="chat-bubble-ai" style="max-width:80%"><div class="md-content">${html}</div></div>`;
    
    // Detect recipe ID from response (if present)
    try {
      const recipeIdMatch = assistantText.match(/recipe_id["\']?\s*[:=]\s*["\']?(\d+)/i) || 
                           assistantText.match(/recipe["\']?\s*[:#]\s*["\']?(\d+)/i);
      if (recipeIdMatch && recipeIdMatch[1]) {
        window.currentRecipeId = parseInt(recipeIdMatch[1]);
        console.log('Recipe ID detected:', window.currentRecipeId);
      }
    } catch (e) {
      console.error('Error detecting recipe ID:', e);
    }
  } else {
    // Escape nội dung người dùng để tránh chèn HTML độc hại.
    const safe = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>');
    wrap.innerHTML = `<div class="chat-bubble-user">${safe}</div>`;
  }
  messagesDiv.insertBefore(wrap, typing);
}

function getCsrf() {
  const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
  if (tokenInput) return tokenInput.value;
  return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
}

// Render lịch sử khi tải trang để người dùng tiếp tục hội thoại cũ.
if (initialMessages.length === 0) {
  emptyState.style.display = 'block';
  messagesDiv.insertBefore(emptyState, typing);
} else {
  initialMessages.forEach((m) => renderMsg(m.role, m.content));
}
scrollBottom();

document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  // Tắt nút gửi tạm thời để tránh gửi trùng khi đang chờ phản hồi.
  document.getElementById('send-btn').disabled = true;
  emptyState.style.display = 'none';
  renderMsg('user', msg);
  typing.classList.add('show');
  scrollBottom();

  try {
    const chatEndpoints = ['/api/chat/send/', '/chat/send/'];
    let handled = false;
    let lastFailure = '';

    for (const endpoint of chatEndpoints) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
          body: JSON.stringify({ message: msg }),
        });
        const raw = await res.text();
        let data = {};
        try {
          data = raw ? JSON.parse(raw) : {};
        } catch {
          data = {};
        }
        if (!res.ok) {
          lastFailure = data.error || `Không thể xử lý tin nhắn (HTTP ${res.status}).`;
          continue;
        }

        typing.classList.remove('show');
        let assistantText = data.content || 'Không có phản hồi từ AI.';
        if (data.meal_plan_created && data.meal_plan_url) {
          assistantText += `\n\n[Đi tới trang Thực đơn](${data.meal_plan_url})`;
        }
        renderMsg('assistant', assistantText);

        if (data.meal_plan_created && data.meal_plan_url) {
          window.setTimeout(() => {
            window.location.assign(data.meal_plan_url);
          }, 250);
        }

        handled = true;
        break;
      } catch (err) {
        lastFailure = err && err.message ? err.message : 'Network error';
      }
    }

    if (!handled) {
      typing.classList.remove('show');
      renderMsg('assistant', lastFailure || 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.');
    }
  } catch {
    typing.classList.remove('show');
    renderMsg('assistant', 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.');
  }

  document.getElementById('send-btn').disabled = false;
  document.getElementById('chat-input').focus();
  scrollBottom();
});

window.clearChat = async function clearChat() {
  if (!confirm('Xóa toàn bộ lịch sử trò chuyện?')) return;
  try {
    const res = await fetch('/api/chat/clear/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf() },
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    location.reload();
  } catch {
    alert('Không thể xóa lịch sử chat lúc này. Vui lòng thử lại.');
  }
};
