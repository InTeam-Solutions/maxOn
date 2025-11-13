#!/bin/sh
set -e

# Get port from environment or use default
PORT=${PORT:-8001}

echo "Starting uvicorn on port $PORT"

# Run uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
