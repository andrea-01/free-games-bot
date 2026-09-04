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

## 🏠 Deploying on CasaOS Homeserver (Web UI)

CasaOS supporta l'installazione diretta di applicazioni personalizzate tramite Docker Compose dall'interfaccia grafica:

### Passaggi di Installazione tramite Web UI:
1. Apri la dashboard del tuo server **CasaOS**.
2. In alto a destra nella griglia delle app, clicca sul pulsante **`+`** ➔ **"Install a customized app"** (Installa un'app personalizzata).
3. Nell'angolo in alto a destra della finestra modale, clicca sull'icona di importazione **"Import"** (icona con freccia/foglio).
4. Incolla la seguente configurazione Compose:

```yaml
name: free-games-bot
services:
  bot:
    cpu_shares: 90
    command: []
    container_name: free-games-bot
    deploy:
      resources:
        limits:
          memory: 512M
    environment:
      - CHECK_INTERVAL_MINUTES=60
      - DATABASE_PATH=/app/data/free_games.db
      - LOG_LEVEL=INFO
      - STEAMGRIDDB_API_KEY=your_steamgriddb_api_key
      - TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    hostname: free-games-bot
    image: ghcr.io/andrea-01/free-games-bot:latest
    labels:
      icon: https://github.com/andrea-01/free-games-bot/blob/main/assets/bot_avatar.jpg?raw=true
    restart: unless-stopped
    volumes:
      - type: bind
        source: /DATA/AppData/free-games-bot/data
        target: /app/data
    ports: []
    devices: []
    cap_add: []
    network_mode: bridge
    privileged: false
x-casaos:
  author: self
  category: self
  hostname: ""
  icon: https://github.com/andrea-01/free-games-bot/blob/main/assets/bot_avatar.jpg?raw=true
  index: /
  is_uncontrolled: false
  port_map: ""
  scheme: http
  store_app_id: free-games-bot
  title:
    custom: Game Deals Bot
    en_us: bot
```

5. Sostituisci i valori di `TELEGRAM_BOT_TOKEN` e `STEAMGRIDDB_API_KEY` con i tuoi token reali.
6. Clicca su **Submit** e poi su **Install**.
7. L'applicazione comparirà nella dashboard con la propria icona personalizzata. Puoi visualizzare i log in tempo reale o riavviare/ricostruire il container facendo clic sui tre puntini dell'app ➔ **Settings / Rebuild**.

---

## 🧪 Testing

Esegui la suite di test automatizzati:
```bash
pytest -v
```
