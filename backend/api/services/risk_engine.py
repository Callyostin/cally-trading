def calculate_risk_metrics(signal: str, last_price: float, atr: float, bb_high: float, bb_low: float):
    if signal == "HOLD" or signal == "NEUTRAL":
        return {
            "entry_price": round(last_price, 2),
            "stop_loss": round(last_price, 2),
            "take_profit": round(last_price, 2),
            "risk_reward_ratio": "0:0",
            "risk_level": "None"
        }
        
    sl_distance = atr * 2.0
    
    if signal == "BUY" or signal == "Strong Buy":
        entry_price = last_price
        stop_loss = entry_price - sl_distance
        if bb_low < stop_loss:
            stop_loss = bb_low
            
        actual_sl_dist = entry_price - stop_loss
        take_profit = entry_price + (actual_sl_dist * 2.3)
        
        volatility_pct = (atr / entry_price) * 100
        if volatility_pct > 3:
            risk_level = "High"
        elif volatility_pct > 1.5:
            risk_level = "Medium"
        else:
            risk_level = "Low"
            
        return {
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward_ratio": "1:2.3",
            "risk_level": risk_level
        }
        
    elif signal == "SELL" or signal == "Strong Sell":
        entry_price = last_price
        stop_loss = entry_price + sl_distance
        
        if bb_high > stop_loss:
            stop_loss = bb_high
            
        actual_sl_dist = stop_loss - entry_price
        take_profit = entry_price - (actual_sl_dist * 2.3)
        
        volatility_pct = (atr / entry_price) * 100
        if volatility_pct > 3:
            risk_level = "High"
        elif volatility_pct > 1.5:
            risk_level = "Medium"
        else:
            risk_level = "Low"
            
        return {
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward_ratio": "1:2.3",
            "risk_level": risk_level
        }
        
    return {
        "entry_price": round(last_price, 2),
        "stop_loss": round(last_price * 0.95, 2),
        "take_profit": round(last_price * 1.05, 2),
        "risk_reward_ratio": "1:2",
        "risk_level": "Medium"
    }

def apply_mtf_weighting(signal: str, base_confidence: float, mtf_trends: dict, volatility_state: str = "Normal", fear_greed_score: int = 50) -> float:
    """
    Penalizes or boosts the base_confidence based on MTF alignment and NLP Sentiment.
    """
    if signal == "HOLD" or signal == "NEUTRAL":
        return base_confidence
        
    weights = {
        '1m': 0.05,
        '5m': 0.05,
        '15m': 0.10,
        '1h': 0.20,
        '4h': 0.30,
        '1d': 0.30
    }
    
    score = 0
    for tf, trend in mtf_trends.items():
        weight = weights.get(tf, 0)
        if signal == "BUY" and trend == "Bullish":
            score += weight
        elif signal == "SELL" and trend == "Bearish":
            score += weight
        elif trend == "Neutral":
            score += (weight * 0.5)
            
    # Scale score to a multiplier
    if score >= 0.8:
        adjusted = base_confidence * 1.15 # Strong alignment boost
    elif score < 0.4:
        adjusted = base_confidence * 0.60 # Heavy counter-trend penalty
    else:
        adjusted = base_confidence
        
    if volatility_state == "Extreme":
        adjusted = adjusted * 0.60 # Brutal penalty to protect capital during chop
        
    # Sentiment Contrarian Adjustments
    if signal == "BUY" and fear_greed_score < 25:
        adjusted = adjusted * 1.1 # Boost confidence for buying fear
    elif signal == "BUY" and fear_greed_score > 75:
        adjusted = adjusted * 0.8 # Penalize buying top greed
    elif signal == "SELL" and fear_greed_score > 75:
        adjusted = adjusted * 1.1 # Boost confidence for shorting greed
    elif signal == "SELL" and fear_greed_score < 25:
        adjusted = adjusted * 0.8 # Penalize shorting bottom fear
        
    return min(99.0, round(adjusted, 1))
