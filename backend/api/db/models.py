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
