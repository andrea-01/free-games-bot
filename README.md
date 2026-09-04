# 🎮 Game Deals Telegram Bot

Un bot Telegram avanzato per monitorare e ricevere notifiche istantanee sui giochi PC 100% gratuiti e sulle migliori offerte digitali da **Epic Games Store, Steam, GOG, Ubisoft Connect, EA / Origin, Itch.io e IndieGala**.

---

## ✨ Funzionalità

- 🖼 **Locandine ad Alta Risoluzione**: Poster verticali (600x900) recuperati da SteamGridDB o direttamente dagli store ufficiali.
- 💰 **Prezzi e Sconti Ufficiali in Euro (€)**: Visualizzazione chiara del prezzo di listino e dell'offerta corrente (es. `<s>19,99 €</s> ➔ GRATIS (100% di sconto)` o `<s>39,99 €</s> ➔ 4,99 € (-88%)`).
- 🇮🇹 **Link Diretti agli Store in Italiano**: Ogni scheda contiene il pulsante diretto per aprire la pagina del negozio in lingua italiana.
- 🏷 **Metadati di Gioco Completi**:
  - Anno di rilascio
  - Generi e categorie (Azione, Avventura, GDR, Strategia, Horror, ecc.)
  - Modalità supportate (`👤 Giocatore singolo`, `👥 Multigiocatore`, `🤝 Co-op`)
  - Recensioni e Valutazioni reali (es. `⭐ 85% positive (12.400 recensioni)`)
  - Data di scadenza dell'offerta
  - Descrizione e sinossi del gioco
- 🚀 **Riscatto con 1-Click**: Pulsante interattivo sotto ogni scheda per riscattare subito il titolo.
- ⚙️ **Pannello Filtri Interattivo (/settings)**:
  - **📢 Notifiche & Recap**: Stato iscrizione chiaramente visibile con toggle rapido 1-click (`[🔔 Notifiche: ATTIVE]` / `[🔕 Notifiche: DISATTIVATE]`).
  - **🏬 Store**: Abilita o disabilita singoli negozi.
  - **🏷️ Categorie**: Filtra in base ai generi di tuo interesse.
  - **💰 Prezzi & Soglie**: Imposta una soglia di listino minimo e un prezzo massimo per le offerte scontate.
  - **🎁 Toggle Listino per Giochi Gratis**: Opzione dedicata per non escludere mai i giochi al 100% gratuiti anche quando imposti un listino minimo sulle offerte a pagamento.
  - **⭐ Filtro Qualità / Anti-Spam**: Elimina shovelware e spam al 99% di sconto richiedendo un punteggio minimo di recensioni positive (≥ 70% o ≥ 80%) e recensori verificati da Steam e CheapShark.
- 🌙 **Recap Serale delle 20:00 (Ora Italiana)**: Ogni sera alle ore 20:00 gli utenti iscritti ricevono un messaggio di riepilogo compatto con tutte le offerte attive pertinenti ai loro interessi, suddiviso in *Giochi Gratuiti* e *Migliori Offerte Scontate* (massimo 2 righe a gioco, con icone di genere, rating e link diretto per il riscatto).
- 🔔 **Notifiche Automatiche Periodiche**: Controllo orario in background con avvisi istantanei sui nuovi giochi gratis.

---

## 🛠 Comandi Disponibili

| Comando | Descrizione |
|---|---|
| `/start` | Avvia il bot, mostra il messaggio di benvenuto e iscrive alle notifiche |
| `/free` | Mostra **solo i titoli 100% gratuiti** secondo i tuoi filtri |
| `/deals` | Mostra **tutte le offerte** (giochi gratis + sconti) secondo i tuoi filtri |
| `/recap` | Mostra il **riepilogo serale compatto** delle offerte attive pertinenti |
| `/nofilter_free` (o `/nofilter-free`) | Mostra **tutti i giochi gratuiti disponibili senza alcun filtro** |
| `/nofilter_recap` (o `/nofilter-recap`) | Mostra il **recap compatto di TUTTE le offerte attive senza alcun filtro** |
| `/settings` | Pannello interattivo per gestire Notifiche, Store, Categorie, Prezzi e Filtro Qualità |
| `/minprice [€]` | Imposta rapidamente il listino minimo (es. `/minprice 10` o `/minprice 0`) |
| `/maxprice [€]` | Imposta il prezzo max per offerte a pagamento (es. `/maxprice 5` o `/maxprice 0`) |
| `/epic` | Mostra promozioni attive e anticipazioni future di Epic Games Store |
| `/steam` | Mostra promozioni e giveaway attivi su Steam |
| `/check` | Cerca subito nuovi giochi non ancora ricevuti |
| `/subscribe` | Attiva le notifiche automatiche e il recap serale |
| `/unsubscribe` | Disattiva le notifiche automatiche e il recap serale |
| `/help` | Mostra la guida completa dei comandi |

---

## 🚀 Guida Rapida all'Avvio

### 1. Requisiti
- Python 3.10+
- Token Bot Telegram ottenuto da [@BotFather](https://t.me/BotFather)
- *(Opzionale)* Chiave API di [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api) per poster ad alta risoluzione

### 2. Configurazione dell'Ambiente

Crea o modifica il file `.env` nella radice del progetto:
```env
TELEGRAM_BOT_TOKEN=il_tuo_token_botfather
STEAMGRIDDB_API_KEY=la_tua_chiave_steamgriddb
CHECK_INTERVAL_MINUTES=60
DATABASE_PATH=data/free_games.db
LOG_LEVEL=INFO
```

### 3. Esecuzione Locale con Python

```bash
# Crea l'ambiente virtuale e installa le dipendenze
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Testa il recupero e la formattazione delle offerte nel terminale:
python -m free_games_bot.main --test-fetch

# Avvia il bot Telegram:
python -m free_games_bot.main
```

### 4. Esecuzione con Docker Compose

```bash
docker compose up -d
```

Per visualizzare i log:
```bash
docker compose logs -f
```

---

## 🏠 Installazione su Server CasaOS (Web UI)

CasaOS supporta l'installazione diretta di applicazioni personalizzate tramite Docker Compose dall'interfaccia grafica:

### Passaggi di Installazione tramite Web UI:
1. Apri la dashboard del tuo server **CasaOS**.
2. In alto a destra nella griglia delle applicazioni, clicca sul pulsante **`+`** ➔ **"Install a customized app"** (Installa un'app personalizzata).
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
      icon: https://github.com/andrea-01/free-games-bot/blob/main/assets/casaos_icon.png?raw=true
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
  icon: https://github.com/andrea-01/free-games-bot/blob/main/assets/casaos_icon.png?raw=true
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

## 🧪 Test Automatizzati

Per eseguire l'intera suite di test:
```bash
pytest -v
```
