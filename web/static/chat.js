const chat = document.querySelector('#chat');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const sendButton = document.querySelector('#send');
const status = document.querySelector('#service-status');

let conversationId = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'
  }[character]));
}

function scrollToLatest() {
  chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
}

function addUserMessage(message) {
  chat.firstElementChild.insertAdjacentHTML('beforeend', `
    <article class="message chat-user">
      ${escapeHtml(message)}
    </article>`);
  scrollToLatest();
}

function addProgress(message) {
  const id = `progress-${Date.now()}`;
  chat.firstElementChild.insertAdjacentHTML('beforeend', `
    <article id="${id}" class="message chat-progress">
      <span class="pulse"></span><span>${escapeHtml(message)}</span>
    </article>`);
  scrollToLatest();
  return id;
}

function kpiCards(kpis) {
  if (!kpis || typeof kpis !== 'object') return '';
  return `<div class="kpi-grid">${Object.entries(kpis).map(([key, value]) => `
    <div class="kpi">
      <span class="kpi-name">${escapeHtml(key)}</span>
      <strong class="kpi-value">${escapeHtml(value)}</strong>
    </div>`).join('')}</div>`;
}

function insightsList(insights) {
  const values = Array.isArray(insights) ? insights : (insights ? [insights] : []);
  if (!values.length) return '';
  return `<ul class="insights">${values.map(insight => `<li>${escapeHtml(insight)}</li>`).join('')}</ul>`;
}

function chartMarkup(chart) {
  if (!chart?.create_visualization) return '';
  const xs = chart.x_values || [];
  const ys = chart.y_values || [];
  if (!xs.length || xs.length !== ys.length) return '';
  const max = Math.max(...ys.map(Number), 1);
  const rows = xs.map((label, index) => {
    const width = Math.max(3, (Number(ys[index]) / max) * 100);
    return `<div class="bar-row">
      <span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
      <span class="bar-track"><span class="bar-value" style="width:${width}%"></span></span>
      <strong class="bar-number">${escapeHtml(ys[index])}</strong>
    </div>`;
  }).join('');
  return `<section class="chart">
    <p class="chart-type">${escapeHtml(chart.chart_type || 'Chart')}</p>
    <h3>${escapeHtml(chart.title || 'IPL visualisation')}</h3>
    <p>${escapeHtml(chart.description || '')}</p>
    <div class="bar-list">${rows}</div>
    <p class="chart-axis">${escapeHtml(chart.x_column || 'Category')} · ${escapeHtml(chart.y_column || 'Value')}</p>
  </section>`;
}

function addResult(data) {
  const noData = data.status === 'no_data';
  chat.firstElementChild.insertAdjacentHTML('beforeend', `
    <article class="message analysis-card">
      <p class="analysis-title">${noData ? 'No data found' : 'Analysis complete'}</p>
      ${noData ? `<p>${escapeHtml(data.message || 'No relevant data found.')}</p>` : `
        ${kpiCards(data.kpis)}
        ${insightsList(data.insights)}
        ${chartMarkup(data.visualization)}`}
    </article>`);
  scrollToLatest();
}

async function submitQuestion(message) {
  addUserMessage(message);
  const progressId = addProgress('Sending your question to the analytics team…');
  sendButton.disabled = true;
  input.disabled = true;

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, conversation_id: conversationId })
    });
    if (!response.ok || !response.body) throw new Error('Service unavailable');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop();
      for (const rawEvent of events) {
        const eventName = rawEvent.match(/^event:\s*(.+)$/m)?.[1] || 'message';
        const dataLine = rawEvent.match(/^data:\s*(.+)$/m)?.[1];
        if (!dataLine) continue;
        const data = JSON.parse(dataLine);
        conversationId = data.conversation_id || conversationId;
        if (eventName === 'progress') document.querySelector(`#${progressId} span:last-child`).textContent = data.message;
        if (eventName === 'complete') { document.querySelector(`#${progressId}`)?.remove(); addResult(data); }
        if (eventName === 'error') throw new Error(data.message);
      }
    }
  } catch (error) {
    document.querySelector(`#${progressId}`)?.remove();
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message">${escapeHtml(error.message || 'Unable to get an answer. Please try again.')}</article>`);
    scrollToLatest();
  } finally {
    sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  submitQuestion(message);
});

document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => {
  input.value = button.textContent.trim();
  input.focus();
}));

fetch('/health').then(response => response.json()).then(data => {
  status.textContent = data.backend === 'connected' ? '● Analytics service online' : '● Backend unavailable';
  status.className = 'status';
}).catch(() => { status.textContent = '● Backend unavailable'; });
