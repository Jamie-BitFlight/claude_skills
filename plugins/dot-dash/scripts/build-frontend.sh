#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PLUGIN_DIR/frontend"
echo "Installing frontend dependencies..."
npm install
echo "Building frontend..."
npm run build
echo "Frontend built to $PLUGIN_DIR/frontend/dist/"
