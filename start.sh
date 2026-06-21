#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirement.txt

# Generate a self-signed TLS cert using Python (avoids macOS LibreSSL -addext issue)
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
  echo "Generating self-signed TLS certificate..."
  python src/gen_cert.py
fi

echo ""
echo "Starting server -> https://localhost:8000"
echo "Open https://localhost:8000 in your laptop browser."
echo ""
echo "NOTE: Browser will show a certificate warning - click Advanced -> Proceed."
echo ""
uvicorn src.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload
