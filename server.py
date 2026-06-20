import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CodeF")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CONFIG_FILE = Path(__file__).parent / "config.json"
security = APIKeyHeader(name="X-API-Key", auto_error=False)

# --- Config ---

DEFAULTS = {
    "projects": [],
    "api_key": secrets.token_urlsafe(32),
    "public_url": "",
    "ngrok_user": "",
    "ngrok_pass": "",
    "allowed_extensions": [".py", ".js", ".ts", ".json", ".md", ".txt", ".yaml", ".yml"],
    "max_read_size": 10485760,
    "max_write_size": 10485760,
    "port": 8000,
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # 补全缺失字段
        for k, v in DEFAULTS.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    save_config(DEFAULTS)
    return dict(DEFAULTS)

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

def get_config():
    return load_config()

# --- Security ---

def verify_key(key: str = Depends(security)):
    cfg = get_config()
    if not key or key != cfg["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

def get_projects(cfg: dict) -> list:
    return [p for p in cfg.get("projects", []) if p.get("enabled", True)]

def safe_path(requested: str, cfg: dict):
    """解析 '项目名/路径'，返回 (绝对路径, 项目名)"""
    for p in get_projects(cfg):
        prefix = p["name"] + "/"
        if requested.startswith(prefix):
            rel = requested[len(prefix):]
            # 在项目的多个目录中查找
            for d in p.get("dirs", []):
                dir_path = Path(d).resolve()
                target = (dir_path / rel).resolve()
                if str(target).startswith(str(dir_path)) and target.exists():
                    return target, p["name"]
            # 文件不存在时，用第一个目录作为写入目标
            if p.get("dirs"):
                dir_path = Path(p["dirs"][0]).resolve()
                target = (dir_path / rel).resolve()
                if str(target).startswith(str(dir_path)):
                    return target, p["name"]
            break
    raise HTTPException(status_code=403, detail="Path not in any enabled project. Format: 项目名/路径")

def check_extension(path: Path, cfg: dict):
    exts = cfg.get("allowed_extensions", [])
    if exts and path.suffix.lower() not in exts:
        raise HTTPException(status_code=403, detail=f"Extension '{path.suffix}' not allowed. Allowed: {exts}")

# --- API ---

@app.get("/api/read")
def read_file(path: str, _: str = Depends(verify_key)):
    cfg = get_config()
    target, _ = safe_path(path, cfg)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="Is a directory")
    if cfg["max_read_size"] > 0 and target.stat().st_size > cfg["max_read_size"]:
        raise HTTPException(status_code=413, detail="File too large")
    check_extension(target, cfg)
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file not supported")
    return {"path": path, "content": content}

@app.post("/api/write")
async def write_file(request: Request, _: str = Depends(verify_key)):
    cfg = get_config()
    body = await request.json()
    file_path = body.get("path", "")
    content = body.get("content", "")
    target, _ = safe_path(file_path, cfg)
    check_extension(target, cfg)
    if cfg["max_write_size"] > 0 and len(content.encode("utf-8")) > cfg["max_write_size"]:
        raise HTTPException(status_code=413, detail="Content too large")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"ok": True, "path": file_path}

