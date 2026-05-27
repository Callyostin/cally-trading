import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.callbacks import BaseCallbackHandler
from typing import List
from api.services.token_manager import compress_prompt, log_token_usage
from api.services.market_data import generate_market_summary

class TokenCallbackHandler(BaseCallbackHandler):
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
    def on_llm_end(self, response, **kwargs):
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            log_token_usage(self.endpoint, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


class MarketAnalysisOutput(BaseModel):
    signal: str = Field(description="The trading signal, one of: BUY, SELL, HOLD")
    confidence: int = Field(description="Confidence level percentage between 0 and 100")
    market_condition: str = Field(description="A short phrase describing the condition (e.g. 'Bearish continuation', 'Bullish breakout')")
    reasons: List[str] = Field(description="A list of 3-5 bullet points explaining the technical reasons for the signal")
    volatility_explanation: str = Field(description="A precise 1-sentence warning or observation about current volatility conditions based on BBW and ATR.")
    fear_greed_score: int = Field(description="A score from 0 (Extreme Fear) to 100 (Extreme Greed) based on NLP analysis of the provided news headlines.")
    sentiment_label: str = Field(description="One of: Extreme Fear, Fear, Neutral, Greed, Extreme Greed")
    news_summary: str = Field(description="A concise 1-2 sentence summary of the overarching narrative driving the market based on the headlines.")

class RealAIAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.llm = ChatOpenAI(temperature=0.2, model="gpt-4o-mini", api_key=self.api_key, max_tokens=250)
            self.parser = JsonOutputParser(pydantic_object=MarketAnalysisOutput)
            self.prompt = PromptTemplate(
                template="""You are a Senior AI Trading Systems Engineer and Quantitative Analyst.
Analyze the following structured market summary and recent news headlines for {symbol} and provide a highly structured, actionable trading signal.

Market Summary:
{market_summary}

Recent News Headlines:
{news_headlines}

Rules:
1. Cross-reference the indicators in the summary to form your directional thesis.
2. Your reasons must be concise and actionable technical observations.
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

                response = self.chain.invoke({
                    "symbol": symbol,
                    "market_summary": market_summary,
                    "news_headlines": compressed_news
                }, config={"callbacks": [TokenCallbackHandler("analyze_market")]})
                
                if isinstance(response.get("reasons"), str):
                    response["reasons"] = [response["reasons"]]
                    
                return {
                    "symbol": symbol,
                    **response
                }
            except Exception as e:
                print(f"LLM Error: {e}")
                pass

        # Fallback Logic
        rsi = market_data.get("indicators", {}).get("rsi", 50)
        vol_state = market_data.get("volatility_state", "Normal")
        
        if rsi < 40:
            signal = "BUY"
            cond = "Oversold bounce potential"
            reasons = ["RSI is below 40 indicating oversold conditions"]
            fg_score = 25
            fg_label = "Fear"
            summary = "Market sentiment is deeply negative, presenting potential oversold bounce opportunities."
        elif rsi > 60:
            signal = "SELL"
            cond = "Overbought retracement"
            reasons = ["RSI is above 60 indicating overbought conditions"]
            fg_score = 75
            fg_label = "Greed"
            summary = "Market is exhibiting greedy behavior, increasing the probability of a sharp retracement."
        else:
            signal = "HOLD"
            cond = "Consolidating"
            reasons = ["RSI is neutral"]
            fg_score = 50
            fg_label = "Neutral"
            summary = "Market narrative is balanced with no clear directional bias from recent headlines."
            
        vol_exp = f"Current volatility state is {vol_state}."

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": 75,
            "market_condition": cond,
            "reasons": reasons + ["(Generated via local fallback algorithm due to missing OpenAI API key)"],
            "volatility_explanation": vol_exp,
            "fear_greed_score": fg_score,
            "sentiment_label": fg_label,
            "news_summary": summary
        }

agent = RealAIAgent()
