from sqlalchemy.orm import Session
from api.db.models import TradeSignal

def get_historical_memory_multiplier(db: Session, signal_direction: str, volatility_state: str) -> dict:
    """
    Calculates the AI's historical win rate for a specific signal direction under a specific volatility state.
    Returns a confidence multiplier and a text explanation based on past performance.
    """
    if signal_direction in ["HOLD", "NEUTRAL"]:
        return {"multiplier": 1.0, "reason": "No adaptive memory adjustment for HOLD signals."}
        
    closed_signals = db.query(TradeSignal).filter(
        TradeSignal.prediction == signal_direction,
        TradeSignal.volatility_state == volatility_state,
        TradeSignal.outcome.in_(["Win", "Loss"])
    ).all()
    
    total = len(closed_signals)
    if total < 3: # Lowered threshold to 3 for testing purposes so memory kicks in faster
        return {"multiplier": 1.0, "reason": "Insufficient historical data for this setup (Adaptive memory requires 3+ closed signals)."}
        
    wins = len([s for s in closed_signals if s.outcome == "Win"])
    win_rate = wins / total
    
    if win_rate >= 0.65:
        # High historical success rate
        return {"multiplier": 1.15, "reason": f"Confidence boosted by 15% due to high historical win rate ({win_rate*100:.0f}%) for {signal_direction}s during {volatility_state} volatility."}
    elif win_rate <= 0.40:
        # Historically poor performance
        return {"multiplier": 0.70, "reason": f"Confidence slashed by 30% to protect capital. Historical win rate is poor ({win_rate*100:.0f}%) for {signal_direction}s during {volatility_state} volatility."}
    else:
        return {"multiplier": 1.0, "reason": f"Historical win rate is average ({win_rate*100:.0f}%). No adaptive memory adjustment applied."}

def get_global_performance(db: Session) -> dict:
    """Gets the lifetime performance of the AI."""
    closed_signals = db.query(TradeSignal).filter(TradeSignal.outcome.in_(["Win", "Loss"])).all()
    total = len(closed_signals)
    wins = len([s for s in closed_signals if s.outcome == "Win"])
    win_rate = (wins / total * 100) if total > 0 else 0.0
    return {
        "total_tracked": total,
        "lifetime_win_rate": round(win_rate, 2)
    }
