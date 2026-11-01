
const chat = document.querySelector('#chat');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const sendButton = document.querySelector('#send');
const status = document.querySelector('#service-status');

let conversationId = null;

// Escape dynamic values before inserting them into HTML or SVG.
function escapeHtml(value) {
  try {
    return String(value ?? '').replace(/[&<>'"]/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'}[character]));
  } catch (error) {
    console.error(`[FRONTEND] HTML escaping failed: ${error.message}`);
    return '';
  }
}

// Scroll the chat container to its latest message.
function scrollToLatest() {
  try {
    chat.scrollTo({top: chat.scrollHeight, behavior: 'smooth'});
  } catch (error) {
    console.error(`[FRONTEND] Chat scrolling failed: ${error.message}`);
  }
}

// Add a user question to the chat.
function addUserMessage(message) {
  try {
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message chat-user">${escapeHtml(message)}</article>`);
    scrollToLatest();
  } catch (error) {
    console.error(`[FRONTEND] Unable to add user message: ${error.message}`);
  }
}

// Add a progress message and return its unique identifier.
function addProgress(message) {
  try {
    const id = `progress-${Date.now()}`;
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article id="${id}" class="message chat-progress"><span class="pulse"></span><span>${escapeHtml(message)}</span></article>`);
    scrollToLatest();
    return id;
  } catch (error) {
    console.error(`[FRONTEND] Unable to add progress message: ${error.message}`);
    throw error;
  }
}

// Render the KPI cards returned by the API.
function kpiCards(kpis) {
  try {
    if (!kpis || typeof kpis !== 'object' || Array.isArray(kpis)) return '';
    return `<div class="kpi-grid">${Object.entries(kpis).map(([key, value]) => `<div class="kpi"><span class="kpi-name">${escapeHtml(key)}</span><strong class="kpi-value">${escapeHtml(value)}</strong></div>`).join('')}</div>`;
  } catch (error) {
    console.error(`[FRONTEND] KPI rendering failed: ${error.message}`);
    return '';
  }
}

// Render the statistical insights returned by the API.
function insightsList(insights) {
  try {
    if (!Array.isArray(insights) || !insights.length) return '';
    return `<ul class="insights">${insights.map(insight => `<li>${escapeHtml(insight)}</li>`).join('')}</ul>`;
  } catch (error) {
    console.error(`[FRONTEND] Insight rendering failed: ${error.message}`);
    return '';
  }
}

// Render a bar chart using the supplied analytical values.
function renderBarChart(labels, values, maxValue) {
  try {
    const rows = labels.map((label, index) => {
      const width = Math.abs(values[index]) / maxValue * 100;
      return `<div class="bar-row"><span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span><span class="bar-track"><span class="bar-value" style="width:${width}%"></span></span><strong class="bar-number">${escapeHtml(values[index])}</strong></div>`;
    }).join('');
    return `<div class="bar-list">${rows}</div>`;
  } catch (error) {
    console.error(`[FRONTEND] Bar chart rendering failed: ${error.message}`);
    return '';
  }
}

// Render a line or scatter chart using SVG.
function renderXYChart(labels, xValues, values, chartType) {
  try {
    const width = 640;
    const height = 250;
    const padding = 42;
    const plotWidth = width - padding * 2;
    const plotHeight = height - padding * 2;
    const numericX = chartType === 'scatter' ? xValues.map(Number) : labels.map((_, index) => index);
    const minX = Math.min(...numericX);
    const maxX = Math.max(...numericX);
    const minY = Math.min(...values);
    const maxY = Math.max(...values);
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const points = numericX.map((value, index) => ({
      x: padding + ((value - minX) / rangeX) * plotWidth,
      y: height - padding - ((values[index] - minY) / rangeY) * plotHeight
    }));
    const marks = chartType === 'line'
      ? `<polyline points="${points.map(point => `${point.x},${point.y}`).join(' ')}" fill="none" stroke="#0f766e" stroke-width="3" stroke-linejoin="round"/>`
      : '';
    const circles = points.map((point, index) => `<circle cx="${point.x}" cy="${point.y}" r="5" fill="#0f766e"><title>${escapeHtml(labels[index])}: ${escapeHtml(values[index])}</title></circle>`).join('');
    const axis = `<line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#9ca3af"/><line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#9ca3af"/>`;
    return `<svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${chartType} chart">${axis}${marks}${circles}</svg><div class="chart-labels">${labels.map(label => `<span>${escapeHtml(label)}</span>`).join('')}</div>`;
  } catch (error) {
    console.error(`[FRONTEND] ${chartType} chart rendering failed: ${error.message}`);
    return '';
  }
}

