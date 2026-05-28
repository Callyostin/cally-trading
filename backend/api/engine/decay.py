import math
from datetime import datetime, timezone

def calculate_decay(base_confidence: float, generated_at: datetime, volatility_state: str) -> float:
    """
    Exponentially decays the confidence of a signal over time.
    High volatility decays signals much faster than normal conditions.
    """
    if base_confidence <= 0:
        return 0.0
        
    now = datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
        
    minutes_elapsed = (now - generated_at).total_seconds() / 60.0
    
    if minutes_elapsed < 0:
        minutes_elapsed = 0
        
    # Decay factor: higher factor = faster decay
    if volatility_state == "Extreme":
        decay_factor = 0.5   # Very fast decay
    elif volatility_state == "Expansion":
        decay_factor = 0.2
    elif volatility_state == "Squeeze":
        decay_factor = 0.05  # Slow decay, waiting for breakout
    else:
        decay_factor = 0.1   # Normal decay
        
    # Exponential decay formula: N(t) = N0 * e^(-λt)
    decayed_confidence = base_confidence * math.exp(-decay_factor * minutes_elapsed)
    
    return max(0.0, round(decayed_confidence, 2))

def get_expiration_time(generated_at: datetime, volatility_state: str) -> datetime:
    """
    Returns the absolute hard-expiration time of a signal based on volatility.
    """
    import datetime as dt
    
    if volatility_state == "Extreme":
        delta = dt.timedelta(minutes=15)
    elif volatility_state == "Expansion":
        delta = dt.timedelta(minutes=30)
    else:
        delta = dt.timedelta(minutes=60)
        
    return generated_at + delta
