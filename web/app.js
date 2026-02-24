const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const collaborateEl = document.getElementById('collaborate');
const chipsEl = document.getElementById('chips');
const aliasEl = document.getElementById('alias');
const transportEl = document.getElementById('transport');
const commandEl = document.getElementById('command');
const addModelBtn = document.getElementById('addModel');
const resetBtn = document.getElementById('reset');

async function api(path, method = 'GET', body) {
  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || '请求失败');
  return data;
}

function renderMessage(msg) {
  const item = document.createElement('div');
  item.className = `msg ${msg.role === 'user' ? 'user' : 'assistant'}`;
  if (msg.pendingId) item.dataset.pendingId = msg.pendingId;
  item.innerHTML = `
    <div class="speaker">${msg.speaker}</div>
    <div>${(msg.text || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br/>')}</div>
  `;
  messagesEl.appendChild(item);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderHistory(history) {
  messagesEl.innerHTML = '';
  history.forEach(renderMessage);
}

function showThinking(collaborate) {
  const pendingId = `pending-${Date.now()}`;
  renderMessage({
    role: 'assistant',
    speaker: collaborate ? '军师团' : '军师',
    text: '思考中...',
    pendingId,
  });
  return pendingId;
}

function clearThinking(pendingId) {
  const el = messagesEl.querySelector(`[data-pending-id="${pendingId}"]`);
  if (el) el.remove();
}

function renderChips(models) {
  chipsEl.innerHTML = '';
  models.forEach((m) => {
    const chip = document.createElement('button');
    chip.className = 'chip';
    chip.textContent = `@${m.alias}`;
    chip.addEventListener('click', () => {
      const txt = inputEl.value.trim();
      inputEl.value = txt ? `${txt} @${m.alias} ` : `@${m.alias} `;
      inputEl.focus();
    });
    chipsEl.appendChild(chip);
  });
}

async function loadInitial() {
  const [modelsData, historyData] = await Promise.all([
    api('/api/models'),
    api('/api/history')
  ]);
  renderChips(modelsData.models || []);
  renderHistory(historyData.history || []);
}

async function sendChat() {
  const text = inputEl.value.trim();
  if (!text) return;

  renderMessage({ role: 'user', speaker: '主公', text });
  const pendingId = showThinking(collaborateEl.checked);
  try {
    sendBtn.disabled = true;
    const data = await api('/api/chat', 'POST', {
      text,
      collaborate: collaborateEl.checked,
    });
    renderHistory(data.history || []);
    inputEl.value = '';
    inputEl.focus();
  } catch (err) {
    clearThinking(pendingId);
    alert(err.message);
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener('click', sendChat);

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
});

addModelBtn.addEventListener('click', async () => {
  const alias = aliasEl.value.trim();
  const transport = transportEl.value;
  const command = commandEl.value.trim();

  if (!alias) {
    alert('请输入代号');
    return;
  }

  try {
    await api('/api/models', 'POST', { alias, transport, command });
    const modelsData = await api('/api/models');
    renderChips(modelsData.models || []);
    aliasEl.value = '';
    commandEl.value = '';
  } catch (err) {
    alert(err.message);
  }
});

resetBtn.addEventListener('click', async () => {
  try {
    await api('/api/reset', 'POST', {});
    renderHistory([]);
  } catch (err) {
    alert(err.message);
  }
});

loadInitial().catch((err) => {
  alert(`初始化失败: ${err.message}`);
});
