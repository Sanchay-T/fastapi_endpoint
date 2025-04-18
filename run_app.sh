#!/usr/bin/env bash
# Run FastAPI backend with correct module path
# Usage: ./run_app.sh

set -e

# Determine script directory (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "env/bin/activate" ]; then
    source "env/bin/activate"
else
    echo "Virtual environment not found at env/. Please create it first." >&2
    exit 1
fi

# Run the FastAPI application as a module so package imports work
exec python -m backend.main 