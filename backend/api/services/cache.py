import sqlite3
import json
import io
import pandas as pd
from typing import Dict, Any, Optional
import asyncio
from utils.logger import logger

class MarketDataCache:
    def __init__(self, db_path: str = "market_cache.db"):
        self.db_path = db_path
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS market_data (
                        symbol TEXT,
                        timeframe TEXT,
                        data_json TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, timeframe)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite cache: {e}")

    async def set_data(self, symbol: str, timeframe: str, data: pd.DataFrame, trend: str):
        async with self._lock:
            if symbol not in self._memory_cache:
                self._memory_cache[symbol] = {}
            
            payload = {
                "trend": trend,
                "df_json": data.to_json(orient='records')
            }
            
            self._memory_cache[symbol][timeframe] = payload
            
            # Persist to SQLite in a thread to avoid blocking
            await asyncio.to_thread(self._save_to_sqlite, symbol, timeframe, payload)

    def _save_to_sqlite(self, symbol: str, timeframe: str, payload: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data (symbol, timeframe, data_json)
                    VALUES (?, ?, ?)
                """, (symbol, timeframe, json.dumps(payload)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save {symbol} {timeframe} to SQLite: {e}")

    async def get_data(self, symbol: str, timeframe: str) -> Optional[tuple[pd.DataFrame, str]]:
        # 1. Try memory
        if symbol in self._memory_cache and timeframe in self._memory_cache[symbol]:
            payload = self._memory_cache[symbol][timeframe]
            df = pd.read_json(io.StringIO(payload["df_json"]), orient='records')
            return df, payload["trend"]
            
        # 2. Try SQLite
        payload = await asyncio.to_thread(self._load_from_sqlite, symbol, timeframe)
        if payload:
            async with self._lock:
                if symbol not in self._memory_cache:
                    self._memory_cache[symbol] = {}
                self._memory_cache[symbol][timeframe] = payload
            df = pd.read_json(io.StringIO(payload["df_json"]), orient='records')
            return df, payload["trend"]
            
        return None

    def _load_from_sqlite(self, symbol: str, timeframe: str) -> Optional[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data_json FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                """, (symbol, timeframe))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to load {symbol} {timeframe} from SQLite: {e}")
        return None
        
    async def get_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        results = {}
        for tf in timeframes:
            data = await self.get_data(symbol, tf)
            if data:
                results[tf] = data
        return results

# Global shared instance
market_cache = MarketDataCache()
