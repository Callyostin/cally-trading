import tiktoken
from api.db.database import SessionLocal
from api.db.models import TokenUsage

# Pricing per 1k tokens for gpt-4o-mini as an example
COST_PER_1K_PROMPT = 0.00015
COST_PER_1K_COMPLETION = 0.0006

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def compress_prompt(text: str, max_tokens: int = 1500) -> str:
    """
    Naively compress a prompt if it exceeds the max tokens.
    In a real scenario, we would selectively trim historical data.
    Here we just truncate and remove redundant whitespace.
    """
    import re
    # Remove excess whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    tokens = count_tokens(text)
    if tokens > max_tokens:
        encoding = tiktoken.get_encoding("cl100k_base")
        encoded = encoding.encode(text)
        truncated = encoded[:max_tokens]
        text = encoding.decode(truncated) + "... [TRUNCATED]"
    
    return text

def log_token_usage(endpoint: str, prompt_tokens: int, completion_tokens: int):
    db = SessionLocal()
    try:
        total = prompt_tokens + completion_tokens
        cost = (prompt_tokens / 1000.0 * COST_PER_1K_PROMPT) + (completion_tokens / 1000.0 * COST_PER_1K_COMPLETION)
        
        usage = TokenUsage(
            endpoint=endpoint,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost=cost
        )
        db.add(usage)
        db.commit()
    except Exception as e:
        print(f"Error logging token usage: {e}")
    finally:
        db.close()
