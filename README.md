# -Crypto-momentum-bot
Extremely rare news + volatility momentum trading bot (RSI/MACD/ADX)

# 🚀 Stringent Momentum Trading Bot

Super rare, high-conviction bot that only trades on **fresh news + CPI + high volatility** confirmed by **RSI + MACD + ADX**.

Designed to sit quiet for days and only fire when everything lines up perfectly.

### Features
- NewsAPI trigger (last 30 minutes only)
- ADX > 30 + ATR volatility spike
- MACD crossover + RSI momentum confirmation
- 1% risk per trade, ATR-based SL/TP
- 4-hour cooldown between trades
- Works on Binance Futures (SOL/USDT, BTC/USDT, etc.)

### How to run
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill your keys
3. `python momentum_bot.py`

**Warning**: Test on Binance testnet first!

Made for quick momentum plays only.
