#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "⚠️  Missing .env file. Copy .env.example and update paths before running."
  exit 1
fi

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
export FLASK_ENV=development

echo "🔧 Installing frontend deps (first run may take a moment)..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "🚀 Starting backend (Flask)..."
(cd "$BACKEND_DIR" && python app.py) &
BACKEND_PID=$!

cleanup() {
  echo "🛑 Shutting down backend..."
  kill "$BACKEND_PID"
}
trap cleanup EXIT

echo "🌐 Starting frontend (Vite)..."
(cd "$FRONTEND_DIR" && npm run dev)

