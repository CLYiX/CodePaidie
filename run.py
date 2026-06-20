import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from server import app, get_config
from pathlib import Path

cfg = get_config()
for p in cfg.get("projects", []):
    for d in p.get("dirs", []):
        Path(d).mkdir(parents=True, exist_ok=True)
print(f"\n  Projects: {len(cfg.get('projects', []))}")
print(f"  UI:       http://localhost:{cfg['port']}")
print(f"  API Key:  {cfg['api_key']}\n")

import uvicorn
config = uvicorn.Config(
    app,
    host="127.0.0.1",
    port=cfg["port"],
    loop="none",
)
server = uvicorn.Server(config)
asyncio.get_event_loop().run_until_complete(server.serve())
