// CodePaidie Extension — Background Service Worker
// Handles API calls to CodePaidie server

const TOOL_MAP = {
  read_file:    { method: 'GET',  endpoint: '/api/read' },
  write_file:   { method: 'POST', endpoint: '/api/write' },
  list_files:   { method: 'GET',  endpoint: '/api/list' },
  tree:         { method: 'GET',  endpoint: '/api/tree' },
  search_files: { method: 'GET',  endpoint: '/api/search' },
  grep_content: { method: 'GET',  endpoint: '/api/grep' },
  delete_file:  { method: 'GET',  endpoint: '/api/delete' },
  create_dir:   { method: 'GET',  endpoint: '/api/mkdir' },
  file_info:    { method: 'GET',  endpoint: '/api/info' },
  exec_command: { method: 'GET',  endpoint: '/api/exec' },
  get_roots:    { method: 'GET',  endpoint: '/api/roots' },
  save_image:   { method: 'POST', endpoint: '/api/save-image' },
};

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'execute_tool') {
    executeTool(msg.tool, msg.args)
      .then(result => sendResponse({ ok: true, result }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true; // async response
  }
});

async function executeTool(toolName, args) {
  const config = await chrome.storage.local.get(['serverUrl', 'apiKey']);
  const serverUrl = config.serverUrl || 'http://127.0.0.1:8000';
  const apiKey = config.apiKey || '';

  const mapping = TOOL_MAP[toolName];
  if (!mapping) {
    throw new Error(`Unknown tool: ${toolName}. Available: ${Object.keys(TOOL_MAP).join(', ')}`);
  }

  const url = new URL(serverUrl + mapping.endpoint);

  let options = {
    method: mapping.method,
    headers: { 'X-API-Key': apiKey },
  };

  if (mapping.method === 'GET') {
    // Append args as query params
    for (const [k, v] of Object.entries(args || {})) {
      if (v !== undefined && v !== null) {
        url.searchParams.set(k, typeof v === 'string' ? v : JSON.stringify(v));
      }
    }
  } else {
    // POST with JSON body
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(args || {});
  }

  const resp = await fetch(url.toString(), options);
  const data = await resp.json();

  if (!resp.ok) {
    throw new Error(data.detail || `API error ${resp.status}`);
  }

  return data;
}
