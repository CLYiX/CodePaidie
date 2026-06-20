# CodeF

> **Kill The Paid AI Coding Agent**

Turn ChatGPT, Gemini, Kimi, or any AI with custom tool support into a free local coding environment. Read, write, search, and execute files on your machine — no Codex, no MCP, no extra fees.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Author: IMFF BIAS**

## Why This Exists

Codex quota is limited. MCP requires Business/Enterprise. DevSpace ([Waishnav/devspace](https://github.com/Waishnav/devspace)) needs MCP.

**Works with ChatGPT, Gemini, Kimi, and any AI that supports custom tool calling.** No special subscription, no extra protocol — just a REST API. Uses official platform features, not browser hacks, so **no ban risk**.

Best suited for platforms where web quota is separate from coding quota (e.g. ChatGPT Plus, Gemini). Not beneficial for platforms where quotas are shared (e.g. Claude).

| | CodeF | Codex | DevSpace |
|--|:--:|:--:|:--:|
| **Platform support** | Any with tool calling | OpenAI only | ChatGPT (MCP) |
| **Subscription** | Any tier | Pro / API | Business/Enterprise |
| **Protocol** | REST API | Native | MCP |
| **Setup** | Low | None | Medium |
| **Ban risk** | None (official API) | N/A | Possible |
| **DALL-E image save** | Yes | No | No |
| **Multi-project** | Yes | No | Yes |
| **Web UI** | Yes | No | No |

## Architecture

```
ChatGPT (Web / Mobile)
        |  HTTPS (X-API-Key header)
    ngrok tunnel
        |
    FastAPI (localhost:8000)
        |  path resolution + auth
    Local filesystem (project isolation)
```

## Quick Start

### 1. Install

```bash
git clone https://github.com/IMFF-BIAS/CodeF.git
cd CodeF
pip install -r requirements.txt
```

### 2. Run

```bash
# Option A: One-click (Windows)
start.bat

# Option B: Manual
python run.py
```

Server starts at `http://localhost:8000`. API key is printed in console.

### 3. Setup ngrok

```bash
# First time only
setup.bat

# Then start tunnel
ngrok http 8000
```

Copy the `https://xxx.ngrok-free.app` URL.

### 4. Configure ChatGPT

1. Open ChatGPT → Create a GPT → **Configure** → **Actions**
2. Paste the OpenAPI schema (from Web UI → "OpenAPI" tab, or see `openapi.json`)
3. Authentication: **API Key** → **Custom** → Header name: `X-API-Key`
4. Paste your API key
5. Save → Test in the GPT

## Path Format

All file operations use `project_name/relative_path`:

```
myproject/src/main.py       → Read src/main.py in "myproject"
myproject/                  → List project root
.                           → List all projects
```

Call `/api/roots` first to discover available projects.

## System Prompt for ChatGPT

Paste this at the start of a new conversation:

```
你是本地文件桥接工具。所有文件操作使用「项目名/相对路径」格式。
第一步：调 /api/roots 查看可用项目和目录。
第二步：用返回的 project 名作为路径前缀。
示例：读取 C:\Users\me\project\src\main.py → 路径填 myproject/src/main.py
注意：
- 不要用 Windows 绝对路径，用「项目名/相对路径」
- 写文件用 POST /api/write，不要用 exec + python -c
- 创建目录用 /api/mkdir，不要问用户
- 出错了自己换方案重试，不要让用户排查
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/roots` | GET | Discover available projects |
| `/api/read?path=` | GET | Read file |
| `/api/write` | POST | Write file (body: `{path, content}`) |
| `/api/list?path=` | GET | List directory (supports `offset`, `limit`) |
| `/api/tree?path=` | GET | Directory tree |
| `/api/delete?path=` | GET | Delete file/directory |
| `/api/copy?source=&dest=` | GET | Copy |
| `/api/move?source=&dest=` | GET | Move/rename |
| `/api/mkdir?path=` | GET | Create directory |
| `/api/info?path=` | GET | File info |
| `/api/search?query=&path=` | GET | Search by filename |
| `/api/grep?query=&path=` | GET | Search file contents |
| `/api/exec?command=` | GET | Execute shell command |
| `/api/save-image` | POST | Save base64 image (body: `{path, image_data}`) |
| `/api/upload` | POST | Upload file (multipart: `file` + `path`) |
| `/api/browse?path=` | GET | Browse filesystem (Web UI) |

## DALL-E Image Workflow

1. ChatGPT generates an image (returns base64)
2. Call `POST /api/save-image` with `{path: "myproject/output/image.png", image_data: "base64..."}`
3. Image saved locally

## Web UI

Open `http://localhost:8000` for:

- **File Browser** — Navigate projects, drag-and-drop upload
- **Project Management** — Add/remove projects and directories
- **Settings** — API key, extensions, size limits
- **OpenAPI Schema** — Copy-paste for Custom GPT setup

## Security

- **Project isolation** — Each project is sandboxed, no cross-project access
- **API key auth** — Random 32-char token, 401 on missing/invalid key
- **Extension whitelist** — Optionally restrict file types (empty = allow all)
- **Size limits** — Configurable read/write limits (0 = unlimited)
- **Path traversal protection** — `safe_path()` validates paths stay within project dirs

## Project Structure

```
CodeF/
  server.py           # FastAPI backend
  run.py              # Entry point
  start.bat           # One-click start (server + ngrok)
  setup.bat           # First-time ngrok install
  config.json         # Runtime config (auto-generated, gitignored)
  config.example.json # Config template
  requirements.txt    # Python dependencies
  openapi.json        # OpenAPI schema backup
  static/
    index.html        # Web UI
```

## Development History

### v1 — Basic API
FastAPI + single sandbox directory, no UI, manual config editing.

### v2 — Web UI + Tunnel
Chinese Web UI, ngrok integration, OpenAPI schema for Custom GPT.

### v3 — Multi-project Isolation
Project-based model: each project has a name, multiple directories, enable/disable toggle. Path format: `project_name/relative_path`.

### v4 — Security
Extension whitelist, size limits, path traversal protection, removed ngrok basic auth (incompatible with Custom GPT).

### v5 — Full API + Image Save
All file operations, DALL-E image save, file upload with drag-and-drop, directory picker UI.

## FAQ

**Q: Will this get my account banned?**
A: No. This uses Custom GPT Actions — an officially supported OpenAI feature. It's the same mechanism as "ask ChatGPT to check the weather" or "look up stocks", just pointing to your own server. No browser automation, no script injection, no ToS violation.

**Q: Why not use MCP?**
A: MCP support in ChatGPT requires Business/Enterprise/Edu subscriptions. DevSpace needs MCP. This project works with any Plus account — the most common tier.

**Q: Which AI platforms are supported?**
A: Any platform that supports custom tool calling / actions / function calling. Tested and confirmed:
- **ChatGPT** — Custom GPT Actions (Plus or higher)
- **Gemini** — Function calling
- **Kimi** — Custom tools
- Any Chinese/ international platform with tool support (通义, 文心, DeepSeek, etc.)

If the platform lets you define external APIs for the AI to call, it works with CodeF.

**Q: Are there platforms where this doesn't help?**
A: Yes. Claude shares web and code quotas, so there's no advantage. Platforms with unlimited or separate coding quotas benefit most.

## License

MIT
