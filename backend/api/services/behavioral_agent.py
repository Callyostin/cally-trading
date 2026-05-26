import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List

class BehavioralAnalysisOutput(BaseModel):
    grade: str = Field(description="A strict letter grade (A, B, C, D, F) evaluating the trader's emotional discipline.")
    overall_assessment: str = Field(description="A brutal but constructive 2-3 sentence summary of their trading psychology.")
    toxic_patterns: List[str] = Field(description="1-3 bullet points identifying specific toxic behaviors (e.g. 'You lose money when trading with FOMO').")
    actionable_advice: List[str] = Field(description="1-2 strict rules the trader must follow to fix their leaks.")

class BehavioralAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.llm = ChatOpenAI(temperature=0.4, model="gpt-4o-mini", api_key=self.api_key)
            self.parser = JsonOutputParser(pydantic_object=BehavioralAnalysisOutput)
            self.prompt = PromptTemplate(
                template="""You are a ruthless but elite Trading Psychologist and Quantitative Coach.
Analyze the following trade journal history. Focus specifically on the relationship between the trader's 'emotion' and their 'pnl'.

Trade Journal History:
{journal_data}

Rules:
1. Be brutally honest. If they are revenge trading or losing money due to FOMO, call it out directly.
2. Identify which emotions yield the highest win rates and which emotions destroy their account.
3. Provide actionable, strict rules to fix their behavioral leaks.

{format_instructions}
""",
                input_variables=["journal_data"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()},
            )
            self.chain = self.prompt | self.llm | self.parser
        else:
            self.llm = None

    def analyze_behavior(self, journal_data: list) -> dict:
        if not journal_data:
            return {
                "grade": "N/A",
                "overall_assessment": "No trades logged yet. Start logging your trades to receive behavioral analysis.",
                "toxic_patterns": [],
                "actionable_advice": []
            }
            
        if self.llm:
            try:
                response = self.chain.invoke({
                    "journal_data": json.dumps(journal_data, indent=2)
                })
                return response
            except Exception as e:
                print(f"LLM Error in Behavioral Agent: {e}")
                pass
                
        # Fallback Logic (Mock analysis based on raw math)
        fomo_pnl = sum(t["pnl"] for t in journal_data if t["emotion"] == "FOMO")
        panic_pnl = sum(t["pnl"] for t in journal_data if t["emotion"] == "Panic")
        revenge_pnl = sum(t["pnl"] for t in journal_data if t["emotion"] == "Revenge")
        confident_pnl = sum(t["pnl"] for t in journal_data if t["emotion"] == "Confident")
        
        toxic = []
        if fomo_pnl < 0:
            toxic.append(f"You have lost ${abs(fomo_pnl):.2f} trading out of FOMO. You lack patience.")
        if panic_pnl < 0:
            toxic.append(f"You have lost ${abs(panic_pnl):.2f} by panic selling. Stop capitulating.")
        if revenge_pnl < 0:
            toxic.append(f"You have lost ${abs(revenge_pnl):.2f} revenge trading. Walk away from the screen after a loss.")
            
        advice = []
        if confident_pnl > 0:
            advice.append("Only take setups where you feel 'Confident'. Stop forcing sub-par trades.")
            
        if not toxic:
            toxic.append("No obvious toxic patterns detected yet.")
            advice.append("Keep logging trades to build a statistically significant sample size.")
            
        return {
            "grade": "C+",
            "overall_assessment": "(Fallback Output): You need to rely on the OpenAI API to get deep psychological insights. This is a basic mathematical review of your PnL vs Emotion metrics.",
            "toxic_patterns": toxic,
            "actionable_advice": advice
        }

behavioral_agent = BehavioralAgent()
