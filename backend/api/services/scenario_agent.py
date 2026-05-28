from api.services.llm_factory import get_llm
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from api.services.ai_agent import TokenCallbackHandler
import os
import re
from dotenv import load_dotenv

load_dotenv()

class ScenarioForecast(BaseModel):
    forecast: str = Field(description="A detailed, tactical explanation of what will likely happen in this scenario.")
    bullish_probability: float = Field(description="Percentage probability (0-100) of a bullish outcome in this scenario.")
    bearish_probability: float = Field(description="Percentage probability (0-100) of a bearish outcome in this scenario.")
    key_levels: list[str] = Field(description="A list of 2-3 key price levels or technical invalidation points to watch.")

def sanitize_prompt(user_input: str) -> str:
    dangerous_keywords = ["ignore", "override", "system prompt", "forget", "instructions", "bypass"]
    sanitized = user_input.lower()
    for word in dangerous_keywords:
        sanitized = sanitized.replace(word, "[REDACTED]")
    sanitized = re.sub(r'[^a-zA-Z0-9\s\.\?\,\$\-]', '', sanitized)
    return sanitized

class ScenarioAgent:
    def __init__(self):
        self.llm = get_llm(
            model="gpt-4o-mini",
            temperature=0.2, # Keep low for analytical consistency
            max_tokens=1500 # Strict boundary to prevent API abuse
        )
        self.parser = PydanticOutputParser(pydantic_object=ScenarioForecast)
        self.prompt = PromptTemplate(
            template="""You are a Senior Quantitative Analyst. The user is asking a hypothetical "What-If" market scenario.
            
You must analyze the scenario based on the CURRENT Live Market Context provided below. You are forecasting what will happen IF the user's scenario plays out in THIS exact market environment.

CURRENT MARKET CONTEXT:
Volatility State: {volatility_state}
Macro Regime: {market_regime}
Live Price: {last_price}
Current Trend Alignment: {mtf_trends}

USER SCENARIO: {query}

Calculate the probabilities of a bullish vs bearish continuation if this scenario plays out. Provide key invalidation levels.
Ensure your probabilities sum to 100%.

{format_instructions}""",
            input_variables=["volatility_state", "market_regime", "last_price", "mtf_trends", "query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        if self.llm:
            self.chain = self.prompt | self.llm | self.parser
        else:
            self.chain = None

    def analyze_scenario(self, query: str, live_state: dict) -> dict:
        try:
            # Safely extract state with fallbacks if loop hasn't run yet
            volatility_state = live_state.get("volatility_state", "Unknown")
            market_regime = live_state.get("market_regime", "Unknown")
            last_price = live_state.get("last_price", 0.0)
            mtf_trends = live_state.get("mtf_trends", {})

            safe_query = sanitize_prompt(query)

            if not self.chain:
                raise Exception("No AI API key provided in .env")

            result = self.chain.invoke({
                "volatility_state": volatility_state,
                "market_regime": market_regime,
                "last_price": last_price,
                "mtf_trends": mtf_trends,
                "query": safe_query
            }, config={"callbacks": [TokenCallbackHandler("scenario_analysis")]})
            
            return {
                "forecast": result.forecast,
                "bullish_probability": result.bullish_probability,
                "bearish_probability": result.bearish_probability,
                "key_levels": result.key_levels
            }
        except Exception as e:
            return {
                "forecast": f"Error running scenario simulation: {str(e)}",
                "bullish_probability": 50.0,
                "bearish_probability": 50.0,
                "key_levels": []
            }

scenario_agent = ScenarioAgent()
