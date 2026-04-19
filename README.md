# Crypto Scalp Arena 🤖📈

**Multi-Strategy Crypto Scalping Trading Arena with Paper Trading, AI Optimization, and Real-time Telegram Reporting**

## Overview

Crypto Scalp Arena adalah sistem bot trading otomatis yang mensimulasikan paper trading dengan modal $1000 USD di live market crypto spot. Sistem ini menjalankan multiple strategi scalping secara bersamaan dalam sebuah "arena", di mana setiap strategi berkompetisi untuk menghasilkan profit terbaik.

### Fitur Utama

- **Paper Trading Engine**: Simulasi trading dengan $1000 modal tanpa uang nyata
- **Multi-Strategi Arena**: 6+ strategi scalping berjalan bersamaan (EMA, RSI, MACD, Bollinger Bands, Price Action, Alpha Signals)
- **Live Market Data**: Real-time OHLCV data dari Binance/Coinbase via CCXT
- **AI Optimizer**: Self-learning system untuk parameter tuning otomatis
- **Performance Tracking**: Winrate, Profit Factor, Sharpe Ratio, Max Drawdown
- **Telegram Integration**: Real-time trade alerts dan daily performance reports
- **Web Dashboard**: Real-time monitoring dengan React + WebSocket
- **Risk Management**: Position sizing, stop loss, max drawdown limits

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (untuk dashboard)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/crypto-scalp-arena.git
cd crypto-scalp-arena

# Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -e ".[dev]"

# Setup environment variables
cp .env.example .env
# Edit .env dengan konfigurasi Anda

# Setup database
python scripts/init_db.py

# Install frontend dependencies
cd frontend
npm install
```

### Running the System

**Terminal 1 - Data Feed Service:**
```bash
python -m services.data_feed
```

**Terminal 2 - Arena Bot Manager:**
```bash
python -m services.arena_manager
```

**Terminal 3 - API Server:**
```bash
python -m services.api_server
```

**Terminal 4 - Telegram Bot:**
```bash
python -m services.telegram_service
```

**Terminal 5 - Frontend Dashboard:**
```bash
cd frontend
npm start
```

Akses dashboard di `http://localhost:3000`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LIVE MARKET DATA                         │
│                  (Binance/Coinbase)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │    Data Feed Service           │
        │  (CCXT + WebSocket Stream)     │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   Message Broker (Redis)       │
        │   - OHLCV stream               │
        │   - Ticker stream              │
        └────────┬───────────────────────┘
                 │
        ┌────────┴─────────┬──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────┐      ┌────────┐         ┌──────────┐
    │ Bot 1  │      │ Bot 2  │  ...    │ Bot N    │
    │ (EMA)  │      │ (RSI)  │         │ (MACD)   │
    └────┬───┘      └────┬───┘         └──────┬───┘
         │               │                    │
         └───────────────┼────────────────────┘
                         │
                    ┌────▼────────┐
                    │ Arena Manager│
                    │ - Tracking   │
                    │ - Metrics    │
                    └────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐    ┌──────────┐    ┌─────────────┐
    │Database│    │Telegram  │    │Dashboard API│
    │        │    │Bot       │    │(WebSocket)  │
    └────────┘    └──────────┘    └─────────────┘
                                        │
                                        ▼
                                   ┌──────────┐
                                   │Dashboard │
                                   │(React)   │
                                   └──────────┘
```

## Strategi Scalping yang Diimplementasikan

| Strategi | Deskripsi | Indikator | Timeframe |
|----------|-----------|-----------|-----------|
| **EMA Crossover** | Fast EMA cross Slow EMA | EMA(9), EMA(26) | 5m |
| **RSI Oversold** | Buy saat RSI < 30, Sell saat RSI > 70 | RSI(14) | 5m |
| **Bollinger Bands** | Buy di lower band, Sell di upper band | BB(20,2) | 5m |
| **MACD** | MACD line cross Signal line | MACD(12,26,9) | 5m |
| **Price Action** | Support/Resistance breakout | Manual levels | 5m |
| **Alpha Signals** | Composite indicator dari multiple signals | EMA+RSI+BB | 5m |

## Configuration

### Trading Parameters

Edit `.env` untuk mengkonfigurasi:

```env
INITIAL_CASH=1000                          # Modal awal simulasi
RISK_PER_TRADE=0.02                        # Risk 2% per trade
MAX_DRAWDOWN_PERCENT=15                    # Max drawdown limit
TRADING_SYMBOLS=BTC/USDT,ETH/USDT,...     # Symbols untuk trading
TIMEFRAME=5m                               # Timeframe analisis
```

### Strategy Parameters

Setiap strategi memiliki parameter yang dapat dikonfigurasi di `config/strategies.json`:

```json
{
  "ema_crossover": {
    "fast_period": 9,
    "slow_period": 26,
    "min_volume": 100000
  },
  "rsi_oversold": {
    "period": 14,
    "oversold_threshold": 30,
    "overbought_threshold": 70
  }
}
```

## API Endpoints

### Trading API

- `GET /api/portfolio` - Get current portfolio state
- `GET /api/trades` - Get trade history
- `POST /api/trades` - Execute manual trade
- `GET /api/strategies` - Get all strategies performance
- `GET /api/strategies/{id}/performance` - Get specific strategy performance

### WebSocket Endpoints

- `ws://localhost:8000/ws/portfolio` - Real-time portfolio updates
- `ws://localhost:8000/ws/trades` - Real-time trade stream
- `ws://localhost:8000/ws/market` - Real-time market data

## Telegram Integration

### Commands

- `/start` - Start receiving notifications
- `/status` - Get current portfolio status
- `/strategies` - Get strategies performance
- `/stop` - Stop receiving notifications
- `/help` - Get help

### Notifications

Bot akan mengirim notifikasi untuk:
- ✅ Trade execution (entry dan exit)
- ⚠️ Risk warnings (approaching max drawdown)
- 📊 Daily performance reports
- 🔴 Critical alerts (bot crash, connection error)

## Performance Metrics

Sistem melacak dan melaporkan:

- **Winrate**: Persentase winning trades
- **Profit Factor**: Gross profit / Gross loss
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Largest peak-to-trough decline
- **Average Trade Duration**: Rata-rata durasi trade
- **Return on Investment (ROI)**: Total return %

## Database Schema

### Tables

- `strategies` - Strategy definitions
- `trades` - All executed trades
- `portfolio_snapshots` - Periodic portfolio states
- `performance_metrics` - Calculated metrics
- `market_data` - Historical OHLCV data

## Logging

Semua aktivitas dicatat di `logs/trading.log`:

```
[2026-04-20 10:30:45] INFO - Data feed started
[2026-04-20 10:30:46] INFO - Bot 1 (EMA Crossover) started
[2026-04-20 10:31:02] INFO - BUY signal from EMA Crossover: BTC/USDT @ $45,230
[2026-04-20 10:31:45] INFO - SELL signal from EMA Crossover: BTC/USDT @ $45,280 | Profit: $50 (+0.11%)
```

## Development

### Running Tests

```bash
pytest tests/ -v --cov=src
```

### Code Style

```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Adding New Strategies

1. Create new strategy class di `src/strategies/`
2. Inherit dari `BaseStrategy`
3. Implement `analyze()` method
4. Register di `src/strategies/__init__.py`
5. Add configuration di `config/strategies.json`

Contoh:

```python
from src.strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, symbol: str, params: dict):
        super().__init__(symbol, params)
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: dict) -> dict:
        # Your analysis logic here
        return {'action': 'BUY', 'confidence': 0.85}
```

## Backtesting

Jalankan backtest untuk validasi strategi:

```bash
python scripts/backtest.py --strategy ema_crossover --symbol BTC/USDT --start 2024-01-01 --end 2026-04-20
```

## Deployment

### Docker

```bash
docker-compose up -d
```

### Cloud Deployment (Google Cloud Run)

```bash
gcloud run deploy crypto-scalp-arena \
  --source . \
  --platform managed \
  --region us-central1
```

## Troubleshooting

### Bot not executing trades

1. Check data feed service: `curl http://localhost:8000/api/health`
2. Check Redis connection: `redis-cli ping`
3. Check database connection: `psql -U user -d crypto_scalp_arena -c "SELECT 1"`
4. Check logs: `tail -f logs/trading.log`

### High slippage

- Reduce `RISK_PER_TRADE` untuk smaller position sizes
- Increase `min_volume` threshold di strategy config
- Use limit orders instead of market orders

### Memory leak

- Check bot process memory: `ps aux | grep python`
- Restart services: `docker-compose restart`
- Check for unclosed database connections

## Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Disclaimer

**This is a paper trading simulator for educational purposes only.** It does not execute real trades or use real money. The strategies and performance metrics are simulated based on historical market data and may not reflect actual trading results. Always conduct thorough backtesting and risk assessment before deploying any trading strategy with real capital.

## Support

For issues, questions, or suggestions:

- 📧 Email: support@cryptoscalp.local
- 💬 Telegram: @cryptoscalp_support
- 🐛 GitHub Issues: [Report Issue](https://github.com/yourusername/crypto-scalp-arena/issues)

## Roadmap

- [ ] Live trading mode (with real money)
- [ ] Advanced AI optimizer (reinforcement learning)
- [ ] Multi-exchange support
- [ ] Mobile app
- [ ] Advanced charting tools
- [ ] Community strategy marketplace
- [ ] Automated strategy backtesting pipeline

---

**Happy Trading! 🚀**
