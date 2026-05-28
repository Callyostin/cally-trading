import pandas as pd
import ta
import asyncio
from typing import Dict, Any

from api.services.binance_client import binance_client
from api.services.cache import market_cache
from api.services.task_manager import task_manager
from utils.logger import logger

def calculate_trend_for_tf(df: pd.DataFrame) -> str:
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

async def _poll_timeframe(symbol: str, timeframe: str, interval_seconds: int):
    """Background task to poll a specific timeframe and update the cache."""
    while True:
        try:
            ohlcv = await binance_client.fetch_ohlcv(symbol, timeframe, limit=100)
            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                trend = calculate_trend_for_tf(df)
                await market_cache.set_data(symbol, timeframe, df, trend)
                logger.info(f"Updated cache for {symbol} {timeframe}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in polling loop for {symbol} {timeframe}: {e}")
        
        await asyncio.sleep(interval_seconds)

async def start_background_pollers(symbol: str = "BTC/USDT"):
    """Starts background polling loops for all required timeframes."""
    intervals = {
        '1m': 15,
        '5m': 30,
        '15m': 60,
        '1h': 300,   # 5 mins
        '4h': 900,   # 15 mins
        '1d': 3600   # 1 hour
    }
    
    for tf, interval in intervals.items():
        task_name = f"poll_{symbol}_{tf}"
        await task_manager.start_task(task_name, _poll_timeframe(symbol, tf, interval))

async def fetch_mtf_data(symbol: str = "BTC/USDT") -> Dict[str, Any]:
    """
    Constructs the MTF data structure entirely from cache to prevent rate limits.
    Fetches the live ticker directly for accurate current pricing.
    """
    # 1. Fetch live ticker (with retries and backoff via client)
    try:
        ticker = await binance_client.fetch_ticker(symbol)
        last_price = ticker.get('last', 0)
        change_percentage = ticker.get('percentage', 0)
    except Exception as e:
        logger.error(f"Failed to fetch live ticker for {symbol}: {e}")
        last_price = 0
        change_percentage = 0

    # 2. Get cached data for all timeframes
    timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    mtf_trends = {}
    primary_df = None
    fallback_df = None

    for tf in timeframes:
        cached = await market_cache.get_data(symbol, tf)
        if cached:
            df, trend = cached
            mtf_trends[tf] = trend
            if tf == '1h':
                primary_df = df
            if fallback_df is None:
                fallback_df = df
        else:
            mtf_trends[tf] = "Neutral"
            
    if primary_df is None or primary_df.empty:
        primary_df = fallback_df

    if primary_df is None or primary_df.empty:
        # Absolute fallback if cache is totally empty
        logger.warning(f"Cache is completely empty for {symbol}. Returning default payload.")
        return _empty_mtf_payload(symbol, last_price, change_percentage)

    # 3. Calculate indicators on the primary timeframe (1h)
    try:
        # Use copy to prevent setting with copy warnings
        df = primary_df.copy()
        
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['ema_20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
        bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_mavg'] = bb.bollinger_mavg()
        df['bbw'] = ((df['bb_high'] - df['bb_low']) / df['bb_mavg']) * 100
        
        latest_bbw = df['bbw'].iloc[-1]
        if pd.isna(latest_bbw):
            volatility_state = "Normal"
        elif latest_bbw < 1.5:
            volatility_state = "Squeeze"
        elif latest_bbw < 3.5:
            volatility_state = "Normal"
        elif latest_bbw < 6.0:
            volatility_state = "Expansion"
        else:
            volatility_state = "Extreme"
            
        df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
        
        latest = df.iloc[-1]
        
        # Local Support and Resistance (Swing high/low over last 20 candles)
        recent_20 = df.iloc[-20:]
        support = recent_20['low'].min()
        resistance = recent_20['high'].max()
        
        return {
            "symbol": symbol,
            "last_price": last_price,
            "change_percentage": change_percentage,
            "mtf_trends": mtf_trends,
            "volatility_state": volatility_state,
            "indicators": {
                "rsi": round(latest['rsi'], 2) if not pd.isna(latest['rsi']) else 50,
                "macd": round(latest['macd'], 2) if not pd.isna(latest['macd']) else 0,
                "macd_signal": round(latest['macd_signal'], 2) if not pd.isna(latest['macd_signal']) else 0,
                "ema_20": round(latest['ema_20'], 2) if not pd.isna(latest['ema_20']) else last_price,
                "ema_50": round(latest['ema_50'], 2) if not pd.isna(latest['ema_50']) else last_price,
                "bb_high": round(latest['bb_high'], 2) if not pd.isna(latest['bb_high']) else last_price * 1.05,
                "bb_low": round(latest['bb_low'], 2) if not pd.isna(latest['bb_low']) else last_price * 0.95,
                "bbw": round(latest_bbw, 2) if not pd.isna(latest_bbw) else 0,
                "atr": round(latest['atr'], 2) if not pd.isna(latest['atr']) else 100,
                "support": round(support, 2),
                "resistance": round(resistance, 2)
            }
        }
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        return _empty_mtf_payload(symbol, last_price, change_percentage)

def _empty_mtf_payload(symbol: str, last_price: float, change_percentage: float) -> dict:
    return {
        "symbol": symbol,
        "last_price": last_price,
        "change_percentage": change_percentage,
        "mtf_trends": {'1m': 'Neutral', '5m': 'Neutral', '15m': 'Neutral', '1h': 'Neutral', '4h': 'Neutral', '1d': 'Neutral'},
        "volatility_state": "Normal",
        "indicators": {
            "rsi": 50, "macd": 0, "macd_signal": 0,
            "ema_20": last_price, "ema_50": last_price,
            "bb_high": last_price * 1.05, "bb_low": last_price * 0.95,
            "bbw": 0, "atr": 100,
            "support": last_price * 0.95, "resistance": last_price * 1.05
        }
    }

def generate_market_summary(data: dict) -> str:
    """
    Converts raw market data into a highly compressed, structured summary to save tokens.
    """
    rsi = data['indicators']['rsi']
    if rsi > 70:
        rsi_state = "Overbought"
    elif rsi < 30:
        rsi_state = "Oversold"
    else:
        rsi_state = "Neutral"
        
    macd = data['indicators']['macd']
    macd_signal = data['indicators']['macd_signal']
    if macd > macd_signal and macd > 0:
        macd_state = "Strong Bullish"
    elif macd > macd_signal:
        macd_state = "Bullish Crossover"
    elif macd < macd_signal and macd < 0:
        macd_state = "Strong Bearish"
    else:
        macd_state = "Bearish Crossover"
        
    trend_1h = data['mtf_trends'].get('1h', 'Neutral')
    
    summary = f"""{data['symbol']} Summary:
- Trend: {trend_1h} (1H)
- Price: {data['last_price']}
- RSI: {rsi} ({rsi_state})
- MACD: {macd_state}
- Resistance: {data['indicators']['resistance']}
- Support: {data['indicators']['support']}
- Volatility: {data['volatility_state']}
"""
    return summary
