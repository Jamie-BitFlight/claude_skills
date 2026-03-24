#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
PORT="${DOT_DASH_PORT:-7765}"
cd "$PLUGIN_DIR/server"
if [ ! -d "node_modules" ]; then
    echo "Installing server dependencies..."
    npm install
fi
if [ ! -f "dist/main.js" ]; then
    echo "Building server..."
    npm run build
fi
echo "Starting dot-dash server on port $PORT..."
node dist/main.js
