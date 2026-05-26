import asyncio
from api.db.database import SessionLocal
from api.db.models import TradeSignal
from api.services.market_data import fetch_mtf_data

async def track_signal_outcomes():
    """
    Background loop that continuously checks pending signals and mathematically grades them 
    as Win/Loss based on live price action hitting the dynamic Risk Engine targets.
    """
    while True:
        db = SessionLocal()
        try:
            pending_signals = db.query(TradeSignal).filter(TradeSignal.outcome == "Pending").all()
            if not pending_signals:
                await asyncio.sleep(5)
                continue
                
            # Group by symbol to minimize API calls
            symbols = list(set([s.symbol for s in pending_signals]))
            prices = {}
            for sym in symbols:
                try:
                    data = await fetch_mtf_data(sym)
                    prices[sym] = data["last_price"]
                except:
                    pass
                    
            for signal in pending_signals:
                current_price = prices.get(signal.symbol)
                if not current_price:
                    continue
                    
                # To simulate faster execution for the prototype, we slightly tighten the hit thresholds.
                # In production, these must hit the exact TP/SL values.
                if signal.prediction == "BUY":
                    if current_price >= signal.take_profit * 0.999:
                        signal.outcome = "Win"
                        signal.pnl_achieved = signal.take_profit - signal.entry_price
                    elif current_price <= signal.stop_loss * 1.001:
                        signal.outcome = "Loss"
                        signal.pnl_achieved = signal.stop_loss - signal.entry_price
                elif signal.prediction == "SELL":
                    if current_price <= signal.take_profit * 1.001:
                        signal.outcome = "Win"
                        signal.pnl_achieved = signal.entry_price - signal.take_profit
                    elif current_price >= signal.stop_loss * 0.999:
                        signal.outcome = "Loss"
                        signal.pnl_achieved = signal.entry_price - signal.stop_loss
                        
            db.commit()
        except Exception as e:
            print(f"Outcome Tracker Error: {e}")
        finally:
            db.close()
            
        await asyncio.sleep(5) # Run frequently to catch quick spikes
