
TRADING BOT PROJECT CONTEXT (IMPORTANT - READ FIRST)

You are continuing a trading bot project. DO NOT change architecture unless explicitly instructed.

CURRENT STATE:
- Using Finnhub FREE tier ONLY (NO TwelveData, NO yfinance)
- Working endpoint: /top
- Strategy: simplified daily top movers
- Data source: Finnhub /quote ONLY (no restricted endpoints)
- No background threads
- No scraping
- No YahooFinance (DO NOT suggest it)

ARCHITECTURE:
- FastAPI app
- On-demand execution (no caching system)
- Universe: fixed list of large-cap stocks
- Strategy:
    1. Fetch quotes
    2. Compute % change
    3. Rank top 5 movers (absolute change)
    4. Score = change (for now)

GOAL:
- Keep system SIMPLE and FREE
- Focus on STRATEGY DEVELOPMENT
- Later: scale up universe + complexity

DO NOT:
- Reintroduce TwelveData
- Reintroduce yfinance
- Add background workers
- Add heavy infra

NEXT STEPS (for new agent):
- Add trading rules (buy/sell logic)
- Add filtering (only positive momentum)
- Add basic backtesting logic

NOTES:
- User explicitly wants minimal friction
- Files are deployed on Render
- System is already LIVE and working

Proceed from here WITHOUT regression.