// Render a pie chart and its legend.
function renderPieChart(labels, values, total) {
  try {
    const palette = ['#0f766e', '#d97706', '#2563eb', '#9333ea', '#dc2626', '#64748b', '#0891b2', '#65a30d'];
    let cumulative = 0;
    const segments = values.map((value, index) => {
      const start = cumulative;
      cumulative += value / total * 100;
      return `${palette[index % palette.length]} ${start}% ${cumulative}%`;
    });
    const legend = labels.map((label, index) => `<div class="pie-legend-item"><span class="pie-swatch" style="background:${palette[index % palette.length]}"></span><span>${escapeHtml(label)}</span><strong>${escapeHtml(values[index])}</strong></div>`).join('');
    return `<div class="pie-wrap"><div class="pie-chart" style="background:conic-gradient(${segments.join(',')})"></div><div class="pie-legend">${legend}</div></div>`;
  } catch (error) {
    console.error(`[FRONTEND] Pie chart rendering failed: ${error.message}`);
    return '';
  }
}

// Render the chart type selected by the Visualization Agent.

function chartMarkup(chart) {
  try {
    if (!chart?.create_visualization) return '';
    const xValues = chart.x_values;
    const labels = chart.x_labels || xValues?.map(String);
    const values = chart.y_values?.map(Number);
    if (!Array.isArray(labels) || !Array.isArray(xValues) || !Array.isArray(values) || !labels.length || labels.length !== values.length || !values.every(Number.isFinite)) return '';
    const chartType = chart.chart_type;
    const maxValue = Math.max(...values.map(Math.abs), 1);
    const total = values.reduce((sum, value) => sum + value, 0);
    let chartContent = '';
    if (chartType === 'bar') chartContent = renderBarChart(labels, values, maxValue);
    else if (chartType === 'line' || chartType === 'scatter') chartContent = renderXYChart(labels, xValues, values, chartType);
    else if (chartType === 'pie' && values.every(value => value >= 0) && total > 0) chartContent = renderPieChart(labels, values, total);
    else return '';
    return `<section class="chart"><p class="chart-type">${escapeHtml(chartType)}</p><h3>${escapeHtml(chart.title || 'IPL Visualisation')}</h3><p>${escapeHtml(chart.description || '')}</p>${chartContent}<p class="chart-axis">${escapeHtml(chart.x_column || 'Category')} · ${escapeHtml(chart.y_column || 'Value')}</p></section>`;
  } catch (error) {
    console.error(`[FRONTEND] Chart rendering failed: ${error.message}`);
    return '';
  }
}


// Add the completed analytical result to the chat.
function addResult(data) {
  try {
    const noData = data.status === 'no_data';
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message analysis-card"><p class="analysis-title">${noData ? 'No data found' : 'Analysis complete'}</p>${noData ? `<p>${escapeHtml(data.message || 'No relevant data found.')}</p>` : `${kpiCards(data.kpis)}${insightsList(data.insights)}${chartMarkup(data.visualization)}`}</article>`);
    scrollToLatest();
  } catch (error) {
    console.error(`[FRONTEND] Unable to display analysis result: ${error.message}`);
  }
}

// Process one complete Server-Sent Event.
function processSSEEvent(rawEvent, progressId) {
  try {
    const lines = rawEvent.split(/\r?\n/);
    const eventName = lines.find(line => line.startsWith('event:'))?.slice(6).trim() || 'message';
    const dataLines = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trim());
    if (!dataLines.length) return false;
    const data = JSON.parse(dataLines.join('\n'));
    conversationId = data.conversation_id || conversationId;
    if (eventName === 'progress') {
      const progressElement = document.querySelector(`#${progressId} span:last-child`);
      if (progressElement) progressElement.textContent = data.message;
    } else if (eventName === 'complete') {
      document.querySelector(`#${progressId}`)?.remove();
      addResult(data);
      return true;
    } else if (eventName === 'error') {
      throw new Error(data.message || 'The analytics service returned an error.');
    }
    return false;
  } catch (error) {
    throw new Error(`Unable to process the analytics response: ${error.message}`);
  }
}

// Submit a question and process the streamed analysis response.
async function submitQuestion(message) {
  addUserMessage(message);
  const progressId = addProgress('Sending your question to the analytics team…');
  sendButton.disabled = true;
  input.disabled = true;
  let completed = false;
  try {
    const response = await fetch('/api/chat/stream', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message, conversation_id: conversationId})});
    if (!response.ok || !response.body) throw new Error(`Analytics service returned HTTP ${response.status}.`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop();
      for (const rawEvent of events) completed = processSSEEvent(rawEvent, progressId) || completed;
    }
    if (buffer.trim()) completed = processSSEEvent(buffer, progressId) || completed;
    if (!completed) throw new Error('The response stream ended before the analysis was completed.');
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

// Handle question submission.
form.addEventListener('submit', event => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  submitQuestion(message);
});

// Populate the question input when a suggestion is selected.
document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => {
  input.value = button.textContent.trim();
  input.focus();
}));

// Display the backend health status.
fetch('/health').then(response => response.json()).then(data => {
  status.textContent = data.backend === 'connected' ? '● Analytics service online' : '● Backend unavailable';
}).catch(error => {
  console.error(`[FRONTEND] Health check failed: ${error.message}`);
  status.textContent = '● Backend unavailable';
});
