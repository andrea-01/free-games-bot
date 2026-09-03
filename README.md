# 🎮 Free Games Telegram Bot

A Telegram bot that monitors and alerts you about 100% free PC game giveaways across major stores including **Epic Games Store, Steam, GOG, Ubisoft Connect, EA / Origin, Itch.io, and IndieGala**.

---

## ✨ Features

- 🖼 **High-Resolution Game Cover**: Direct from SteamGridDB (600x900 poster grids) or official store key assets.
- 💰 **Stock Price & Discount**: Displays original regular price (e.g. `<s>$19.99</s> ➔ FREE (100% OFF)`).
- 🏷 **Rich Metadata**:
  - Release Year (e.g. `2016`)
  - Genre Tags (e.g. `Adventure, Indie, Sci-Fi`)
  - Player Modes (`👤 Single-player`, `👥 Multi-player`, `🤝 Co-op`)
  - Expiry / Offer End Date
  - Brief description
- 🚀 **1-Click Claim**: Interactive Telegram button directly opening the store page.
- 🔔 **Automated Background Alerts**: Automatically notifies all subscribed users whenever a new free game is detected (runs every hour, customizable).
- ⏳ **Upcoming Deals**: Teasers for upcoming Epic Games giveaways so you never miss what's coming next week.

---

## 🛠 Commands

| Command | Description |
|---|---|
| `/start` | Starts the bot and automatically subscribes you to deal notifications |
| `/free` or `/deals` | Fetches and displays all active 100% free PC games right now |
| `/settings` | Toggle which stores you want to receive alerts from (Epic, Steam, GOG, etc.) |
| `/epic` | Shows current and upcoming free games on Epic Games Store |
| `/steam` | Shows free promotions on Steam |
| `/check` | Checks for newly released games matching your store preferences |
| `/subscribe` | Enables automated background deal alerts |
| `/unsubscribe` | Disables automated alerts (you can still use `/free` anytime) |
| `/help` | Displays command list and instructions |

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- *(Optional)* SteamGridDB API key from [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api)

### 2. Configure Environment

Create or edit your `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
STEAMGRIDDB_API_KEY=your_steamgriddb_key_here
CHECK_INTERVAL_MINUTES=60
DATABASE_PATH=data/free_games.db
LOG_LEVEL=INFO
```

### 3. Run Locally with Python

```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Test deal fetching & formatting in the terminal without starting the bot:
python -m free_games_bot.main --test-fetch

# Launch the live Telegram bot:
python -m free_games_bot.main
```

### 4. Run with Docker Compose

```bash
docker compose up -d
```

To view logs:
```bash
docker compose logs -f
```

---

## 🏠 Deploying on CasaOS Homeserver

CasaOS is powered by Docker under the hood. You can deploy this bot in under 2 minutes:

### Option A: Via CasaOS Web UI ("Custom Install")
1. Open your CasaOS dashboard.
2. In the top right corner of the apps grid, click **`+`** (Install a customized app) ➔ **"Install a customized app"**.
3. In the top-right corner of the popup modal, click the **import icon** (`import` / `Compose`).
4. Paste the following CasaOS-ready Compose configuration:
   ```yaml
   name: free-games-bot
   services:
     bot:
       image: ghcr.io/andrea-01/free-games-bot:latest
       container_name: free-games-bot
       restart: unless-stopped
       environment:
         - TELEGRAM_BOT_TOKEN=your_token_here
         - STEAMGRIDDB_API_KEY=your_sgdb_key_here
         - CHECK_INTERVAL_MINUTES=60
         - DATABASE_PATH=/app/data/free_games.db
         - LOG_LEVEL=INFO
       volumes:
         - /DATA/AppData/free-games-bot:/app/data
   ```
5. Click **Submit** and click **Install**.

### Option B: Via Terminal / SSH on CasaOS (Recommended)
1. SSH into your CasaOS server or open CasaOS Terminal:
   ```bash
   git clone https://github.com/your-username/free-games-bot.git /DATA/AppData/free-games-bot-app
   cd /DATA/AppData/free-games-bot-app
   ```
2. Create and edit your `.env` file with your credentials:
   ```bash
   cp .env.example .env
   nano .env
   ```
3. Start the bot with Docker Compose:
   ```bash
   docker compose up -d --build
   ```
4. CasaOS will automatically detect the container and display it on your CasaOS Web Dashboard! You can click the container icon to view live logs, CPU usage, and restart it anytime.

---

## 🧪 Testing

Run the automated test suite:
```bash
pytest -v
```
