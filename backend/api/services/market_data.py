import ccxt
import pandas as pd
import ta
import asyncio

def calculate_trend_for_tf(df: pd.DataFrame):
    if len(df) < 50:
        return "Neutral"
    
    ema20 = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator().iloc[-1]
    rsi = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
    
    if ema20 > ema50 and rsi > 50:
        return "Bullish"
    elif ema20 < ema50 and rsi < 50:
        return "Bearish"
    else:
        return "Neutral"

def fetch_single_timeframe(symbol, timeframe):
    try:
        # New instance per thread to avoid session conflicts
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        trend = calculate_trend_for_tf(df)
        return timeframe, trend, df
    except Exception as e:
        print(f"Error fetching {timeframe}: {e}")
        return timeframe, "Neutral", pd.DataFrame()

async def fetch_mtf_data(symbol: str = "BTC/USDT"):
    """
    Asynchronously fetches 6 timeframes and computes macro alignment.
    """
    timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    exchange = ccxt.binance()
    ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
    
    tasks = [
        asyncio.to_thread(fetch_single_timeframe, symbol, tf)
        for tf in timeframes
    ]
    results = await asyncio.gather(*tasks)
    
    mtf_trends = {}
    primary_df = None
    
    for tf, trend, df in results:
        mtf_trends[tf] = trend
        if tf == '1h':
            primary_df = df
            
    if primary_df is None or primary_df.empty:
        primary_df = results[0][2]

    # Primary Indicators for AI
    primary_df['rsi'] = ta.momentum.RSIIndicator(close=primary_df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=primary_df['close'])
    primary_df['macd'] = macd.macd()
    primary_df['macd_signal'] = macd.macd_signal()
    primary_df['ema_20'] = ta.trend.EMAIndicator(close=primary_df['close'], window=20).ema_indicator()
    primary_df['ema_50'] = ta.trend.EMAIndicator(close=primary_df['close'], window=50).ema_indicator()
    bb = ta.volatility.BollingerBands(close=primary_df['close'], window=20, window_dev=2)
    primary_df['bb_high'] = bb.bollinger_hband()
    primary_df['bb_low'] = bb.bollinger_lband()
    primary_df['bb_mavg'] = bb.bollinger_mavg()
    primary_df['bbw'] = ((primary_df['bb_high'] - primary_df['bb_low']) / primary_df['bb_mavg']) * 100
    
    latest_bbw = primary_df['bbw'].iloc[-1]
    if latest_bbw < 1.5:
        volatility_state = "Squeeze"
    elif latest_bbw < 3.5:
        volatility_state = "Normal"
    elif latest_bbw < 6.0:
        volatility_state = "Expansion"
    else:
        volatility_state = "Extreme"
        
    primary_df['atr'] = ta.volatility.AverageTrueRange(high=primary_df['high'], low=primary_df['low'], close=primary_df['close'], window=14).average_true_range()
    
    latest = primary_df.iloc[-1]
    
    return {
        "symbol": symbol,
        "last_price": ticker['last'],
        "change_percentage": ticker['percentage'],
        "mtf_trends": mtf_trends,
        "volatility_state": volatility_state,
        "indicators": {
            "rsi": round(latest['rsi'], 2) if not pd.isna(latest['rsi']) else 50,
            "macd": round(latest['macd'], 2) if not pd.isna(latest['macd']) else 0,
            "macd_signal": round(latest['macd_signal'], 2) if not pd.isna(latest['macd_signal']) else 0,
            "ema_20": round(latest['ema_20'], 2) if not pd.isna(latest['ema_20']) else ticker['last'],
            "ema_50": round(latest['ema_50'], 2) if not pd.isna(latest['ema_50']) else ticker['last'],
            "bb_high": round(latest['bb_high'], 2) if not pd.isna(latest['bb_high']) else ticker['last'] * 1.05,
            "bb_low": round(latest['bb_low'], 2) if not pd.isna(latest['bb_low']) else ticker['last'] * 0.95,
            "bbw": round(latest_bbw, 2) if not pd.isna(latest_bbw) else 0,
            "atr": round(latest['atr'], 2) if not pd.isna(latest['atr']) else 100
        }
    }
