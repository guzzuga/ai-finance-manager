#!/bin/bash
# ============================================
# ZYNEFINANCE - Backend & Bot Setup Script
# ============================================
# Usage: bash setup.sh
# Requirements: Python 3.10+, pip, git

set -e

echo "=========================================="
echo "  ZYNEFINANCE - Backend Setup"
echo "=========================================="

# 1. Clone repo (skip if already exists)
if [ ! -d "$HOME/ai-finance-manager" ]; then
    echo "[1/6] Cloning repository..."
    cd ~
    git clone https://github.com/guzzuga/ai-finance-manager.git
else
    echo "[1/6] Repository already exists, pulling latest..."
    cd ~/ai-finance-manager
    git pull
fi

cd ~/ai-finance-manager/backend

# 2. Create virtual environment
echo "[2/6] Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Install dependencies
echo "[3/6] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "[4/6] Creating .env file..."
    cat > .env << 'ENVEOF'
# ============================================
# ZYNEFINANCE Configuration
# ============================================

# --- Database ---
DATABASE_URL=sqlite:///./data/finance.db

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# --- AI Service (BluesMinds) ---
MIMO_API_KEY=YOUR_API_KEY_HERE
MIMO_BASE_URL=https://api.bluesminds.com/v1
MIMO_MODEL=glm-4.6

# --- Google Sheets (Optional) ---
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}
GOOGLE_SHEETS_ID=YOUR_SHEET_ID_HERE
GOOGLE_SHEETS_ENABLED=false

# --- Server ---
API_HOST=0.0.0.0
API_PORT=8000
ENVEOF
    echo "⚠️  Edit ~/ai-finance-manager/backend/.env with your credentials!"
else
    echo "[4/6] .env already exists, skipping..."
fi

# 5. Create data directory & initialize database
echo "[5/6] Initializing database..."
mkdir -p data
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app.database.database import engine, Base
    from app.models import models
    Base.metadata.create_all(bind=engine)
    print('Database initialized successfully!')
except Exception as e:
    print(f'Database init: {e}')
"

# 6. Create systemd services (optional)
echo "[6/6] Creating systemd services..."

# Backend API service
sudo tee /etc/systemd/system/zynefinance-api.service > /dev/null << SVCEOF
[Unit]
Description=ZYNEFINANCE Backend API
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$HOME/ai-finance-manager/backend
ExecStart=$HOME/ai-finance-manager/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=$HOME/ai-finance-manager/backend/.venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
SVCEOF

# Telegram Bot service
sudo tee /etc/systemd/system/zynefinance-bot.service > /dev/null << SVCEOF
[Unit]
Description=ZYNEFINANCE Telegram Bot
After=network.target zynefinance-api.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$HOME/ai-finance-manager/backend
ExecStart=$HOME/ai-finance-manager/backend/.venv/bin/python -m app.bot.telegram_polling
Restart=always
RestartSec=5
Environment=PATH=$HOME/ai-finance-manager/backend/.venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload

echo ""
echo "=========================================="
echo "  Backend Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env:  nano ~/ai-finance-manager/backend/.env"
echo "  2. Start API:  sudo systemctl start zynefinance-api"
echo "  3. Start Bot:  sudo systemctl start zynefinance-bot"
echo "  4. Enable auto-start:"
echo "     sudo systemctl enable zynefinance-api"
echo "     sudo systemctl enable zynefinance-bot"
echo ""
echo "Check status:"
echo "  sudo systemctl status zynefinance-api"
echo "  sudo systemctl status zynefinance-bot"
echo ""
