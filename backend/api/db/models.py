import json
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from .database import Base

class TradeSignal(Base):
    __tablename__ = "trade_signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    prediction = Column(String) # BUY, SELL, HOLD
    confidence = Column(Float)
    market_condition = Column(String)
    
    reasons = Column(Text)
    mtf_trends = Column(Text)
    
    volatility_state = Column(String)
    volatility_explanation = Column(Text)
    
    fear_greed_score = Column(Integer)
    sentiment_label = Column(String)
    news_summary = Column(Text)
    
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(String)
    risk_level = Column(String)
    
    outcome = Column(String, default="Pending") # Pending, Win, Loss, Expired
    pnl_achieved = Column(Float, default=0.0)
    
    market_regime = Column(String)
    regime_strategy = Column(Text)
    
    # New fields for Hybrid Real-Time Engine
    decay_rate = Column(Float, default=0.1)
    expiration_time = Column(DateTime(timezone=True))
    ai_bias_score = Column(Float, default=0.0)
    local_confluence_score = Column(Float, default=0.0)
    invalidated_by = Column(String, default=None)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AICache(Base):
    __tablename__ = "ai_cache"

    id = Column(Integer, primary_key=True, index=True)
    state_hash = Column(String, index=True, unique=True)
    response_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TradeJournal(Base):
    __tablename__ = "trade_journal"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    direction = Column(String) # Long, Short
    pnl = Column(Float)
    emotion = Column(String) # Confident, FOMO, Panic, Revenge, Neutral
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VirtualPortfolio(Base):
    __tablename__ = "virtual_portfolio"
    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, default=10000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ActivePosition(Base):
    __tablename__ = "active_position"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    direction = Column(String) # Long, Short
    entry_price = Column(Float)
    size = Column(Float)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PaperTradeHistory(Base):
    __tablename__ = "paper_trade_history"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    direction = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    size = Column(Float)
    pnl = Column(Float)
    outcome = Column(String) # Win, Loss
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TokenUsage(Base):
    __tablename__ = "token_usage"
    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # admin, user
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

