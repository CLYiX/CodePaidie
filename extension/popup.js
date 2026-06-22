const SITES = [
  { host: 'chatgpt.com', name: 'ChatGPT' },
  { host: 'gemini.google.com', name: 'Gemini' },
  { host: 'kimi.moonshot.cn', name: 'Kimi' },
  { host: 'tongyi.aliyun.com', name: '通义' },
  { host: 'yiyan.baidu.com', name: '文心' },
  { host: 'chat.deepseek.com', name: 'DeepSeek' },
  { host: 'chat.lmsys.org', name: 'ChatLM' },
  { host: 'huggingface.co', name: 'HuggingChat' },
];

document.addEventListener('DOMContentLoaded', async () => {
  // Load saved config
  const data = await chrome.storage.local.get(['serverUrl', 'apiKey', 'enabled', 'autoInject']);
  document.getElementById('serverUrl').value = data.serverUrl || 'http://127.0.0.1:8000';
  document.getElementById('apiKey').value = data.apiKey || '';
  document.getElementById('enabled').checked = data.enabled !== false;
  document.getElementById('autoInject').checked = data.autoInject !== false;

  // Get current tab host
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  let currentHost = '';
  try { currentHost = new URL(tab.url).hostname; } catch (e) {}

  // Render site list
  const siteList = document.getElementById('siteList');
  siteList.innerHTML = SITES.map(s => {
    const active = currentHost.includes(s.host);
    return `<div class="site">${active ? '<span class="check">●</span>' : '<span style="color:#333">○</span>'} ${s.name} ${active ? '<span style="color:#4ade80;font-size:11px;">(current)</span>' : ''}</div>`;
  }).join('');

  // Check connection
  checkConnection(data.serverUrl, data.apiKey);

  // Save button
  document.getElementById('saveBtn').addEventListener('click', async () => {
    const config = {
      serverUrl: document.getElementById('serverUrl').value.replace(/\/+$/, ''),
      apiKey: document.getElementById('apiKey').value,
      enabled: document.getElementById('enabled').checked,
      autoInject: document.getElementById('autoInject').checked,
    };
    await chrome.storage.local.set(config);
    checkConnection(config.serverUrl, config.apiKey);
    const hint = document.getElementById('saveHint');
    hint.textContent = 'Saved!';
    setTimeout(() => hint.textContent = '', 2000);
  });
});

async function checkConnection(url, key) {
  const statusEl = document.getElementById('status');
  const statusText = document.getElementById('statusText');
  statusEl.className = 'status checking';
  statusText.textContent = 'Checking connection...';

  try {
    const resp = await fetch(`${url}/api/roots`, {
      headers: { 'X-API-Key': key },
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const data = await resp.json();
      const projects = (data.roots || []).length;
      statusEl.className = 'status connected';
      statusText.textContent = `Connected — ${projects} project${projects !== 1 ? 's' : ''}`;
    } else {
      statusEl.className = 'status disconnected';
      statusText.textContent = resp.status === 401 ? 'Invalid API key' : `Error ${resp.status}`;
    }
  } catch (e) {
    statusEl.className = 'status disconnected';
    statusText.textContent = 'Cannot reach server';
  }
}
