#!/bin/bash
cd "$(dirname "$0")" || exit 1

# Activate the virtual environment
source venv/bin/activate

# Run uvicorn server
uvicorn backend.main:app --reload --host 0.0.0.0
