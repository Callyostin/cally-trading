import os
import json
from api.services.llm_factory import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.callbacks import BaseCallbackHandler
from typing import List
from api.services.token_manager import compress_prompt, log_token_usage
from api.services.market_data import generate_market_summary
import hashlib
from api.db.database import SessionLocal
from api.db.models import AICache

class TokenCallbackHandler(BaseCallbackHandler):
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
    def on_llm_end(self, response, **kwargs):
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            log_token_usage(self.endpoint, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


class MarketAnalysisOutput(BaseModel):
    bias: str = Field(description="The macro directional bias, one of: Bullish, Bearish, Neutral")
    bias_confidence: int = Field(description="Confidence level percentage in the macro bias between 0 and 100")
    market_condition: str = Field(description="A short phrase describing the macro condition (e.g. 'Bearish continuation', 'Bullish breakout')")
    reasons: List[str] = Field(description="A list of 3-5 bullet points explaining the strategic reasons for the bias")
    volatility_explanation: str = Field(description="A precise 1-sentence warning or observation about current volatility conditions based on BBW and ATR.")
    fear_greed_score: int = Field(description="A score from 0 (Extreme Fear) to 100 (Extreme Greed) based on NLP analysis of the provided news headlines.")
    sentiment_label: str = Field(description="One of: Extreme Fear, Fear, Neutral, Greed, Extreme Greed")
    news_summary: str = Field(description="A concise 1-2 sentence summary of the overarching narrative driving the market based on the headlines.")

class RealAIAgent:
    def __init__(self):
        self.llm = get_llm(temperature=0.2, model="gpt-4o-mini", max_tokens=1500)
        if self.llm:
            self.parser = JsonOutputParser(pydantic_object=MarketAnalysisOutput)
            self.prompt = PromptTemplate(
                template="""You are an Institutional AI Trading Strategist.
Analyze the following highly compressed market summary and recent news headlines for {symbol}.
Provide a MACRO DIRECTIONAL BIAS (Bullish, Bearish, Neutral) rather than an immediate execution signal.

Market Summary:
{market_summary}

Recent News Headlines:
{news_headlines}

Rules:
1. Cross-reference the indicators in the summary to form your strategic directional bias.
2. Your reasons must be concise, focusing on macro context and overarching trend.
3. Analyze the Volatility state to generate a `volatility_explanation` warning.
4. Perform NLP sentiment analysis on the News Headlines to calculate a `fear_greed_score` (0-100), assign a `sentiment_label`, and generate a `news_summary`.

{format_instructions}
""",
                input_variables=["symbol", "market_summary", "news_headlines"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()},
            )
            self.chain = self.prompt | self.llm | self.parser
        else:
            self.llm = None

    def analyze_market(self, symbol: str, market_data: dict, news_headlines: list) -> dict:
        """
        Uses LangChain and OpenAI to analyze the market data and headlines.
        Falls back to rule-based logic if no API key is provided.
        """
        if self.llm:
            try:
                market_summary = generate_market_summary(market_data)
                news_str = json.dumps(news_headlines)
                compressed_news = compress_prompt(news_str, max_tokens=500)
                
                # Check semantic cache
                state_str = f"{symbol}_{market_summary}_{compressed_news}"
                state_hash = hashlib.md5(state_str.encode('utf-8')).hexdigest()
                
                db = SessionLocal()
                try:
                    cached = db.query(AICache).filter(AICache.state_hash == state_hash).first()
                    if cached:
                        print(f"AI Cache hit for {symbol}")
                        return {"symbol": symbol, **json.loads(cached.response_json)}
                finally:
                    db.close()

                response = self.chain.invoke({
                    "symbol": symbol,
                    "market_summary": market_summary,
                    "news_headlines": compressed_news
                }, config={"callbacks": [TokenCallbackHandler("analyze_market")]})
                
                if isinstance(response.get("reasons"), str):
                    response["reasons"] = [response["reasons"]]
                    
                # Save to cache
                db = SessionLocal()
                try:
                    new_cache = AICache(state_hash=state_hash, response_json=json.dumps(response))
                    db.add(new_cache)
                    db.commit()
                except Exception as e:
                    print(f"Cache save error: {e}")
                    db.rollback()
                finally:
                    db.close()
                    
                return {
                    "symbol": symbol,
                    **response
                }
            except Exception as e:
                print(f"LLM Error: {e}")
                pass

        # Fallback Logic (Failsafe)
        vol_state = market_data.get("volatility_state", "Normal")
        
        bias = "Neutral"
        cond = "Signal generation temporarily unavailable"
        reasons = [
            "AI Analysis Service is currently unavailable", 
            "Awaiting system recovery to resume market tracking"
        ]
        fg_score = 50
        fg_label = "Neutral"
        summary = "No narrative available due to API service disruption."
            
        vol_exp = f"Current volatility state is {vol_state}."

        return {
            "symbol": symbol,
            "bias": bias,
            "bias_confidence": 0,
            "market_condition": cond,
            "reasons": reasons,
            "volatility_explanation": vol_exp,
            "fear_greed_score": fg_score,
            "sentiment_label": fg_label,
            "news_summary": summary
        }

agent = RealAIAgent()
