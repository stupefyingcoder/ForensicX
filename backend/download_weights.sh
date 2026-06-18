#!/usr/bin/env bash
set -e

WEIGHTS_DIR="$(cd "$(dirname "$0")" && pwd)/weights"
mkdir -p "$WEIGHTS_DIR"

echo "Downloading Real-ESRGAN x4plus weights (~67MB)..."
curl -L -o "$WEIGHTS_DIR/RealESRGAN_x4plus.pth" \
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

echo "Done. Weights saved to $WEIGHTS_DIR/RealESRGAN_x4plus.pth"
