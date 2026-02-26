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
const memoryQueryEl = document.getElementById('memoryQuery');
const memorySearchBtn = document.getElementById('memorySearch');
const memoryDatesEl = document.getElementById('memoryDates');
const memoryDetailEl = document.getElementById('memoryDetail');

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

function escapeHtml(text) {
  return (text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderRichText(text, container) {
  const raw = text || '';
  if (window.marked && window.DOMPurify) {
    const html = window.marked.parse(raw);
    container.innerHTML = window.DOMPurify.sanitize(html);
    if (window.renderMathInElement) {
      window.renderMathInElement(container, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        throwOnError: false,
      });
    }
    return;
  }
  container.innerHTML = escapeHtml(raw).replace(/\n/g, '<br/>');
}

function renderMessage(msg) {
  const item = document.createElement('div');
  item.className = `msg ${msg.role === 'user' ? 'user' : 'assistant'}`;
  if (msg.pendingId) item.dataset.pendingId = msg.pendingId;
  const safeSpeaker = escapeHtml(msg.speaker || '');
  item.innerHTML = `
    <div class="speaker">${safeSpeaker}</div>
    <div class="msg-body"></div>
  `;
  renderRichText(msg.text || '', item.querySelector('.msg-body'));
  messagesEl.appendChild(item);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderHistory(history) {
  messagesEl.innerHTML = '';
  history.forEach(renderMessage);
}

function formatMessageLine(m) {
  const time = (m.time || '').replace('T', ' ').slice(0, 19);
  return `[${time}] ${m.speaker || '未知'}(${m.role || 'unknown'}): ${m.text || ''}`;
}

function renderMemoryDates(items) {
  memoryDatesEl.innerHTML = '';
  if (!items || items.length === 0) {
    memoryDatesEl.innerHTML = '<div class="memory-item">暂无历史记录</div>';
    return;
  }
  items.forEach((row) => {
    const topics = (row.topics || []).slice(0, 6).join('、') || '无';
    const summary = row.summary || '无摘要';
    const item = document.createElement('div');
    item.className = 'memory-item';
    item.innerHTML = `
      <div class="memory-date">${row.date || ''}</div>
      <div class="memory-topics">话题：${escapeHtml(topics)}</div>
      <div class="memory-summary">${escapeHtml(summary)}</div>
      <button class="chip" data-date="${row.date || ''}" style="margin-top:6px;">查看当日详情</button>
    `;
    item.querySelector('button').addEventListener('click', () => loadMemoryDetail(row.date));
    memoryDatesEl.appendChild(item);
  });
}

async function loadMemoryDates(query = '') {
  const q = query ? `?q=${encodeURIComponent(query)}` : '';
  const data = await api(`/api/memory/dates${q}`);
  renderMemoryDates(data.dates || []);
}

async function loadMemoryDetail(date) {
  if (!date) return;
  const data = await api(`/api/memory/date?date=${encodeURIComponent(date)}`);
  const lines = (data.history || []).map(formatMessageLine);
  memoryDetailEl.textContent = lines.length ? lines.join('\n') : '该日期无聊天记录。';
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
    api('/api/history'),
    loadMemoryDates()
  ]);
  renderChips(modelsData.models || []);
  renderHistory(historyData.history || []);
}

async function sendChat() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';
  inputEl.focus();
  renderMessage({ role: 'user', speaker: '主公', text });
  const pendingId = showThinking(collaborateEl.checked);
  try {
    sendBtn.disabled = true;
    const data = await api('/api/chat', 'POST', {
      text,
      collaborate: collaborateEl.checked,
    });
    renderHistory(data.history || []);
    await loadMemoryDates(memoryQueryEl.value.trim());
  } catch (err) {
    inputEl.value = text;
    inputEl.focus();
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

memorySearchBtn.addEventListener('click', async () => {
  try {
    await loadMemoryDates(memoryQueryEl.value.trim());
  } catch (err) {
    alert(err.message);
  }
});

resetBtn.addEventListener('click', async () => {
  try {
    await api('/api/reset', 'POST', {});
    renderHistory([]);
    await loadMemoryDates(memoryQueryEl.value.trim());
    memoryDetailEl.textContent = '选择日期后可查看当日完整聊天内容。';
  } catch (err) {
    alert(err.message);
  }
});

loadInitial().catch((err) => {
  alert(`初始化失败: ${err.message}`);
});
