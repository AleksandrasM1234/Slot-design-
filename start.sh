#!/bin/bash

cd "$(dirname "$0")"

echo "Starting Slot Asset Generator..."
echo ""

OS_TYPE="$(uname -s)"

install_on_linux() {
  if command -v apt-get &> /dev/null; then
    echo "Installing missing dependencies via apt..."
    sudo apt-get update -qq
    if ! command -v python3.12 &> /dev/null; then
      sudo apt-get install -y software-properties-common
      sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
      sudo apt-get update -qq
      sudo apt-get install -y python3.12 python3.12-venv python3-pip
    fi
    if ! command -v node &> /dev/null; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null
      sudo apt-get install -y nodejs
    fi
    if ! command -v lsof &> /dev/null; then
      sudo apt-get install -y lsof
    fi
  else
    echo "Warning: no apt-get found. Install Python 3.12, Node.js, and lsof manually before continuing."
  fi
}

install_on_mac() {
  if ! command -v brew &> /dev/null; then
    echo "Homebrew not found — installing it first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
  fi
  if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 not found — installing via Homebrew..."
    brew install python@3.12
  fi
  if ! command -v node &> /dev/null; then
    echo "Node.js not found — installing via Homebrew..."
    brew install node
  fi
}

if [ "$OS_TYPE" = "Darwin" ]; then
  install_on_mac
elif [ "$OS_TYPE" = "Linux" ]; then
  install_on_linux
else
  echo "Unsupported OS ($OS_TYPE). Install Python 3.12 and Node.js manually, then re-run this script."
fi

PYTHON_BIN=$(command -v python3.12 || command -v python3)

echo ""

for PORT in 8000 5173; do
  if command -v lsof &> /dev/null; then
    PID=$(lsof -ti :$PORT)
    if [ -n "$PID" ]; then
      echo "Port $PORT was already in use — stopping old process ($PID)..."
      kill -9 $PID
    fi
  fi
done

if [ ! -d "venv" ]; then
  echo "First run detected — setting up Python environment..."
  "$PYTHON_BIN" -m venv venv
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
  echo "WARNING: No .env file found. Ask the project owner for one and place it in this folder."
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