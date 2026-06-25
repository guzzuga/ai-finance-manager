# ZYNEFINANCE - Backend & Telegram Bot

Personal finance manager dengan AI parser dan Telegram bot.

## Quick Start (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/guzzuga/ai-finance-manager/main/setup.sh | bash
```

## Manual Setup

### 1. Clone & Install
```bash
git clone https://github.com/guzzuga/ai-finance-manager.git
cd ai-finance-manager/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env  # or create .env manually
nano .env
```

Required environment variables:
```
DATABASE_URL=sqlite:///./data/finance.db
TELEGRAM_BOT_TOKEN=your_bot_token
MIMO_API_KEY=your_bluesminds_api_key
MIMO_BASE_URL=https://api.bluesminds.com/v1
MIMO_MODEL=glm-4.6
```

### 3. Initialize Database
```bash
mkdir -p data
python3 -c "from app.database.database import engine, Base; from app.models import models; Base.metadata.create_all(bind=engine)"
```

### 4. Run
```bash
# API Server (port 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Telegram Bot
python -m app.bot.telegram_polling
```

## Systemd Services (Production)

After running `setup.sh`, services are auto-created:
```bash
sudo systemctl start zynefinance-api
sudo systemctl start zynefinance-bot
sudo systemctl enable zynefinance-api zynefinance-bot
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Login |
| `/api/transactions` | GET/POST | Transactions CRUD |
| `/api/categories` | GET | Categories |
| `/api/reports/summary` | GET | Financial summary |
| `/api/reports/monthly` | GET | Monthly report |
| `/api/reports/daily` | GET | Daily report |
| `/api/export/csv` | GET | Export CSV |
| `/api/export/excel` | GET | Export Excel |

## Tech Stack
- Python 3.10+
- FastAPI
- SQLAlchemy + SQLite
- BluesMinds AI (glm-4.6)
- Telegram Bot API
