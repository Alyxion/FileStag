#!/bin/bash
# Build the package for distribution
#
# Usage:
#   ./scripts/build.sh          # Just build the wheel
#   ./scripts/build.sh --full   # Rebuild README first, then build

set -e

cd "$(dirname "$0")/.."

# Check for --full flag
if [[ "$1" == "--full" ]]; then
    echo "=== Rebuilding README files ==="
    poetry run python scripts/build_readme.py
    echo ""
fi

echo "=== Cleaning previous builds ==="
rm -rf dist/ build/ *.egg-info

echo "=== Building package ==="
poetry build

echo ""
echo "=== Build complete ==="
ls -la dist/
