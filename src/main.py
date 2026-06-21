import io
import json
import socket
from pathlib import Path
from typing import Set

import netifaces
import qrcode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Mobile Motion Controller")

laptop_connections: Set[WebSocket] = set()
mobile_connections: Set[WebSocket] = set()

# Player ID assignment
mobile_players: dict[WebSocket, str] = {}   # ws → "P1", "P2", …
_next_player_num: int = 1
_free_player_nums: list[int] = []


def _assign_player_id() -> str:
    global _next_player_num
    if _free_player_nums:
        _free_player_nums.sort()
        n = _free_player_nums.pop(0)
    else:
        n = _next_player_num
        _next_player_num += 1
    return f"P{n}"


def _release_player_id(pid: str) -> None:
    try:
        _free_player_nums.append(int(pid[1:]))
    except (ValueError, IndexError):
        pass

def get_local_ip() -> str:
    """Return the en0 (WiFi) IPv4 address, falling back to UDP-probe if unavailable."""
    try:
        addrs = netifaces.ifaddresses("en0")
        return addrs[netifaces.AF_INET][0]["addr"]
    except (KeyError, ValueError, OSError):
        pass
    # Fallback: pick the interface that routes to the internet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

@app.get("/", response_class=HTMLResponse)
async def laptop_ui():
    return (BASE_DIR / "static" / "index.html").read_text()

@app.get("/mobile", response_class=HTMLResponse)
async def mobile_ui():
    return (BASE_DIR / "static" / "mobile.html").read_text()

@app.get("/experiences", response_class=HTMLResponse)
async def experiences_ui():
    return (BASE_DIR / "static" / "experiences.html").read_text()

@app.get("/exp/battle-painter", response_class=HTMLResponse)
async def exp_battle_painter():
    return (BASE_DIR / "static" / "exp_battle_painter.html").read_text()

@app.get("/sounds/{filename}")
async def serve_sound(filename: str):
    path = BASE_DIR / "static" / "sounds" / filename
    if not path.exists() or not path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    suffix = path.suffix.lower()
    media_types = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav"}
    return Response(content=path.read_bytes(), media_type=media_types.get(suffix, "application/octet-stream"))

@app.get("/exp/tilt-snake", response_class=HTMLResponse)
async def exp_tilt_snake():
    return (BASE_DIR / "static" / "exp_tilt_snake.html").read_text()

@app.get("/qr.png")
async def generate_qr():
    local_ip = get_local_ip()
    url = f"https://{local_ip}:8000/mobile"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")

@app.get("/api/status")
async def status():
    return {
        "laptop_connections": len(laptop_connections),
        "mobile_connections": len(mobile_connections),
        "local_ip": get_local_ip(),
    }

@app.get("/api/players")
async def players():
    return {"players": sorted(mobile_players.values())}

async def _broadcast(message: str, targets: Set[WebSocket]) -> None:
    dead: Set[WebSocket] = set()
    for ws in list(targets):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    targets -= dead

@app.websocket("/ws/mobile")
async def mobile_ws(websocket: WebSocket):
    await websocket.accept()
    player_id = _assign_player_id()
    mobile_players[websocket] = player_id
    mobile_connections.add(websocket)
    # Tell this phone its player ID
    await websocket.send_text(json.dumps({"type": "assigned", "playerId": player_id}))
    # Notify laptops of new connection
    await _broadcast(
        json.dumps({"type": "status", "mobiles_connected": len(mobile_connections), "newPlayer": player_id}),
        laptop_connections,
    )
    try:
        while True:
            data = await websocket.receive_text()
            # Inject playerId into every forwarded message
            try:
                msg = json.loads(data)
                msg["playerId"] = player_id
                data = json.dumps(msg)
            except (json.JSONDecodeError, TypeError):
                pass
            await _broadcast(data, laptop_connections)
    except WebSocketDisconnect:
        mobile_connections.discard(websocket)
        mobile_players.pop(websocket, None)
        _release_player_id(player_id)
        await _broadcast(
            json.dumps({"type": "status", "mobiles_connected": len(mobile_connections), "leftPlayer": player_id}),
            laptop_connections,
        )

@app.websocket("/ws/laptop")
async def laptop_ws(websocket: WebSocket):
    await websocket.accept()
    laptop_connections.add(websocket)
    # Send full current roster immediately so late-joining pages see all connected phones
    await websocket.send_text(
        json.dumps({
            "type": "status",
            "mobiles_connected": len(mobile_connections),
            "players": sorted(mobile_players.values()),
        })
    )
    try:
        while True:
            await websocket.receive_text()  # keep-alive; laptop only receives
    except WebSocketDisconnect:
        laptop_connections.discard(websocket)
