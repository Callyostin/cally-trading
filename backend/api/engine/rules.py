def evaluate_tactical_confluence(ai_bias: str, indicators: dict) -> dict:
    """
    Evaluates real-time indicators against the AI's macro bias.
    Returns the final tactical signal, confluence score, and reasons.
    """
    score = 0.0
    reasons = []
    
    rsi = indicators.get('rsi', 50)
    macd = indicators.get('macd', 0)
    macd_signal = indicators.get('macd_signal', 0)
    last_price = indicators.get('last_price', 0)
    ema_20 = indicators.get('ema_20', 0)
    
    if ai_bias == "Bullish":
        if rsi < 35:
            score += 15.0
            reasons.append("RSI shows deep oversold pullback (ideal long entry)")
        elif 35 <= rsi <= 55:
            score += 10.0
            reasons.append("RSI is resetting nicely for continuation")
        elif rsi > 70:
            score -= 20.0
            reasons.append("RSI is overbought (chasing is dangerous)")
            
        if macd > macd_signal:
            score += 10.0
            reasons.append("MACD is crossed bullish")
        else:
            score -= 5.0
            
        if last_price > ema_20:
            score += 5.0
            reasons.append("Price is holding above 20 EMA")
            
    elif ai_bias == "Bearish":
        if rsi > 65:
            score += 15.0
            reasons.append("RSI shows overbought bounce (ideal short entry)")
        elif 45 <= rsi <= 65:
            score += 10.0
            reasons.append("RSI is resetting nicely for continuation down")
        elif rsi < 30:
            score -= 20.0
            reasons.append("RSI is deeply oversold (chasing shorts is dangerous)")
            
        if macd < macd_signal:
            score += 10.0
            reasons.append("MACD is crossed bearish")
        else:
            score -= 5.0
            
        if last_price < ema_20:
            score += 5.0
            reasons.append("Price is holding below 20 EMA")
            
    else:
        # Neutral bias
        reasons.append("AI Bias is Neutral, waiting for structural shift")
        score = 0.0
        
    # Cap score
    score = max(0.0, min(30.0, score))
    
    # Final Decision Logic
    if ai_bias == "Bullish" and score >= 20.0:
        final_signal = "BUY"
    elif ai_bias == "Bearish" and score >= 20.0:
        final_signal = "SELL"
    else:
        final_signal = "HOLD"
        
    return {
        "tactical_signal": final_signal,
        "confluence_score": round(score, 1),
        "reasons": reasons
    }
