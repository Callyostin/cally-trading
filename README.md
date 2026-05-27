# Nexus AI Trading Assistant: Complete System Architecture

Welcome to the **Nexus AI Trading Assistant**. This document serves as the comprehensive technical foundation for the application. It is designed for software engineers, quantitative developers, and architects to quickly understand *how* the system works, *what* technologies drive it, and *why* specific architectural decisions were made.

---

## 🏗 High-Level Architecture

The application follows a decoupled **Client-Server architecture**, strictly separating the deterministic quantitative math from the frontend UI.

- **Backend**: Python 3, FastAPI, SQLite, LangChain (OpenAI). Operates entirely asynchronously using `asyncio` to handle continuous market data streaming and background execution without blocking API requests.
- **Frontend**: Next.js 14, React, TailwindCSS. A highly responsive, Bloomberg-terminal style dashboard that reacts to server-sent WebSocket events in real-time.

### Why this split?
Quantitative trading systems require extremely low-latency, stateful background loops to calculate indicators and track autonomous trades. Python (with `asyncio` and `ccxt`) is the industry standard for this. Meanwhile, React handles the complex state management required to render high-density trading dashboards cleanly.

---

## 🧠 Backend Engine Deep Dive

The backend (`/backend`) is not just an API; it is a continuous, self-driving engine. The heart of the system is `main.py`, which runs the `generate_and_broadcast_signals()` infinite loop as a background task.

### 1. Market Data & Regime Detection
- **File**: `api/services/market_data.py` & `api/services/regime_detector.py`
- **How it works**: The system fetches live OHLCV data via `ccxt`. It calculates local deterministic math (RSI, Bollinger Bands, ATR) and evaluates Multi-Timeframe (MTF) trend alignments.
- **The "Why"**: By using local math to classify the "Market Regime" (e.g., *Trending*, *Ranging*, *High Volatility*), we prevent the LLM from hallucinating technical realities. The AI is fed mathematical facts, ensuring strict quantitative grounding.

### 2. The AI Agent & NLP Sentiment
- **File**: `api/services/ai_agent.py`
- **How it works**: Uses LangChain and OpenAI (`gpt-4o-mini`). The agent ingests the calculated regime, volatility state, and live news headlines. It performs NLP sentiment analysis (extracting "Fear & Greed") and outputs a Base Confidence score for a directional bias (BUY/SELL/HOLD).
- **The "Why"**: LLMs are terrible at raw math, but exceptional at unstructured data synthesis (news/sentiment). We offload the sentiment and narrative reasoning to the LLM, but keep the technical math strictly in Python.

### 3. Risk Engine
- **File**: `api/services/risk_engine.py`
- **How it works**: Takes the AI's directional bias and applies strict risk parameters. Calculates dynamic Take Profit (TP) based on Bollinger Band extremes and Stop Loss (SL) based on Average True Range (ATR). It computes the precise Risk/Reward Ratio.
- **The "Why"**: An AI might be right about direction but wrong about timing. The Risk Engine enforces mechanical, emotionless risk management independent of the AI's confidence.

### 4. Adaptive Memory (Reinforcement Learning)
- **File**: `api/services/learning_engine.py` & `api/services/outcome_tracker.py`
- **How it works**: An asynchronous task continually compares the AI's past signals against current live prices. If a past signal hits its TP, it counts as a Win. If it hits SL, it's a Loss. The `learning_engine.py` aggregates this historical Win Rate. If the AI is currently on a losing streak, it *penalizes* (reduces) the AI's live confidence multiplier. If on a winning streak, it boosts it.
- **The "Why"**: Static algorithms break down when market behavior changes. Adaptive Memory ensures the system dynamically self-calibrates its risk appetite based on its actual, empirical recent performance.

### 5. Autonomous Paper Trading
- **File**: `api/services/paper_engine.py`
- **How it works**: Users can open virtual trades. A dedicated background `asyncio` task polls the live price every 3 seconds. If the live price crosses an active trade's SL or TP, the engine autonomously closes the position, calculates Realized PnL, and updates the `VirtualPortfolio` database table.
- **The "Why"**: Provides a totally safe, zero-risk sandbox to validate the AI's signals. Running it as an isolated background loop ensures execution never blocks the main API thread.

### 6. AI Scenario Forecaster
- **File**: `api/services/scenario_agent.py`
- **How it works**: Exposes an endpoint that accepts hypothetical user queries ("What if BTC breaks $70k?"). The agent parses the *live, globally cached market state* and calculates probabilistic continuations (Bullish % vs Bearish %).

---

## 🖥 Frontend Architecture Deep Dive

The frontend (`/frontend`) is built with Next.js, optimizing for extremely dense data visualization.

### 1. The Live Dashboard (`/page.tsx`)
- A WebSocket connection listens to `ws://localhost:8000/ws/signals`. 
- Every time the backend loop completes a cycle, it blasts the JSON payload to the frontend.
- React immediately hydrates the UI, updating the Market Regime widget, NLP Fear/Greed bar, and the TradingView chart.
- **Design Decision**: Removed container max-widths to force a 4-column, full-viewport CSS Grid. This mimics professional software (Bloomberg Terminal) maximizing screen real estate for the chart while pushing dense analytics into an independently scrollable sidebar.

### 2. Paper Trading UI (`/paper/page.tsx`)
- Splits the view into an Execution Terminal (form) and an Active Positions table.
- **Design Decision**: The positions table pings the backend rapidly to reflect autonomous closures by the `paper_engine` in real-time, simulating a real brokerage environment.

### 3. Scenario Forecasting (`/scenarios/page.tsx`)
- A conversational interface that renders structured data (Probability Bars, Invalidation Levels) instead of raw text blocks.
- **Design Decision**: Separated into its own route to provide ample screen space for the dynamic visual elements without cluttering the fast-moving live dashboard.

---

## 🗄 Database Schema (`trading.db`)
Uses **SQLite** with **SQLAlchemy** ORM for frictionless local deployment without requiring complex Docker/Postgres setups.
1. `TradeSignal`: Complete log of every AI prediction, its confidence, and the mathematical state at the time.
2. `SignalOutcome`: The resolved result (Win/Loss) of a `TradeSignal` used by the Adaptive Memory engine.
3. `VirtualPortfolio`: Tracks the user's paper trading balance.
4. `ActivePosition` & `PaperTradeHistory`: Tracks open and closed simulated trades.
5. `TradeJournal`: User-entered emotional tracking and behavioral AI analysis notes.

---

## 🚀 How to Run the System

The application requires two separate processes running concurrently:

1. **Start the Backend**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```
   *Note: Ensure your `.env` file contains `OPENAI_API_KEY=your_key`.*

2. **Start the Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Access**
   Open `http://localhost:3000` in a maximized browser window.
