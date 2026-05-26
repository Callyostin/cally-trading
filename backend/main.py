from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import asyncio
import json

# Load env vars
load_dotenv()

from api.db.database import engine, Base, get_db, SessionLocal
from api.db.models import TradeSignal, TradeJournal, VirtualPortfolio, ActivePosition, PaperTradeHistory
from api.services.ai_agent import agent
from api.services.behavioral_agent import behavioral_agent
from api.services.market_data import fetch_mtf_data
from api.services.risk_engine import calculate_risk_metrics, apply_mtf_weighting
from api.services.backtester import run_backtest
from api.services.news_aggregator import fetch_crypto_headlines
from api.services.outcome_tracker import track_signal_outcomes
from api.services.learning_engine import get_historical_memory_multiplier, get_global_performance
from api.services.paper_engine import run_paper_execution_loop
from api.services.regime_detector import detect_market_regime
from api.services.scenario_agent import scenario_agent
from pydantic import BaseModel

# Global state for scenario forecasting
LATEST_MARKET_STATE = {}

class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"

class JournalEntry(BaseModel):
    symbol: str
    direction: str
    pnl: float
    emotion: str
    notes: str

class PaperExecuteRequest(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    size: float
    take_profit: float
    stop_loss: float

class ScenarioRequest(BaseModel):
    query: str

# Create DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Trading Assistant API",
    description="Backend services for the AI Trading Assistant Platform",
    version="1.0.0"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = set()

@app.websocket("/ws/signals")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.post("/api/backtest")
def trigger_backtest(req: BacktestRequest):
    return run_backtest(symbol=req.symbol, timeframe=req.timeframe, limit=1000)

@app.post("/api/journal/log")
def log_trade(req: JournalEntry):
    db = SessionLocal()
    try:
        new_entry = TradeJournal(
            symbol=req.symbol,
            direction=req.direction,
            pnl=req.pnl,
            emotion=req.emotion,
            notes=req.notes
        )
        db.add(new_entry)
        db.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.get("/api/journal/history")
def get_journal_history():
    db = SessionLocal()
    try:
        trades = db.query(TradeJournal).order_by(TradeJournal.created_at.desc()).all()
        return {"success": True, "data": [{"symbol": t.symbol, "direction": t.direction, "pnl": t.pnl, "emotion": t.emotion, "notes": t.notes, "created_at": str(t.created_at)} for t in trades]}
    finally:
        db.close()

@app.get("/api/journal/analyze")
def analyze_behavior():
    db = SessionLocal()
    try:
        trades = db.query(TradeJournal).order_by(TradeJournal.created_at.desc()).all()
        journal_data = [{"symbol": t.symbol, "direction": t.direction, "pnl": t.pnl, "emotion": t.emotion, "notes": t.notes} for t in trades]
        analysis = behavioral_agent.analyze_behavior(journal_data)
        return {"success": True, "analysis": analysis}
    finally:
        db.close()

@app.post("/api/paper/execute")
def execute_paper_trade(req: PaperExecuteRequest):
    db = SessionLocal()
    try:
        portfolio = db.query(VirtualPortfolio).first()
        if not portfolio:
            portfolio = VirtualPortfolio(balance=10000.0)
            db.add(portfolio)
            db.commit()
            
        required_margin = req.size * req.entry_price
        if portfolio.balance < required_margin:
            return {"success": False, "error": "Insufficient virtual balance."}
            
        # Deduct margin
        portfolio.balance -= required_margin
        
        # Open position
        new_pos = ActivePosition(
            symbol=req.symbol, direction=req.direction,
            entry_price=req.entry_price, size=req.size,
            take_profit=req.take_profit, stop_loss=req.stop_loss
        )
        db.add(new_pos)
        db.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.get("/api/paper/portfolio")
def get_paper_portfolio():
    db = SessionLocal()
    try:
        portfolio = db.query(VirtualPortfolio).first()
        if not portfolio:
            portfolio = VirtualPortfolio(balance=10000.0)
            db.add(portfolio)
            db.commit()
            
        active = db.query(ActivePosition).all()
        history = db.query(PaperTradeHistory).order_by(PaperTradeHistory.created_at.desc()).limit(50).all()
        
        return {
            "success": True,
            "balance": portfolio.balance,
            "active_positions": [{"symbol": p.symbol, "direction": p.direction, "entry_price": p.entry_price, "size": p.size, "take_profit": p.take_profit, "stop_loss": p.stop_loss} for p in active],
            "history": [{"symbol": h.symbol, "direction": h.direction, "pnl": h.pnl, "outcome": h.outcome, "created_at": str(h.created_at)} for h in history]
        }
    finally:
        db.close()

@app.post("/api/paper/reset")
def reset_paper_account():
    db = SessionLocal()
    try:
        db.query(ActivePosition).delete()
        db.query(PaperTradeHistory).delete()
        portfolio = db.query(VirtualPortfolio).first()
        if portfolio:
            portfolio.balance = 10000.0
        else:
            portfolio = VirtualPortfolio(balance=10000.0)
            db.add(portfolio)
        db.commit()
        return {"success": True}
    finally:
        db.close()

@app.post("/api/scenario/analyze")
def analyze_scenario(req: ScenarioRequest):
    global LATEST_MARKET_STATE
    result = scenario_agent.analyze_scenario(req.query, LATEST_MARKET_STATE)
    return {"success": True, "data": result}

async def generate_and_broadcast_signals():
    while True:
        try:
            if not active_connections:
                await asyncio.sleep(5)
                continue
                
            symbol = "BTC/USDT"
            
            # 1. Fetch Async MTF Data
            live_data = await fetch_mtf_data(symbol)
            
            # 2. Call the AI Orchestrator
            # 2.5 Fetch Dynamic News Headlines
            headlines = fetch_crypto_headlines(symbol, live_data["volatility_state"])
            
            # 2.8 Detect Market Regime
            regime_data = detect_market_regime(
                rsi=live_data["indicators"]["rsi"],
                volatility_state=live_data["volatility_state"],
                mtf_trends=live_data["mtf_trends"]
            )
            
            # 3. Analyze with NLP & AI Agent
            ai_result = agent.analyze_market(symbol, live_data, headlines)
            
            # 3.2 Dynamic Risk Calculations
            risk_result = calculate_risk_metrics(symbol, live_data["last_price"], live_data["indicators"]["atr"], ai_result["signal"])
            
            # 3.5 Apply MTF, Volatility & Sentiment Weighting
            base_adj_confidence = apply_mtf_weighting(
                signal=ai_result["signal"], 
                base_confidence=ai_result["confidence"], 
                mtf_trends=live_data["mtf_trends"],
                volatility_state=live_data["volatility_state"],
                fear_greed_score=ai_result.get("fear_greed_score", 50)
            )
            
            # 3.8 Apply Adaptive Memory Reinforcement Loop
            db = SessionLocal()
            try:
                memory_data = get_historical_memory_multiplier(db, ai_result["signal"], live_data["volatility_state"])
                global_perf = get_global_performance(db)
            finally:
                db.close()
                
            final_confidence = min(99.0, round(base_adj_confidence * memory_data["multiplier"], 1))
            ai_result["confidence"] = final_confidence
            
            # Update Global Market State for Scenario Agent
            global LATEST_MARKET_STATE
            LATEST_MARKET_STATE = {
                "volatility_state": live_data["volatility_state"],
                "market_regime": regime_data["regime"],
                "last_price": live_data["last_price"],
                "mtf_trends": live_data["mtf_trends"]
            }
            
            # Combine payloads
            final_payload = {
                **ai_result, 
                **risk_result, 
                "mtf_trends": live_data["mtf_trends"],
                "volatility_state": live_data["volatility_state"],
                "memory_reason": memory_data["reason"],
                "global_performance": global_perf,
                "market_regime": regime_data["regime"],
                "regime_strategy": regime_data["strategy"]
            }
            
            # 4. Save to DB
            db = SessionLocal()
            try:
                signal_record = TradeSignal(
                    symbol=final_payload["symbol"],
                    prediction=final_payload["signal"],
                    confidence=float(final_payload["confidence"]),
                    market_condition=final_payload["market_condition"],
                    reasons=json.dumps(final_payload["reasons"]),
                    entry_price=final_payload["entry_price"],
                    stop_loss=final_payload["stop_loss"],
                    take_profit=final_payload["take_profit"],
                    risk_reward_ratio=final_payload["risk_reward_ratio"],
                    risk_level=final_payload["risk_level"],
                    mtf_trends=json.dumps(final_payload["mtf_trends"]),
                    volatility_state=final_payload["volatility_state"],
                    volatility_explanation=final_payload["volatility_explanation"],
                    fear_greed_score=final_payload["fear_greed_score"],
                    sentiment_label=final_payload["sentiment_label"],
                    news_summary=final_payload["news_summary"],
                    market_regime=final_payload["market_regime"],
                    regime_strategy=final_payload["regime_strategy"]
                )
                db.add(signal_record)
                db.commit()
            except Exception as e:
                print(f"Error saving to DB: {e}")
                db.rollback()
            finally:
                db.close()
                
            # 5. Broadcast to clients
            for connection in list(active_connections):
                try:
                    await connection.send_json(final_payload)
                except Exception:
                    active_connections.remove(connection)
                    
        except Exception as e:
            print(f"Background task error: {e}")
            
        await asyncio.sleep(20) # Poll slightly slower to respect rate limits with 6 timeframes

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(generate_and_broadcast_signals())
    asyncio.create_task(track_signal_outcomes())
    asyncio.create_task(run_paper_execution_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
