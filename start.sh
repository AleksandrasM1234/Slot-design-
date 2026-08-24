#!/bin/bash

cd "$(dirname "$0")"

echo "Starting Slot Asset Generator..."
echo ""

if [ ! -d "venv" ]; then
  echo "Error: venv not found. Run this once first:"
  echo "  python3 -m venv venv"
  echo "  source venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

source venv/bin/activate

echo "Starting backend..."
python3 -m uvicorn asset_pipeline.api.main:app --reload &
BACKEND_PID=$!

sleep 2

echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Both servers are running."
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both."

trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait