import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(**kwargs):
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if openai_key:
        if "model" not in kwargs:
            kwargs["model"] = "gpt-4o-mini"
        return ChatOpenAI(api_key=openai_key, **kwargs)
    elif gemini_key:
        # Override OpenAI models with Gemini equivalents
        if "model" in kwargs and "gpt" in kwargs["model"]:
            kwargs["model"] = "gemini-3.5-flash"
        elif "model" not in kwargs:
            kwargs["model"] = "gemini-3.5-flash"
            
        # Handle max_tokens parameter for Gemini
        if "max_tokens" in kwargs:
            kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
            
        return ChatGoogleGenerativeAI(google_api_key=gemini_key, **kwargs)
    else:
        return None
