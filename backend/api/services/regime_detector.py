def detect_market_regime(rsi: float, volatility_state: str, mtf_trends: dict) -> dict:
    """
    Mathematically classifies the overarching macro market regime and provides a tactical strategy 
    recommendation based on Volatility (BBW), Momentum (RSI), and Multi-Timeframe Alignment.
    """
    bull_count = list(mtf_trends.values()).count("Bullish")
    bear_count = list(mtf_trends.values()).count("Bearish")
    
    if volatility_state == "Extreme":
        regime = "High Volatility / Chop"
        strategy = "Momentum Scalping. Keep holding times extremely short. Use tight stop losses and expect massive wicks. Do not hold overnight."
    elif volatility_state == "Expansion":
        if bull_count >= 4 or rsi > 60:
            regime = "Trending Bullish"
            strategy = "Trend Following. Buy the dips on lower timeframes. Let winners run and aggressively trail stop losses."
        elif bear_count >= 4 or rsi < 40:
            regime = "Trending Bearish"
            strategy = "Trend Following. Short the bounces. Keep a wide stop loss to avoid getting wicked out of the trend."
        else:
            regime = "Breakout / Transition"
            strategy = "Wait for Confirmation. The market volatility is expanding but direction is unclear. Wait for a confirmed 4H candle close."
    elif volatility_state == "Squeeze":
        regime = "Squeeze / Accumulation"
        strategy = "Straddle Strategy. Market is coiling up for a massive directional move. Place buy/sell stops above and below the current range."
    else:
        # Normal volatility
        if 40 <= rsi <= 60 and bull_count < 4 and bear_count < 4:
            regime = "Ranging / Consolidation"
            strategy = "Mean Reversion. Buy support, sell resistance. Take profits aggressively at the middle of the range. Do not expect breakouts."
        elif bull_count >= 4:
            regime = "Slow Grind Bullish"
            strategy = "Accumulation. Slowly scale into long positions on minor pullbacks. Expect shallow dips."
        elif bear_count >= 4:
            regime = "Slow Bleed Bearish"
            strategy = "Distribution. Slowly scale into short positions."
        else:
            regime = "Choppy / Directionless"
            strategy = "Capital Preservation. The market lacks clear momentum or trend alignment. Wait for a clear setup to develop. Do not force trades."

    return {
        "regime": regime,
        "strategy": strategy
    }
