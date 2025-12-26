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
#
# Recommended workflow:
#   ./scripts/build.sh        # Build the wheel
#   ./scripts/test_wheel.sh   # Test it locally
#   ./scripts/deploy_pypi.sh  # Deploy to PyPI

set -e

cd "$(dirname "$0")/.."

# Check that dist/ exists and has files
if [ ! -d "dist" ] || [ -z "$(ls -A dist 2>/dev/null)" ]; then
    echo "Error: No built package found in dist/"
    echo "Run ./scripts/build.sh first"
    exit 1
fi

echo "=== Testing wheel before deployment ==="
./scripts/test_wheel.sh

echo ""
echo "=== Package to deploy ==="
ls -la dist/
echo ""

if [[ "$1" == "--test" ]]; then
    echo "=== Deploying to Test PyPI ==="
    poetry config repositories.testpypi https://test.pypi.org/legacy/
    poetry publish -r testpypi
    echo ""
    echo "=== Deployed to TestPyPI ==="
    echo "Install with: pip install -i https://test.pypi.org/simple/ filestag"
else
    echo "=== Deploying to PyPI ==="
    poetry publish
    echo ""
    echo "=== Deployed to PyPI ==="
    echo "Install with: pip install filestag"
fi
