import asyncio
from api.db.database import SessionLocal
from api.db.models import VirtualPortfolio, ActivePosition, PaperTradeHistory
from api.services.market_data import fetch_mtf_data

async def run_paper_execution_loop():
    """
    Background asynchronous task that constantly monitors ActivePositions.
    It closes them out and calculates PnL if the live market price hits their Stop Loss or Take Profit targets.
    """
    while True:
        db = SessionLocal()
        try:
            positions = db.query(ActivePosition).all()
            if not positions:
                await asyncio.sleep(2)
                continue
                
            portfolio = db.query(VirtualPortfolio).first()
            if not portfolio:
                portfolio = VirtualPortfolio(balance=10000.0)
                db.add(portfolio)
                db.commit()

            # Batch price fetches
            symbols = list(set([p.symbol for p in positions]))
            prices = {}
            for sym in symbols:
                try:
                    data = await fetch_mtf_data(sym)
                    prices[sym] = data["last_price"]
                except:
                    pass

            for pos in positions:
                current_price = prices.get(pos.symbol)
                if not current_price:
                    continue
                
                close_trade = False
                pnl = 0.0
                outcome = ""
                exit_price = 0.0
                
                # To simulate faster execution for the prototype, we slightly tighten the hit thresholds.
                if pos.direction == "Long":
                    if current_price >= pos.take_profit * 0.999:
                        close_trade = True
                        pnl = (pos.take_profit - pos.entry_price) * pos.size
                        outcome = "Win"
                        exit_price = pos.take_profit
                    elif current_price <= pos.stop_loss * 1.001:
                        close_trade = True
                        pnl = (pos.stop_loss - pos.entry_price) * pos.size
                        outcome = "Loss"
                        exit_price = pos.stop_loss
                elif pos.direction == "Short":
                    if current_price <= pos.take_profit * 1.001:
                        close_trade = True
                        pnl = (pos.entry_price - pos.take_profit) * pos.size
                        outcome = "Win"
                        exit_price = pos.take_profit
                    elif current_price >= pos.stop_loss * 0.999:
                        close_trade = True
                        pnl = (pos.entry_price - pos.stop_loss) * pos.size
                        outcome = "Loss"
                        exit_price = pos.stop_loss
                        
                if close_trade:
                    # Log to History
                    history = PaperTradeHistory(
                        symbol=pos.symbol, direction=pos.direction,
                        entry_price=pos.entry_price, exit_price=exit_price,
                        size=pos.size, pnl=pnl, outcome=outcome
                    )
                    db.add(history)
                    
                    # Update Virtual Balance (return margin capital + realized pnl)
                    capital_returned = (pos.size * pos.entry_price) + pnl
                    portfolio.balance += capital_returned
                    
                    # Destroy active position
                    db.delete(pos)
                    
            db.commit()
        except Exception as e:
            print(f"Paper Engine Error: {e}")
        finally:
            db.close()
            
        await asyncio.sleep(2) # Run frequently to ensure accurate SL/TP execution
