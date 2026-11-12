"""Demo apps on the device, all on localhost only (nothing listens publicly).

:3000  web app          "Hello from <device> app", plus /sub/page.txt
:8000  second web app   "Hello from <device> shop"
:3001  dashboard        plain HTTP page + WebSocket echo on the same port
"""
import asyncio, http, os, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import websockets

NAME = os.environ.get("DEVICE_NAME", "device")

def web(port, title):
    root = f"/www/{port}"
    os.makedirs(f"{root}/sub", exist_ok=True)
    open(f"{root}/index.html", "w").write(f"Hello from {NAME} {title}\n")
    open(f"{root}/sub/page.txt", "w").write("deep path ok\n")
    handler = partial(SimpleHTTPRequestHandler, directory=root)
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()

async def dashboard():
    async def page(path, headers):
        if headers.get("Upgrade", "").lower() != "websocket":
            return http.HTTPStatus.OK, [], f"Hello from {NAME} dashboard\n".encode()
    async def echo(ws, path=None):
        async for msg in ws:
            await ws.send(f"{NAME} echo: {msg}")
    async with websockets.serve(echo, "127.0.0.1", 3001, process_request=page):
        await asyncio.Future()

threading.Thread(target=web, args=(3000, "app"), daemon=True).start()
threading.Thread(target=web, args=(8000, "shop"), daemon=True).start()
asyncio.run(dashboard())
