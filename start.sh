#!/bin/bash

# JournalFinder — Start All Services

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== Starting JournalFinder Services ==="

# Check/Activate Virtual Environment
if [ -d "$PROJECT_ROOT/venv" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/venv/bin/python"
    UVICORN_EXEC="$PROJECT_ROOT/venv/bin/uvicorn"
else
    echo "Virtual environment not found in $PROJECT_ROOT/venv."
    exit 1
fi

# 1. Start FastAPI ML Service (Port 8001)
echo "Starting ML Service on port 8001..."
$UVICORN_EXEC ml_service.main:app --host 127.0.0.1 --port 8001 &
ML_PID=$!

# 2. Start Django Backend (Port 8000)
echo "Starting Django Backend on port 8000..."
$PYTHON_EXEC backend/manage.py runserver 127.0.0.1:8000 &
DJANGO_PID=$!

# 3. Start React Frontend (Port 3000)
echo "Starting React Frontend on port 3000..."
BROWSER=none npm --prefix frontend start &
FRONTEND_PID=$!

echo ""
echo "Services started:"
echo " - ML Service:   http://localhost:8001 (PID $ML_PID)"
echo " - Django API:   http://localhost:8000 (PID $DJANGO_PID)"
echo " - Frontend UI:  http://localhost:3000 (PID $FRONTEND_PID)"
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $ML_PID $DJANGO_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
