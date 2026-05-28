import os
import sys

# Add the backend dir to sys.path so we can import from api
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.services.ai_agent import agent

try:
    market_data = {
        "indicators": {"rsi": 30},
        "volatility_state": "High"
    }
    news_headlines = ["BTC dumps 10%", "Market crashing"]
    res = agent.analyze_market("BTC", market_data, news_headlines)
    print("SUCCESS")
    print(res)
except Exception as e:
    print("FAILED")
    print(e)
