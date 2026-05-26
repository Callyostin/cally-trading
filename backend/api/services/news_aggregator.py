import random

def fetch_crypto_headlines(symbol: str, volatility_state: str) -> list:
    """
    Simulates fetching real-time headlines from crypto news APIs.
    Dynamically adjusts the tone of the headlines based on the current 
    volatility state to give the NLP LLM engine realistic contextual data.
    """
    asset = symbol.split('/')[0]
    
    if volatility_state == "Extreme":
        return [
            f"BREAKING: Massive liquidation cascade hits {asset} markets!",
            f"Traders panic as {asset} volatility reaches historic highs.",
            "Is the bull run over? Analysts warn of further downside.",
            f"Whales moving massive amounts of {asset} to exchanges."
        ]
    elif volatility_state == "Expansion":
        return [
            f"{asset} breaks key resistance, eyes higher targets.",
            "Institutional inflows surging as market structure improves.",
            f"Traders cautiously optimistic as {asset} shows strength.",
            "New protocol upgrades driving positive sentiment across the board."
        ]
    elif volatility_state == "Squeeze":
        return [
            f"{asset} volatility drops to multi-month lows. Big move imminent?",
            "Market choppy and directionless ahead of key macro data.",
            f"Retail interest in {asset} fading amid sideways action.",
            "Bollinger bands tightest since last year, traders await breakout."
        ]
    else:
        return [
            f"{asset} holding steady at major support levels.",
            "General market sentiment remains relatively balanced today.",
            f"On-chain metrics for {asset} show healthy long-term accumulation.",
            "No major macro catalysts expected this week, expecting chop."
        ]
