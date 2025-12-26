#!/bin/bash
# Test the built wheel before deployment
#
# Usage:
#   ./scripts/test_wheel.sh
#
# This script:
#   1. Creates a temporary virtual environment
#   2. Installs the built wheel
#   3. Runs basic smoke tests
#   4. Cleans up

set -e

cd "$(dirname "$0")/.."

# Check that dist/ exists and has a wheel
WHEEL=$(ls dist/*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
    echo "Error: No wheel found in dist/"
    echo "Run ./scripts/build.sh first"
    exit 1
fi

echo "=== Testing wheel: $WHEEL ==="
echo ""

# Create temp directory for test venv
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "=== Creating test virtual environment ==="
# Use poetry's Python to ensure correct version
PYTHON_PATH=$(poetry env info --executable)
"$PYTHON_PATH" -m venv "$TMPDIR/venv"
source "$TMPDIR/venv/bin/activate"

echo "=== Installing wheel ==="
pip install --quiet "$WHEEL"

echo "=== Running smoke tests ==="
echo ""

# Test 1: Import package
echo "Test 1: Import filestag"
python -c "import filestag; print(f'  ✓ Package imports (version: {filestag.__version__})')"

# Test 2: Import core classes
echo "Test 2: Import core classes"
python -c "from filestag import FileStag, FileSource, FileSink; print('  ✓ Core classes import')"

# Test 3: Test FileStag basic operations
echo "Test 3: FileStag save/load"
python -c "
from filestag import FileStag
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, 'test.txt')
    FileStag.save_text(path, 'Hello FileStag!')
    content = FileStag.load_text(path)
    assert content == 'Hello FileStag!', 'Content mismatch'
print('  ✓ save_text/load_text work')
"

# Test 4: Test JSON operations
echo "Test 4: FileStag JSON"
python -c "
from filestag import FileStag
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, 'test.json')
    data = {'name': 'FileStag', 'version': '0.1.0'}
    FileStag.save_json(path, data)
    loaded = FileStag.load_json(path)
    assert loaded == data, 'JSON mismatch'
print('  ✓ save_json/load_json work')
"

# Test 5: Test ZIP support
echo "Test 5: ZIP file support"
python -c "
from filestag import FileStag
import tempfile
import zipfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    # Create a test zip
    zip_path = os.path.join(tmpdir, 'test.zip')
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('hello.txt', 'Hello from ZIP!')

    # Read from zip:// URL
    content = FileStag.load_text(f'zip://{zip_path}/hello.txt')
    assert content == 'Hello from ZIP!', 'ZIP content mismatch'
print('  ✓ zip:// protocol works')
"

# Test 6: Test web cache import
echo "Test 6: Web cache import"
python -c "from filestag.web import WebCache; print('  ✓ WebCache imports')"

# Test 7: Test async support
echo "Test 7: Async support"
python -c "
import asyncio
from filestag import FileStag
import tempfile
import os

async def test():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'async_test.txt')
        await FileStag.save_text_async(path, 'Async works!')
        content = await FileStag.load_text_async(path)
        assert content == 'Async works!', 'Async content mismatch'

asyncio.run(test())
print('  ✓ Async operations work')
"

echo ""
echo "=== All tests passed ==="
echo ""
echo "Wheel is ready for deployment: $WHEEL"
