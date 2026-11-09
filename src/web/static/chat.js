
const chat = document.querySelector('#chat');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const sendButton = document.querySelector('#send');
const status = document.querySelector('#service-status');
const newChatButton = document.querySelector('#new-chat');
const characterCount = document.querySelector('#character-count');

let conversationId = localStorage.getItem('ipl_conversation_id') || null;
let isSubmitting = false;

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

// Add a plain assistant message to the chat.
function addAssistantMessage(message, className = 'chat-assistant') {
  try {
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message ${className}"><span class="message-label">IPL Insights Assistant</span>${escapeHtml(message)}</article>`);
    scrollToLatest();
  } catch (error) {
    console.error(`[FRONTEND] Unable to add assistant message: ${error.message}`);
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

// Update the progress message.
function updateProgress(progressId, message) {
  try {
    const progressElement = document.querySelector(`#${progressId} span:last-child`);
    if (progressElement) progressElement.textContent = message;
  } catch (error) {
    console.error(`[FRONTEND] Progress update failed: ${error.message}`);
  }
}

// Remove the progress message.
function removeProgress(progressId) {
  try {
    document.querySelector(`#${progressId}`)?.remove();
  } catch (error) {
    console.error(`[FRONTEND] Progress removal failed: ${error.message}`);
  }
}

// Render the KPI cards returned by the API.
function kpiCards(kpis) {
  try {
    if (!kpis || typeof kpis !== 'object' || Array.isArray(kpis)) return '';
    return `<div class="kpi-grid">${Object.entries(kpis).map(([key, value]) => `<div class="kpi"><span class="kpi-name">${escapeHtml(key.replaceAll('_', ' '))}</span><strong class="kpi-value">${escapeHtml(value)}</strong></div>`).join('')}</div>`;
  } catch (error) {
    console.error(`[FRONTEND] KPI rendering failed: ${error.message}`);
    return '';
  }
}

// Render the statistical insights returned by the API.
function insightsList(insights) {
  try {
    if (!Array.isArray(insights) || !insights.length) return '';
    return `<h3 class="analysis-subtitle">Key insights</h3><ul class="insights">${insights.map(insight => `<li>${escapeHtml(insight)}</li>`).join('')}</ul>`;
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
      return `<div class="bar-row"><span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span><span class="bar-track"><span class="bar-value" style="width:${width}%"></span></span><strong class="bar-number">${escapeHtml(parseFloat(values[index]).round(2))}</strong></div>`;
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
      ? `<polyline points="${points.map(point => `${point.x},${point.y}`).join(' ')}" fill="none" stroke="#0f9488" stroke-width="3" stroke-linejoin="round"/>`
      : '';
    const circles = points.map((point, index) => `<circle cx="${point.x}" cy="${point.y}" r="5" fill="#0f9488"><title>${escapeHtml(labels[index])}: ${escapeHtml(values[index])}</title></circle>`).join('');
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
    const palette = ['#0f9488', '#d97706', '#2563eb', '#9333ea', '#dc2626', '#64748b', '#0891b2', '#65a30d'];
    let cumulative = 0;
    const segments = values.map((value, index) => {
      const start = cumulative;
      cumulative += value / total * 100;
      return `${palette[index % palette.length]} ${start}% ${cumulative}%`;
    });
    const legend = labels.map((label, index) => `<div class="pie-legend-item"><span class="pie-swatch" style="background:${palette[index % palette.length]}"></span><span>${escapeHtml(label)}</span><strong>${escapeHtml(parseFloat(values[index]).round(2))}</strong></div>`).join('');
    return `<div class="pie-wrap"><div class="pie-chart" style="background:conic-gradient(${segments.join(',')})"></div><div class="pie-legend">${legend}</div></div>`;
  } catch (error) {
    console.error(`[FRONTEND] Pie chart rendering failed: ${error.message}`);
    return '';
  }
}

// Render one visualization returned by the backend.
function singleChartMarkup(chart) {
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

// Render all visualizations returned by the backend.
function chartMarkup(visualizations) {
  try {
    if (!Array.isArray(visualizations)) return '';
    return visualizations.map(singleChartMarkup).filter(Boolean).join('');
  } catch (error) {
    console.error(`[FRONTEND] Multiple chart rendering failed: ${error.message}`);
    return '';
  }
}

// Render the analytical result table.
function resultTable(table) {
  try {
    if (!table || !Array.isArray(table.columns) || !Array.isArray(table.rows) || !table.rows.length) return '';
    const headers = table.columns.map(column => `<th>${escapeHtml(column.replaceAll('_', ' '))}</th>`).join('');
    const rows = table.rows.map(row => `<tr>${table.columns.map(column => `<td>${escapeHtml(row[column])}</td>`).join('')}</tr>`).join('');
    return `<section class="result-table-section"><h3>Analytical results</h3><div class="result-table-wrapper"><table class="result-table"><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table></div><p class="table-caption">Showing up to 100 returned records.</p></section>`;
  } catch (error) {
    console.error(`[FRONTEND] Result table rendering failed: ${error.message}`);
    return '';
  }
}

// Render domain-specific cricket analytics in a collapsible section.
function domainAnalyticsMarkup(analytics) {
  try {
    if (!analytics || typeof analytics !== 'object' || !Object.keys(analytics).length) return '';
    return `<details class="domain-analytics"><summary>Advanced cricket analytics</summary><pre>${escapeHtml(JSON.stringify(analytics, null, 2))}</pre></details>`;
  } catch (error) {
    console.error(`[FRONTEND] Domain analytics rendering failed: ${error.message}`);
    return '';
  }
}

// Render a clarification response from the assistant.
function addClarification(data) {
  try {
    const message = data.clarification_question || data.message || 'Could you clarify what you would like to analyse?';
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message clarification-card"><span class="message-label">One quick clarification</span><p>${escapeHtml(message)}</p></article>`);
    scrollToLatest();
  } catch (error) {
    console.error(`[FRONTEND] Clarification rendering failed: ${error.message}`);
  }
}

// Add the completed analytical result to the chat.
function addResult(data) {
  try {
    if (data.status === 'clarification') {
      addClarification(data);
      return;
    }
    if (data.status === 'error') {
      addAssistantMessage(data.message || 'The analysis could not be completed.', 'message-error');
      return;
    }
    if (data.status === 'no_data') {
      chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message no-data-card"><span class="message-label">No matching data</span>${escapeHtml(data.message || 'No relevant IPL data was found for this question.')}</article>`);
      scrollToLatest();
      return;
    }
    const visualizations = data.visualizations || (data.visualization ? [data.visualization] : []);
    chat.firstElementChild.insertAdjacentHTML('beforeend', `<article class="message analysis-card"><p class="analysis-title">Analysis complete</p>${kpiCards(data.kpis)}${insightsList(data.insights)}${chartMarkup(visualizations)}${resultTable(data.table)}${domainAnalyticsMarkup(data.domain_analytics)}</article>`);
    scrollToLatest();
  } catch (error) {
    console.error(`[FRONTEND] Unable to display analysis result: ${error.message}`);
    addAssistantMessage('The analysis was generated, but the result could not be displayed.', 'message-error');
  }
}

// Persist the conversation identifier received from the backend.
function saveConversationId(data) {
  try {
    if (!data.conversation_id) return;
    conversationId = data.conversation_id;
    localStorage.setItem('ipl_conversation_id', conversationId);
  } catch (error) {
    console.error(`[FRONTEND] Conversation ID persistence failed: ${error.message}`);
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
    saveConversationId(data);
    if (eventName === 'progress') {
      updateProgress(progressId, data.message || 'Working on your analysis...');
    } else if (eventName === 'complete' || eventName === 'clarification') {
      removeProgress(progressId);
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

// Enable or disable the chat controls during a request.
function setSubmittingState(submitting) {
  try {
    isSubmitting = submitting;
    sendButton.disabled = submitting;
    input.disabled = submitting;
    newChatButton.disabled = submitting;
    sendButton.textContent = submitting ? 'Working...' : 'Send ↗';
  } catch (error) {
    console.error(`[FRONTEND] Chat state update failed: ${error.message}`);
  }
}

// Submit a question and process the streamed analysis response.
async function submitQuestion(message) {
  addUserMessage(message);
  const progressId = addProgress('Understanding your question...');
  setSubmittingState(true);
  let completed = false;
  try {
    console.log('[FRONTEND] Submitting analytics question.');
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
    removeProgress(progressId);
    console.error(`[FRONTEND] Question submission failed: ${error.message}`);
    addAssistantMessage(error.message || 'Unable to get an answer. Please try again.', 'message-error');
  } finally {
    setSubmittingState(false);
    input.focus();
  }
}

// Restore the previous conversation when the page is refreshed.
async function restoreConversation() {
  try {
    if (!conversationId) return;
    console.log('[FRONTEND] Restoring previous conversation.');
    const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}`);
    if (!response.ok) {
      if (response.status === 404) {
        localStorage.removeItem('ipl_conversation_id');
        conversationId = null;
      }
      return;
    }
    const data = await response.json();
    const messages = Array.isArray(data.messages) ? data.messages : [];
    if (!messages.length) return;
    chat.firstElementChild.innerHTML = '';
    messages.forEach(message => {
      const content = message.content || message.message || message.text || '';
      if (!content) return;
      if (message.role === 'user') addUserMessage(content);
      else addAssistantMessage(content);
    });
    scrollToLatest();
  } catch (error) {
    console.error(`[FRONTEND] Conversation restoration failed: ${error.message}`);
  }
}

// Start a new conversation and clear the current chat.
function startNewChat() {
  try {
    if (isSubmitting) return;
    conversationId = null;
    localStorage.removeItem('ipl_conversation_id');
    chat.firstElementChild.innerHTML = `<article class="message message-intro"><span class="message-label">IPL Insights Assistant</span>Welcome! I can help you explore IPL data across seasons, teams, players and venues. Ask a question to get started.</article>`;
    input.value = '';
    updateCharacterCount();
    input.focus();
    console.log('[FRONTEND] Started a new conversation.');
  } catch (error) {
    console.error(`[FRONTEND] Unable to start a new conversation: ${error.message}`);
  }
}

// Update the composer character counter.
function updateCharacterCount() {
  try {
    characterCount.textContent = `${input.value.length} / 1000`;
  } catch (error) {
    console.error(`[FRONTEND] Character counter update failed: ${error.message}`);
  }
}

// Resize the question input to fit its content.
function resizeInput() {
  try {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
  } catch (error) {
    console.error(`[FRONTEND] Textarea resize failed: ${error.message}`);
  }
}

// Display the backend health status.
async function checkServiceHealth() {
  try {
    const response = await fetch('/health');
    if (!response.ok) throw new Error(`Health endpoint returned HTTP ${response.status}.`);
    const data = await response.json();
    const online = data.backend === 'connected';
    status.textContent = online ? 'Analytics service online' : 'Backend unavailable';
    status.classList.toggle('online', online);
    status.classList.toggle('offline', !online);
  } catch (error) {
    console.error(`[FRONTEND] Health check failed: ${error.message}`);
    status.textContent = 'Backend unavailable';
    status.classList.add('offline');
  }
}

// Handle question submission.
form.addEventListener('submit', event => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || isSubmitting) return;
  input.value = '';
  updateCharacterCount();
  resizeInput();
  submitQuestion(message);
});

// Populate the question input when a suggestion is selected.
document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => {
  input.value = button.textContent.trim();
  updateCharacterCount();
  resizeInput();
  input.focus();
}));

// Start a fresh conversation when the new-chat button is selected.
newChatButton.addEventListener('click', startNewChat);

// Update the input size and character count as the user types.
input.addEventListener('input', () => {
  updateCharacterCount();
  resizeInput();
});

// Submit on Enter and insert a new line on Shift + Enter.
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

// Initialize the frontend when the page loads.
async function initializeApp() {
  console.log('[FRONTEND] Initializing IPL Insights.');
  await restoreConversation();
  await checkServiceHealth();
  updateCharacterCount();
  resizeInput();
}

initializeApp();
