#!/bin/bash
# Deploy to PyPI
#
# Usage:
#   ./scripts/deploy_pypi.sh          # Deploy to PyPI
#   ./scripts/deploy_pypi.sh --test   # Deploy to Test PyPI first
#
# Prerequisites:
#   - poetry config pypi-token.pypi <your-token>
#   - For test: poetry config repositories.testpypi https://test.pypi.org/legacy/
#   - For test: poetry config pypi-token.testpypi <your-test-token>

set -e

cd "$(dirname "$0")/.."

echo "=== Building package (with README rebuild) ==="
./scripts/build.sh --full

if [[ "$1" == "--test" ]]; then
    echo ""
    echo "=== Deploying to Test PyPI ==="
    poetry publish -r testpypi
    echo ""
    echo "Test package available at: https://test.pypi.org/project/filestag/"
else
    echo ""
    echo "=== Deploying to PyPI ==="
    poetry publish
    echo ""
    echo "Package available at: https://pypi.org/project/filestag/"
fi
