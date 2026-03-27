import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# ========================= CONFIG =========================
SYMBOL = 'SOL/USDT'          # Change to BTC/USDT or whatever you trade
TIMEFRAME = '5m'
LEVERAGE = 10
RISK_PERCENT = 1.0           # 1% risk per trade
COOLDOWN_HOURS = 4

# API keys
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'options': {'defaultType': 'future'},   # perpetual futures
    'enableRateLimit': True,
})

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
# ========================================================

exchange.set_leverage(LEVERAGE, SYMBOL)

last_trade_time = datetime.now() - timedelta(hours=COOLDOWN_HOURS)

def fetch_ohlcv():
    bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=200)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def get_fresh_news_sentiment():
    """Only considers news from last 30 minutes — this is the 'quick momentum' trigger"""
    url = f"https://newsapi.org/v2/everything?q={SYMBOL.split('/')[0]} OR CPI&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10).json()
        if 'articles' not in resp or not resp['articles']:
            return 'neutral'

        now = datetime.utcnow()
        positive_words = ['beat', 'surprise', 'higher', 'rise', 'bullish', 'surge', 'positive', 'strong', 'rally']
        negative_words = ['miss', 'lower', 'decline', 'bearish', 'drop', 'negative', 'weak', 'fall']

        score = 0
        recent_articles = 0

        for article in resp['articles']:
            pub_time = datetime.strptime(article['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
            if now - pub_time > timedelta(minutes=30):
                continue  # only fresh news

            recent_articles += 1
            text = (article['title'] + " " + article.get('description', "")).lower()
            pos = sum(1 for w in positive_words if w in text)
            neg = sum(1 for w in negative_words if w in text)
            score += pos - neg

        if recent_articles == 0:
            return 'neutral'
        if score >= 3:
            return 'positive'
        if score <= -3:
            return 'negative'
        return 'neutral'
    except:
        return 'neutral'

def calculate_indicators(df):
    df['rsi'] = ta.rsi(df['close'], length=14)
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    df['adx'] = adx['ADX_14']
    macd = ta.macd(df['close'])
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    return df

def get_current_position():
    positions = exchange.fetch_positions([SYMBOL])
    for pos in positions:
        if float(pos['contracts']) != 0:
            return 'long' if float(pos['contracts']) > 0 else 'short'
    return None

def close_position():
    position = get_current_position()
    if position:
        side = 'sell' if position == 'long' else 'buy'
        exchange.create_market_order(SYMBOL, side, abs(float(positions[0]['contracts'])))
        print(f"[{datetime.now()}] Closed {position} position")

def enter_trade(side):
    global last_trade_time
    close_position()  # flat before new trade

    df = fetch_ohlcv()
    latest = df.iloc[-1]
    atr = latest['atr']

    balance = float(exchange.fetch_balance()['USDT']['free'])
    risk_amount = balance * (RISK_PERCENT / 100)
    stop_distance = atr * 1.5
    amount = (risk_amount / stop_distance) * LEVERAGE   # position size

    # Safety cap
    amount = min(amount, balance * LEVERAGE * 0.05)

    order = exchange.create_market_order(SYMBOL, side, amount)
    print(f"[{datetime.now()}] 🔥 ENTERED {side.upper()} | Size: {amount:.4f} | News + Technicals aligned")

    # Set SL/TP (ATR based)
    if side == 'buy':
        sl_price = latest['close'] - stop_distance * 1.2
        tp_price = latest['close'] + stop_distance * 2.4
    else:
        sl_price = latest['close'] + stop_distance * 1.2
        tp_price = latest['close'] - stop_distance * 2.4

    # You can replace with proper stop/take orders via exchange.create_order() if preferred
    last_trade_time = datetime.now()

def main():
    print(f"🚀 Stringent Momentum Bot started for {SYMBOL} | Only trades on fresh news + RSI/MACD/ADX + volatility")
    print("Extremely rare & high-conviction only...\n")

    while True:
        try:
            now = datetime.now()
            if now - last_trade_time < timedelta(hours=COOLDOWN_HOURS):
                time.sleep(60)
                continue

            df = fetch_ohlcv()
            df = calculate_indicators(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            sentiment = get_fresh_news_sentiment()

            # High volatility filter
            high_vol = (latest['adx'] > 30) and (latest['atr'] > 1.5 * df['atr'].mean())

            # MACD momentum
            macd_bull_cross = (prev['macd'] < prev['macd_signal']) and (latest['macd'] > latest['macd_signal']) and (latest['macd_hist'] > 0)
            macd_bear_cross = (prev['macd'] > prev['macd_signal']) and (latest['macd'] < latest['macd_signal']) and (latest['macd_hist'] < 0)

            # RSI momentum (sweet spot)
            rsi_bull = (45 < latest['rsi'] < 65) and (latest['rsi'] > prev['rsi'])
            rsi_bear = (35 < latest['rsi'] < 55) and (latest['rsi'] < prev['rsi'])

            # === TRADE LOGIC (only if news is the catalyst) ===
            if sentiment == 'positive' and high_vol and macd_bull_cross and rsi_bull:
                enter_trade('buy')
            elif sentiment == 'negative' and high_vol and macd_bear_cross and rsi_bear:
                enter_trade('sell')

            # Status every 60 seconds
            print(f"[{now.strftime('%H:%M:%S')}] Status: {sentiment.upper()} news | ADX:{latest['adx']:.1f} | RSI:{latest['rsi']:.1f} | Vol: {'HIGH' if high_vol else 'low'}")

            time.sleep(60)  # check every minute

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
