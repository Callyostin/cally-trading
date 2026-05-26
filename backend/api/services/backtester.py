import ccxt
import pandas as pd
import ta
import numpy as np

def run_backtest(symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 1000):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate Indicators
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        df['ema_20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
        df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
        
        # Simulation variables
        initial_balance = 10000.0
        balance = initial_balance
        equity_curve = []
        trades = 0
        winning_trades = 0
        gross_profit = 0.0
        gross_loss = 0.0
        max_drawdown = 0.0
        peak_balance = initial_balance
        
        in_position = False
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        position_size = 0.0
        
        # Start iterating after indicators populate (row 50)
        for i in range(50, len(df)):
            current_row = df.iloc[i]
            
            # 1. Manage existing position
            if in_position:
                if current_row['low'] <= stop_loss:
                    exit_price = stop_loss
                    pnl = (exit_price - entry_price) * position_size
                    balance += pnl
                    trades += 1
                    gross_loss += abs(pnl)
                    in_position = False
                elif current_row['high'] >= take_profit:
                    exit_price = take_profit
                    pnl = (exit_price - entry_price) * position_size
                    balance += pnl
                    trades += 1
                    winning_trades += 1
                    gross_profit += pnl
                    in_position = False
            
            # 2. Look for new entry (Simulating our AI's technical rules)
            if not in_position:
                rsi = current_row['rsi']
                ema20 = current_row['ema_20']
                ema50 = current_row['ema_50']
                
                # Trend alignment & oversold pullback
                if rsi < 40 and ema20 > ema50:
                    in_position = True
                    entry_price = current_row['close']
                    atr = current_row['atr']
                    # Dynamic Risk Engine targets
                    stop_loss = entry_price - (atr * 2)
                    take_profit = entry_price + (atr * 4) # 1:2 R/R
                    position_size = (balance * 0.99) / entry_price
            
            # Update metrics
            if balance > peak_balance:
                peak_balance = balance
            drawdown = (peak_balance - balance) / peak_balance * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                
            # We record equity curve every row for smooth chart
            equity_curve.append({
                "timestamp": current_row['timestamp'],
                "equity": round(balance, 2)
            })
            
        win_rate = (winning_trades / trades * 100) if trades > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        net_profit = balance - initial_balance
        
        return {
            "success": True,
            "metrics": {
                "initial_balance": initial_balance,
                "final_balance": round(balance, 2),
                "net_profit": round(net_profit, 2),
                "net_profit_pct": round((net_profit / initial_balance) * 100, 2),
                "total_trades": trades,
                "win_rate": round(win_rate, 2),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(max_drawdown, 2)
            },
            "equity_curve": equity_curve
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
