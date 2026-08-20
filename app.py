
import os
from flask import Flask, render_template, jsonify, request
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

TOP_50_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", 
    "LINKUSDT", "SUIUSDT", "NEARUSDT", "APTUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT", "BCHUSDT", 
    "ATOMUSDT", "FTMUSDT", "INJUSDT", "RENDERUSDT", "TIAUSDT", "SEIUSDT", "FETUSDT", "ARBUSDT", 
    "PEPEUSDT", "SHIBUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "GALAUSDT", "SANDUSDT", "MANAUSDT", 
    "OPUSDT", "LDOUSDT", "STXUSDT", "ICPUSDT", "FILUSDT", "ORDIUSDT", "AAVEUSDT", "CRVUSDT", 
    "RUNEUSDT", "THETAUSDT", "ALGOUSDT", "EGLDUSDT", "FLOWUSDT", "AXSUSDT", "DYDXUSDT", "KASUSDT", 
    "NOTUSDT", "JUPUSDT"
]

def fetch_klines(symbol, interval, limit=60):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        if isinstance(data, dict) and 'code' in data:
            return None
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except:
        return None

def analyze_single_coin(symbol, interval='1h', df_btc=None):
    df = fetch_klines(symbol, interval, limit=60)
    if df is None or len(df) < 30:
        return None

    recent_high = df['high'].iloc[-21:-1].max()
    recent_low = df['low'].iloc[-21:-1].min()
    current_close = df['close'].iloc[-1]
    
    avg_vol = df['volume'].iloc[-21:-1].mean()
    curr_vol = df['volume'].iloc[-1]
    vol_confirmed = curr_vol > (avg_vol * 1.15)

    btc_bullish = df_btc['close'].iloc[-1] > df_btc['close'].iloc[-10].mean() if df_btc is not None else True
    btc_bearish = df_btc['close'].iloc[-1] < df_btc['close'].iloc[-10].mean() if df_btc is not None else True

    signal_type = "NEUTRAL"
    if (current_close > recent_high) and vol_confirmed and btc_bullish:
        signal_type = "STRONG BUY (BREAKOUT)"
    elif (current_close < recent_low) and vol_confirmed and btc_bearish:
        signal_type = "STRONG SELL (BREAKOUT)"

    sl = round(current_close * 0.975, 4) if "BUY" in signal_type else round(current_close * 1.025, 4)
    tp = round(current_close * 1.040, 4) if "BUY" in signal_type else round(current_close * 0.960, 4)

    return {
        'symbol': symbol,
        'price': current_close,
        'signal': signal_type,
        'suggested_sl': sl,
        'suggested_tp': tp,
        'volume_ratio': round(curr_vol / avg_vol, 2)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan_all')
def scan_all():
    interval = request.args.get('interval', '1h')
    df_btc = fetch_klines('BTCUSDT', interval, limit=30)
    
    active_signals = []
    for symbol in TOP_50_COINS:
        res = analyze_single_coin(symbol, interval, df_btc)
        if res and res['signal'] != "NEUTRAL":
            active_signals.append(res)
            
    return jsonify({
        'total_scanned': len(TOP_50_COINS),
        'signals_found': len(active_signals),
        'results': active_signals
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
