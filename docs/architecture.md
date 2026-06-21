# Architecture

## Overview

```
 Phones (browsers)                  Laptop (browser + server)
 ─────────────────                  ─────────────────────────────────────────
 /mobile                ──WS──▶  FastAPI  ──WS──▶  / (hub dashboard)
   DeviceMotion API               /ws/mobile        /ws/laptop
   DeviceOrientation              /ws/laptop
   Shows: player ID               /qr.png
          unique bg color         /api/status
          tilt motion             /api/players
```

## Design Principles

- **`/mobile` is experience-agnostic.** Phones connect once, get assigned a player ID (P1, P2…), display it full-screen with a unique color, and stream tilt motion continuously. They are unaware of which experience is running.
- **`/` (index) is the connection hub.** It shows a live per-player dashboard with tilt visualisers, sensor data and Hz counters. Phones stay connected here while users navigate to experiences.
- **Experiences are independent.** Each experience declares its own slot config (Slot 1 = your brush, Slot 2 = opponent…), lets the user assign connected devices to those slots, and then uses `phoneState[slotId]` for input routing.

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| FastAPI server | `src/main.py` | Serves HTML, WS relay, player ID assignment, QR, REST API |
| Hub dashboard | `src/static/index.html` | Live per-player cards: tilt ball, sensor values, Hz counter |
| Mobile controller | `src/static/mobile.html` | Assigns player ID, shows full-screen colored ID, streams tilt |
| Experiences list | `src/static/experiences.html` | Game catalogue |
| Battle Painter | `src/static/exp_battle_painter.html` | Tilt-based painting game with slot-based device assignment |
| Marble Maze | `src/static/exp_marble.html` | Tilt-based marble maze |

## Player ID System

The server maintains a free-list of player numbers (`P1`, `P2`, …).

1. Phone connects to `/ws/mobile` → server assigns the next available ID.
2. Server sends `{"type":"assigned","playerId":"P1"}` to that phone.
3. Server broadcasts `{"type":"status","newPlayer":"P1","players":["P1",…]}` to all laptop connections.
4. On disconnect, the ID is returned to the free-list and `{"type":"status","leftPlayer":"P1"}` is broadcast.

When a laptop page opens its WS, it immediately receives a full `players` roster snapshot so late-joining pages (e.g., opening an experience after phones are connected) always see the current state.

## Data Flow

### Phone → Server → Laptop

```
Phone (30 fps)
  → WS /ws/mobile
  → server injects playerId
  → broadcast to all /ws/laptop connections
```

Motion frame (sent every ~33 ms):
```json
{
  "type": "motion",
  "playerId": "P1",
  "acceleration":  { "x": float, "y": float, "z": float },
  "rotationRate":  { "alpha": float, "beta": float, "gamma": float },
  "orientation":   { "alpha": float, "beta": float, "gamma": float }
}
```

Tilt mapping used by experiences:
```
tiltX = clamp(orientation.gamma / 45, -1, 1)   // left/right
tiltY = clamp(orientation.beta  / 45, -1, 1)   // forward/back
```

## Experience Slot Pattern

Each experience maintains:

```javascript
const cfg = {
  slot1: 'keyboard',   // 'keyboard' | playerId  — controls player brush
  slot2: 'ai:normal',  // 'none' | 'ai:easy' | 'ai:normal' | 'ai:hard' | playerId
};

const phoneState = {};  // { 'P1': { tiltX, tiltY }, 'P2': { tiltX, tiltY }, … }
```

Lobby shows two slot rows, dynamically populated from `connectedPlayers`. User assigns any connected device to any slot. When a phone disconnects mid-session, its slot automatically resets.

## REST API

| Endpoint | Response |
|----------|----------|
| `GET /api/status` | `{ laptop_connections, mobile_connections, local_ip }` |
| `GET /api/players` | `{ players: ["P1", "P2", …] }` |
| `GET /qr.png` | QR code PNG encoding `https://<LAN-IP>:8000/mobile` |

## Security Note

Motion sensor APIs require a secure context (`https://`). The project uses a self-signed TLS certificate. Users must accept the browser warning once on first visit.

