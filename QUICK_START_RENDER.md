# Quick Start: Deploy Crypto Scalp Arena di Render.com

## ✅ Status Sekarang
- Web Service (API Server): **DEPLOYED** ✅
- URL: https://crypto-scalp-arena.onrender.com

## 🚀 Langkah Berikutnya: Setup Database & Background Workers

### Step 1: Create PostgreSQL Database

1. Go to: https://dashboard.render.com/new/postgres
2. **Name**: `crypto-scalp-db`
3. **Database**: `crypto_scalp_arena`
4. **User**: `postgres`
5. **Region**: `Oregon` (same as API)
6. **Plan**: `Free`
7. Click **"Create Database"**
8. Tunggu sampai status berubah menjadi "Available" (2-3 menit)
9. **Copy Internal Database URL** (format: `postgresql://user:password@host/dbname`)

### Step 2: Create Redis Cache

1. Go to: https://dashboard.render.com/new/redis
2. **Name**: `crypto-scalp-redis`
3. **Region**: `Oregon`
4. **Plan**: `Free`
5. Click **"Create Redis"**
6. Tunggu sampai status "Available"
7. **Copy Internal Redis URL** (format: `redis://default:password@host:port`)

### Step 3: Add Environment Variables ke Web Service

1. Go to: https://dashboard.render.com
2. Klik service **crypto-scalp-arena**
3. Go to **Settings** → **Environment**
4. Add these variables:

```
TELEGRAM_BOT_TOKEN=8602463308:AAFyOTLZ9oNo7BtAmlk6t-W01iT8fxcbIyk
TELEGRAM_CHAT_ID=1402991511
EXCHANGE_NAME=binance
INITIAL_CASH=1000
TRADING_SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT,XRP/USDT,ADA/USDT
TIMEFRAME=5m
LOG_LEVEL=INFO
PAPER_TRADING_ENABLED=true
INITIAL_PORTFOLIO_VALUE=1000
DATABASE_URL=<paste PostgreSQL URL dari Step 1>
REDIS_URL=<paste Redis URL dari Step 2>
```

5. Click **"Save"** - Web Service akan auto-redeploy

### Step 4: Deploy Background Workers

Render Free tier hanya support 1 service per repository. Untuk deploy multiple workers, kita perlu create 3 services terpisah dengan cara manual:

#### Worker 1: Arena Manager
1. Go to: https://dashboard.render.com/new/web
2. **Name**: `crypto-scalp-arena-manager`
3. **Environment**: `Docker`
4. **Build Command**: (leave empty)
5. **Start Command**: `python -m src.services.arena_manager`
6. **Plan**: `Free`
7. Add same environment variables (copy dari Web Service)
8. Click **"Create Web Service"**

#### Worker 2: Data Feed
1. Go to: https://dashboard.render.com/new/web
2. **Name**: `crypto-scalp-data-feed`
3. **Environment**: `Docker`
4. **Start Command**: `python -m src.services.data_feed`
5. **Plan**: `Free`
6. Add same environment variables
7. Click **"Create Web Service"**

#### Worker 3: Telegram Service
1. Go to: https://dashboard.render.com/new/web
2. **Name**: `crypto-scalp-telegram`
3. **Environment**: `Docker`
4. **Start Command**: `python -m src.services.telegram_service`
5. **Plan**: `Free`
6. Add same environment variables
7. Click **"Create Web Service"**

### Step 5: Verify All Services Running

1. Go to: https://dashboard.render.com
2. Lihat semua 4 services:
   - ✅ crypto-scalp-arena (Web Service) - status "Live"
   - ✅ crypto-scalp-arena-manager (Worker) - status "Live"
   - ✅ crypto-scalp-data-feed (Worker) - status "Live"
   - ✅ crypto-scalp-telegram (Worker) - status "Live"

3. Jika ada yang "Exited" atau "Failed", klik service tersebut dan lihat logs untuk debug

### Step 6: Wait for First Report

Setelah semua services running:
- Data Feed akan mulai fetch market data dari Binance
- Arena Manager akan jalankan 6 strategi scalping
- Telegram Service akan send laporan ke Telegram Anda

**Laporan pertama akan masuk dalam 5-10 menit!** 📊

### 📊 Laporan yang Akan Anda Terima

**Real-time Trade Alerts:**
```
📈 Trade Executed
Strategy: EMA Crossover
Symbol: BTC/USDT
Side: BUY
Price: $45,230.50
Quantity: 0.001 BTC
```

**Hourly Performance Report:**
```
📊 Hourly Performance Update
Portfolio Value: $1,050.25 (+5.03%)
Total Trades: 24
Winrate: 66.67%
Profit Factor: 2.15
Top Performer: EMA Crossover (+8.2%)
```

**Daily Summary:**
```
📈 Daily Trading Summary
Portfolio Value: $1,125.50 (+12.55%)
Total Trades: 156
Winning Trades: 104 (66.67%)
Losing Trades: 52 (33.33%)
Winrate: 66.67%
Profit Factor: 2.42
Max Drawdown: -3.2%
Sharpe Ratio: 1.85
```

---

## 🔧 Troubleshooting

### Service Status "Exited"
- Click service → Logs
- Look for error messages
- Common issues:
  - Missing environment variables
  - Database connection failed
  - Redis connection failed

### No Telegram Messages
- Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
- Verify Telegram service logs
- Make sure bot is running in Telegram service

### API Not Responding
- Check https://crypto-scalp-arena.onrender.com/health
- Should return: `{"status":"healthy","timestamp":"..."}`

---

## 📞 Support

Jika ada error atau pertanyaan, check logs di Render dashboard untuk detail error message.

Good luck! 🚀
