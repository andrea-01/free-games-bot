# 🎮 Free Games Telegram Bot

A Telegram bot that monitors and alerts you about 100% free PC game giveaways across major stores including **Epic Games Store, Steam, GOG, Ubisoft Connect, EA / Origin, Itch.io, and IndieGala**.

---

## ✨ Caratteristiche / Features

- 🖼 **Locandine ad alta risoluzione**: Da SteamGridDB (poster verticali 600x900) o store ufficiali.
- 💰 **Prezzi in Euro (€)**: Visualizzazione del prezzo di listino e dell'eventuale sconto (es. `<s>19,99 €</s> ➔ GRATIS (100% di sconto)`).
- 🇮🇹 **Pagine Store Italiane**: Link diretti alle pagine in lingua italiana degli store ufficiali.
- 🏷 **Metadati Completi**:
  - Anno di rilascio (es. `2024`)
  - Categorie e generi (es. `Avventura, Indie, GDR`)
  - Modalità (`👤 Giocatore singolo`, `👥 Multigiocatore`, `🤝 Co-op`)
  - Recensioni e Valutazione (es. `⭐ 85% positive (12.400 recensioni)`)
  - Scadenza / Termine dell'offerta
  - Descrizione del gioco
- 🚀 **Riscatto con 1-Click**: Pulsante interattivo Telegram che apre direttamente la pagina dello store.
- ⚙️ **Filtri Personalizzati & Anti-Spam (/settings)**:
  - **🏬 Store**: Abilita o disabilita singoli store (Epic, Steam, GOG, ecc.)
  - **🏷️ Categorie**: Filtra per generi preferiti (Azione, GDR, Strategia, ecc.)
  - **💰 Prezzi & Soglie**: Imposta un listino minimo, un prezzo massimo scontato, e un toggle dedicato per mantenere sempre visibili i giochi gratis al 100%!
  - **⭐ Filtro Qualità / Anti-Spam**: Elimina shovelware e spam al 99% di sconto richiedendo un punteggio minimo (es. ≥ 70% o ≥ 80% positive) e recensori minimi da Steam / CheapShark.
- 🔔 **Avvisi Automatici Periodici**: Notifica automatica oraria di nuovi giochi disponibili per tutti gli iscritti.

---

## 🛠 Comandi / Commands

| Comando | Descrizione |
|---|---|
| `/start` | Avvia il bot e iscrive automaticamente agli avvisi |
| `/free` | Mostra **solo i giochi 100% gratuiti** secondo i tuoi filtri |
| `/deals` | Mostra **tutte le offerte** (giochi gratis + sconti) secondo i tuoi filtri |
| `/nofilter-free` | Mostra **tutti i giochi gratuiti disponibili senza alcun filtro** |
| `/settings` | Menu interattivo: Store, Categorie, Prezzi, Toggle Gratis e Filtro Qualità |
| `/minprice [€]` | Imposta il valore minimo del gioco (es. `/minprice 10` o `/minprice 0`) |
| `/maxprice [€]` | Imposta prezzo max per offerte a pagamento (es. `/maxprice 5` o `/maxprice 0`) |
| `/epic` | Mostra promozioni attive e future di Epic Games Store |
| `/steam` | Mostra promozioni e giveaway Steam |
| `/check` | Controlla nuovi arrivi non ancora ricevuti |
| `/subscribe` | Attiva le notifiche automatiche periodiche |
| `/unsubscribe` | Disattiva le notifiche automatiche |
| `/help` | Guida completa ai comandi |

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
