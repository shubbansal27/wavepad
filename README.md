# Mobile Motion Controller

A FastAPI app that turns your phone's browser into a real-time motion controller — no native app needed.

## How it works

1. Run the server on your laptop.
2. Open `http://localhost:8000` on your laptop browser — you'll see a QR code.
3. Scan the QR code with your phone (same WiFi). Your phone opens `/mobile` in its browser.
4. Tap **Start Sending Motion** on the phone.
5. The laptop dashboard shows live accelerometer, rotation-rate, and orientation data streamed over WebSocket.

## Quick start

```bash
./start.sh
```

Then open **http://localhost:8000** in your laptop browser.

## Requirements

Python 3.10+ · packages in `requirement.txt`

## iOS note

Safari on iOS 13+ requires the user to tap a button before motion permission is granted — the mobile page handles this automatically.

## Project structure

```
src/
  main.py              FastAPI app (HTTP + WebSocket)
  static/
    index.html         Laptop dashboard
    mobile.html        Mobile controller page
requirement.txt
start.sh
```
