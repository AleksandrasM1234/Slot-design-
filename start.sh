#!/bin/bash

cd "$(dirname "$0")"

echo "Starting Slot Asset Generator..."
echo ""

for PORT in 8000 5173; do
  PID=$(lsof -ti :$PORT)
  if [ -n "$PID" ]; then
    echo "Port $PORT was already in use — stopping old process ($PID)..."
    kill -9 $PID
  fi
done

if [ ! -d "venv" ]; then
  echo "First run detected — setting up Python environment..."
  python3 -m venv venv
  source venv/bin/activate
  python3 -m pip install --upgrade pip
  python3 -m pip install -r requirements.txt
else
  source venv/bin/activate
fi

if [ ! -d "frontend/node_modules" ]; then
  echo "First run detected — installing frontend dependencies..."
  (cd frontend && npm install)
fi

if [ ! -f ".env" ]; then
  echo ""
  echo "WARNING: No .env file found. Create one with your API keys before generating anything:"
  echo "  LEONARDO_API_KEY=your_key_here"
  echo "  GROQ_API_KEY=your_key_here"
  echo ""
fi

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