@app.get("/api/list")
def list_files(path: str = ".", offset: int = 0, limit: int = 200, _: str = Depends(verify_key)):
    cfg = get_config()
    # 根目录：列出所有项目
    if path == ".":
        projects = get_projects(cfg)
        items = []
        for p in projects:
            items.append({
                "name": p["name"],
                "path": p["name"] + "/",
                "type": "dir",
                "size": None,
            })
        return {"type": "dir", "items": items, "total": len(items)}
    target, proj_name = safe_path(path, cfg)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if target.is_file():
        return {"type": "file", "name": target.name}
    all_items = []
    try:
        for item in target.iterdir():
            rel_path = proj_name + "/" + str(item.relative_to(target.parent)).replace("\\", "/")
            all_items.append({
                "name": item.name,
                "path": rel_path,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
    except PermissionError:
        pass
    # 排序：目录在前，然后按名称
    all_items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
    total = len(all_items)
    items = all_items[offset:offset + limit]
    return {"type": "dir", "items": items, "total": total, "offset": offset, "limit": limit}

@app.get("/api/delete")
def delete_file(path: str, _: str = Depends(verify_key)):
    cfg = get_config()
    target, _ = safe_path(path, cfg)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if target.is_dir():
        import shutil
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True}

@app.get("/api/copy")
def copy_file(source: str, dest: str, _: str = Depends(verify_key)):
    cfg = get_config()
    src, _ = safe_path(source, cfg)
    dst, _ = safe_path(dest, cfg)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    import shutil
    if src.is_dir():
        shutil.copytree(str(src), str(dst))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
    return {"ok": True, "from": source, "to": dest}

@app.get("/api/move")
def move_file(source: str, dest: str, _: str = Depends(verify_key)):
    cfg = get_config()
    src, _ = safe_path(source, cfg)
    dst, _ = safe_path(dest, cfg)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    import shutil
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return {"ok": True, "from": source, "to": dest}

@app.get("/api/mkdir")
def mkdir(path: str, _: str = Depends(verify_key)):
    cfg = get_config()
    target, _ = safe_path(path, cfg)
    target.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": path}

@app.get("/api/info")
def file_info(path: str, _: str = Depends(verify_key)):
    cfg = get_config()
    target, _ = safe_path(path, cfg)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    stat = target.stat()
    return {
        "path": path,
        "type": "dir" if target.is_dir() else "file",
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "extension": target.suffix,
    }

@app.get("/api/search")
def search_files(query: str, path: str = ".", _: str = Depends(verify_key)):
    cfg = get_config()
    start, proj_name = safe_path(path, cfg)
    if not start.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    results = []
    for item in start.rglob("*"):
        if query.lower() in item.name.lower():
            rel = proj_name + "/" + str(item.relative_to(start.parent)).replace("\\", "/")
            results.append({"path": rel, "type": "dir" if item.is_dir() else "file"})
    return {"results": results[:100]}

@app.get("/api/grep")
def grep_content(query: str, path: str = ".", ext: str = "", _: str = Depends(verify_key)):
    cfg = get_config()
    start, proj_name = safe_path(path, cfg)
    if not start.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    results = []
    pattern = ext if ext else "*"
    for item in start.rglob(pattern):
        if not item.is_file():
            continue
        if cfg.get("max_read_size", 0) > 0 and item.stat().st_size > cfg["max_read_size"]:
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if query.lower() in line.lower():
                rel = proj_name + "/" + str(item.relative_to(start.parent)).replace("\\", "/")
                results.append({"file": rel, "line": i, "content": line.strip()[:200]})
                if len(results) >= 100:
                    return {"results": results}
    return {"results": results}

@app.get("/api/exec")
async def exec_command(command: str, _: str = Depends(verify_key)):
    import subprocess
    cfg = get_config()
    projects = get_projects(cfg)
    cwd = str(Path(projects[0]["dirs"][0]).resolve()) if projects and projects[0].get("dirs") else "."
    def _run():
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=120
            )
            return {
                "stdout": result.stdout[:10000],
                "stderr": result.stderr[:10000],
                "code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out (120s)", "code": -1}
    return await asyncio.to_thread(_run)

@app.get("/api/tree")
def tree(path: str = ".", _: str = Depends(verify_key)):
    cfg = get_config()
    if path == ".":
        projects = get_projects(cfg)
        lines = []
        for i, p in enumerate(projects):
            connector = "+-- " if i < len(projects) - 1 else "\\-- "
            lines.append(f"{connector}{p['name']}/")
        return {"tree": "\n".join(lines) if lines else "(no projects)"}
    target, _ = safe_path(path, cfg)
    if not target.exists() or target.is_file():
        raise HTTPException(status_code=400, detail="Not a directory")
    lines = []
    def walk(d: Path, prefix: str = ""):
        items = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items):
            connector = "+-- " if i < len(items) - 1 else "\\-- "
            lines.append(f"{prefix}{connector}{item.name}")
            if item.is_dir():
                ext = "|   " if i < len(items) - 1 else "    "
                walk(item, prefix + ext)
    walk(target)
    return {"tree": "\n".join(lines)}

# --- Project Roots (for ChatGPT to discover paths) ---

@app.get("/api/roots")
def get_roots(_: str = Depends(verify_key)):
    cfg = get_config()
    projects = get_projects(cfg)
    roots = []
    for p in projects:
        roots.append({
            "project": p["name"],
            "dirs": p.get("dirs", []),
            "hint": f"路径格式: {p['name']}/相对路径"
        })
    return {"roots": roots}

# --- Image Save (for ChatGPT DALL-E) ---

@app.post("/api/save-image")
async def save_image(request: Request, _: str = Depends(verify_key)):
    """保存 base64 图片到本地文件。body: {path: "项目名/文件名.png", image_data: "base64..."}"""
    import base64
    cfg = get_config()
    body = await request.json()
    file_path = body.get("path", "")
    image_data = body.get("image_data", "")
    if not file_path or not image_data:
        raise HTTPException(status_code=400, detail="path and image_data required")
    # 去掉 data:image/xxx;base64, 前缀
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    # 修正 base64 padding
    padding = 4 - len(image_data) % 4
    if padding != 4:
        image_data += "=" * padding
    target, _ = safe_path(file_path, cfg)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(image_data))
    return {"ok": True, "path": file_path, "size": target.stat().st_size}

@app.post("/api/upload")
async def upload_file(request: Request):
    """上传文件到项目目录。multipart/form-data: file + path"""
    from fastapi import UploadFile
    # 直接从 header 读 key
    key = request.headers.get("X-API-Key", "")
    cfg = get_config()
    if not key or key != cfg["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    form = await request.form()
    upload: UploadFile = form.get("file")
    file_path: str = form.get("path", "")
    if not upload or not file_path:
        raise HTTPException(status_code=400, detail="file and path required")
    # 自动补项目前缀
    if "/" not in file_path:
        projects = get_projects(cfg)
        if projects:
            file_path = projects[0]["name"] + "/" + file_path
    target, _ = safe_path(file_path, cfg)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = await upload.read()
    target.write_bytes(content)
    return {"ok": True, "path": file_path, "size": len(content)}

# --- Web UI ---

@app.get("/", response_class=HTMLResponse)
def ui():
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))

@app.post("/api/config")
async def update_config(request: Request):
    body = await request.json()
    cfg = get_config()
    if "allowed_extensions" in body:
        cfg["allowed_extensions"] = body["allowed_extensions"]
    if "max_read_size" in body:
        cfg["max_read_size"] = int(body["max_read_size"])
    if "max_write_size" in body:
        cfg["max_write_size"] = int(body["max_write_size"])
    if "public_url" in body:
        cfg["public_url"] = body["public_url"].strip()
    if "ngrok_user" in body:
        cfg["ngrok_user"] = body["ngrok_user"].strip()
    if "ngrok_pass" in body:
        cfg["ngrok_pass"] = body["ngrok_pass"].strip()
    if "regenerate_key" in body and body["regenerate_key"]:
        cfg["api_key"] = secrets.token_urlsafe(32)
    save_config(cfg)
    return {"ok": True, "config": {k: v for k, v in cfg.items() if k != "api_key"}}

@app.get("/api/config")
def get_config_api():
    cfg = get_config()
    return {k: v for k, v in cfg.items() if k != "api_key"}

@app.get("/api/key")
def get_key():
    cfg = get_config()
    return {"api_key": cfg["api_key"]}

# --- Directory Browser (for UI picker) ---

@app.get("/api/browse")
def browse_dirs(path: str = "C:\\", _: str = Depends(verify_key)):
    """浏览文件系统目录，用于选择沙箱路径"""
    target = Path(path).resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if target.is_file():
        return {"path": str(target), "parent": str(target.parent), "items": []}
    items = []
    try:
        for item in sorted(target.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                items.append({"name": item.name, "path": str(item), "type": "dir"})
    except PermissionError:
        pass
    parent = str(target.parent) if str(target.parent) != str(target) else ""
    return {"path": str(target), "parent": parent, "items": items}

# --- Project Management ---

@app.get("/api/sandboxes")
def list_sandboxes():
    cfg = get_config()
    projects = cfg.get("projects", [])
    connections = cfg.get("connections", [])
    return {"sandboxes": projects, "connections": connections}

@app.post("/api/sandboxes")
async def update_sandboxes(request: Request):
    body = await request.json()
    cfg = get_config()
    if "sandboxes" in body:
        cfg["projects"] = body["sandboxes"]
    if "connections" in body:
        cfg["connections"] = body["connections"]
    save_config(cfg)
    for p in cfg.get("projects", []):
        for d in p.get("dirs", []):
            Path(d).mkdir(parents=True, exist_ok=True)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    cfg = get_config()
    for p in cfg.get("projects", []):
        for d in p.get("dirs", []):
            Path(d).mkdir(parents=True, exist_ok=True)
    print(f"\n  Projects: {len(cfg.get('projects', []))}")
    print(f"  UI:       http://localhost:{cfg['port']}")
    print(f"  API Key:  {cfg['api_key']}\n")
    uvicorn.run(app, host="127.0.0.1", port=cfg["port"])
    
