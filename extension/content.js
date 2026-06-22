// CodePaidie Extension — Content Script
// Injected into AI chat pages. Detects platforms, injects prompt, observes tool calls.

(() => {
  'use strict';

  // --- Config ---
  const TOOL_TAG = '<tool_call>';
  const TOOL_TAG_END = '</tool_call>';
  const RESULT_TAG = '<tool_result>';
  const RESULT_TAG_END = '</tool_result>';

  const SYSTEM_PROMPT = `You have access to local file operations via tools. When you need to read, write, search, or manage files, output a tool call in this exact format:

<tool_call>
{"name": "tool_name", "args": {"param": "value"}}
</tool_call>

Available tools:
- read_file: Read file. Args: {path}
- write_file: Write file. Args: {path, content}
- list_files: List directory. Args: {path}
- tree: Directory tree. Args: {path}
- search_files: Search by name. Args: {query, path}
- grep_content: Search file contents. Args: {query, path, ext}
- delete_file: Delete file/directory. Args: {path}
- create_dir: Create directory. Args: {path}
- file_info: Get file info. Args: {path}
- exec_command: Execute shell command. Args: {command}
- get_roots: List available projects. Args: {}

Path format: project_name/relative_path. Example: default/src/main.py
Call get_roots first to discover available projects.

Rules:
- Output ONLY the <tool_call> tag when you need file access
- Do NOT explain the call before making it
- Wait for the tool result before continuing
- If a tool call fails, try a different approach`;

  // --- Platform Detection ---
  const PLATFORMS = {
    'chatgpt.com': {
      name: 'ChatGPT',
      getInput: () => document.querySelector('#prompt-textarea'),
      getResponseContainer: (el) => el.closest('[data-message-author-role="assistant"]') || el.parentElement,
      submitInput: (input) => {
        // ChatGPT: trigger Enter key or click send button
        const btn = document.querySelector('button[data-testid="send-button"]');
        if (btn) btn.click();
        else input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      },
      insertText: (input, text) => {
        input.innerText = text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      },
    },
    'gemini.google.com': {
      name: 'Gemini',
      getInput: () => document.querySelector('.ql-editor, [contenteditable="true"]'),
      getResponseContainer: (el) => el.closest('.model-response-text, .response-content') || el.parentElement,
      submitInput: (input) => {
        const btn = document.querySelector('button.send-button, [aria-label="Send message"]');
        if (btn) btn.click();
        else input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      },
      insertText: (input, text) => {
        input.innerText = text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      },
    },
    'kimi.moonshot.cn': {
      name: 'Kimi',
      getInput: () => document.querySelector('[contenteditable="true"]'),
      getResponseContainer: (el) => el.closest('.message-content, .chat-message') || el.parentElement,
      submitInput: (input) => {
        const btn = document.querySelector('button[class*="send"], [data-testid="send-button"]');
        if (btn) btn.click();
        else input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      },
      insertText: (input, text) => {
        input.innerText = text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      },
    },
    'tongyi.aliyun.com': {
      name: '通义',
      getInput: () => document.querySelector('textarea, [contenteditable="true"]'),
      getResponseContainer: (el) => el.closest('.message-content, .chat-message') || el.parentElement,
      submitInput: (input) => {
        const btn = document.querySelector('button[class*="send"]');
        if (btn) btn.click();
        else input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      },
      insertText: (input, text) => {
        if (input.tagName === 'TEXTAREA') { input.value = text; input.dispatchEvent(new Event('input', { bubbles: true })); }
        else { input.innerText = text; input.dispatchEvent(new Event('input', { bubbles: true })); }
      },
    },
    'yiyan.baidu.com': {
      name: '文心',
      getInput: () => document.querySelector('textarea, [contenteditable="true"]'),
      getResponseContainer: (el) => el.closest('.message-content, .chat-message') || el.parentElement,
      submitInput: (input) => {
        const btn = document.querySelector('button[class*="send"]');
        if (btn) btn.click();
        else input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      },
      insertText: (input, text) => {
        if (input.tagName === 'TEXTAREA') { input.value = text; input.dispatchEvent(new Event('input', { bubbles: true })); }
        else { input.innerText = text; input.dispatchEvent(new Event('input', { bubbles: true })); }
      },
    },
    'chat.deepseek.com': {
      name: 'DeepSeek',
      getInput: () => document.querySelector('textarea'),
      getResponseContainer: (el) => el.closest('.message-content, .chat-message') || el.parentElement,
      submitInput: (input) => {
        const btn = document.querySelector('button[class*="send"], [aria-label="Send"]');
        if (btn) btn.click();
        else input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      },
      insertText: (input, text) => {
        input.value = text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      },
    },
  };

  function detectPlatform() {
    const host = window.location.hostname;
    for (const [domain, platform] of Object.entries(PLATFORMS)) {
      if (host.includes(domain)) return platform;
    }
    return null;
  }

  // --- State ---
  let isProcessing = false;
  let lastProcessedText = '';

  // --- Core Logic ---
  async function init() {
    const platform = detectPlatform();
    if (!platform) return;

    const config = await chrome.storage.local.get(['enabled', 'autoInject']);
    if (config.enabled === false) return;

    console.log(`[CodePaidie] Detected: ${platform.name}`);

    if (config.autoInject !== false) {
      waitForInput(platform, (input) => {
        injectPrompt(platform, input);
      });
    }

    observeResponses(platform);
  }

  function waitForInput(platform, callback, attempts = 0) {
    if (attempts > 60) return; // 30 seconds max
    const input = platform.getInput();
    if (input) {
      callback(input);
    } else {
      setTimeout(() => waitForInput(platform, callback, attempts + 1), 500);
    }
  }

  function injectPrompt(platform, input) {
    // Check if prompt already injected
    if (input.dataset.codepaidiePrompt === '1') return;
    input.dataset.codepaidiePrompt = '1';

    // For ChatGPT, we need to set the system prompt via the custom instructions
    // For other platforms, we prepend to the first message
    if (platform.name === 'ChatGPT') {
      // ChatGPT has a dedicated system prompt area; we'll prepend to user message instead
      // The user can also paste the prompt manually
    }

    console.log('[CodePaidie] System prompt ready');
  }

  function observeResponses(platform) {
    // Watch the entire page for new AI responses
    const observer = new MutationObserver((mutations) => {
      if (isProcessing) return;

      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          checkForToolCall(node, platform);
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  function checkForToolCall(node, platform) {
    const text = node.textContent || '';
    if (!text.includes(TOOL_TAG)) return;
    if (text.includes(RESULT_TAG)) return; // already processed

    const start = text.indexOf(TOOL_TAG);
    const end = text.indexOf(TOOL_TAG_END, start);
    if (end === -1) return; // tag not closed yet

    const jsonStr = text.substring(start + TOOL_TAG.length, end).trim();

    // Avoid processing same tool call twice
    if (jsonStr === lastProcessedText) return;
    lastProcessedText = jsonStr;

    try {
      const toolCall = JSON.parse(jsonStr);
      if (toolCall.name && toolCall.args !== undefined) {
        handleToolCall(toolCall, platform);
      }
    } catch (e) {
      console.warn('[CodePaidie] Failed to parse tool call:', e);
    }
  }

  async function handleToolCall(toolCall, platform) {
    isProcessing = true;
    console.log(`[CodePaidie] Tool call: ${toolCall.name}`, toolCall.args);

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'execute_tool',
        tool: toolCall.name,
        args: toolCall.args,
      });

      let resultText;
      if (response.ok) {
        resultText = JSON.stringify(response.result, null, 2);
      } else {
        resultText = JSON.stringify({ error: response.error });
      }

      // Truncate very long results
      if (resultText.length > 50000) {
        resultText = resultText.substring(0, 50000) + '\n... (truncated)';
      }

      const resultMsg = `${RESULT_TAG}\n${resultText}\n${RESULT_TAG_END}`;
      await injectResultMessage(resultMsg, platform);

    } catch (e) {
      console.error('[CodePaidie] Tool execution failed:', e);
      const errMsg = `${RESULT_TAG}\n${JSON.stringify({ error: e.message })}\n${RESULT_TAG_END}`;
      await injectResultMessage(errMsg, platform);
    }

    isProcessing = false;
  }

  async function injectResultMessage(text, platform) {
    // Wait a bit for AI to finish generating
    await new Promise(r => setTimeout(r, 1000));

    const input = platform.getInput();
    if (!input) {
      console.warn('[CodePaidie] Could not find input field');
      return;
    }

    platform.insertText(input, text);

    // Small delay then submit
    await new Promise(r => setTimeout(r, 500));
    platform.submitInput(input);
  }

  // --- Init ---
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
