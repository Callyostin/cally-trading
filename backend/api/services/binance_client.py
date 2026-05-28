import ccxt
import asyncio
import os
from utils.logger import logger
import traceback

class BinanceClient:
    def __init__(self):
        # We use the synchronous CCXT client to bypass the aiodns/aiohttp 
        # DNS resolution bug on Windows, but we will wrap its calls in 
        # asyncio.to_thread so it behaves exactly like an async client 
        # and doesn't block the FastAPI event loop.
        exchange_config = {
            'enableRateLimit': True,
            'timeout': 30000,
        }
        
        # Add API keys if available in environment variables
        api_key = os.getenv('BINANCE_API_KEY')
        secret = os.getenv('BINANCE_SECRET')
        
        if api_key and secret:
            exchange_config['apiKey'] = api_key
            exchange_config['secret'] = secret
            
        self.exchange = ccxt.binance(exchange_config)
        
    async def fetch_ticker(self, symbol: str, retries: int = 3):
        for attempt in range(retries):
            try:
                # Wrap the sync call in to_thread
                ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
                return ticker
            except Exception as e:
                logger.warning(f"Error fetching ticker for {symbol} (Attempt {attempt+1}/{retries}): {repr(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch ticker for {symbol} after {retries} attempts.\n{traceback.format_exc()}")
                    raise

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100, retries: int = 3):
        for attempt in range(retries):
            try:
                ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
                return ohlcv
            except Exception as e:
                logger.warning(f"Error fetching OHLCV for {symbol} {timeframe} (Attempt {attempt+1}/{retries}): {repr(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch OHLCV for {symbol} {timeframe} after {retries} attempts.\n{traceback.format_exc()}")
                    raise

    async def fetch_balance(self, retries: int = 3):
        if not self.exchange.apiKey:
            return None
        for attempt in range(retries):
            try:
                balance = await asyncio.to_thread(self.exchange.fetch_balance)
                return balance
            except Exception as e:
                logger.warning(f"Error fetching balance (Attempt {attempt+1}/{retries}): {repr(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch balance after {retries} attempts.\n{traceback.format_exc()}")
                    return None
                    
    async def fetch_positions(self, retries: int = 3):
        if not self.exchange.apiKey:
            return []
        for attempt in range(retries):
            try:
                # fetch_positions is available on ccxt binance for futures/margin
                positions = await asyncio.to_thread(self.exchange.fetch_positions)
                return positions
            except Exception as e:
                logger.warning(f"Error fetching positions (Attempt {attempt+1}/{retries}): {repr(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch positions after {retries} attempts.\n{traceback.format_exc()}")
                    return []

    async def close(self):
        # Sync ccxt doesn't strictly need close(), but we can safely ignore or call it
        pass

# Global shared instance
binance_client = BinanceClient()
