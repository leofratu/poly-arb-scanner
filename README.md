# Poly-Arb-Scanner 📈

A terminal-based CLI tool that scans Polymarket for risk-adjusted arbitrage opportunities against traditional finance (TradFi) treasury benchmark yields. 

## Features
- **Live Polymarket Gamma API Integration:** Fetches active binary options, outcome prices, and order book depth.
- **TradFi Yield Interpolation:** Connects to Yahoo Finance (`^IRX`, `^FVX`, `^TNX`) to pull live risk-free treasury yields and dynamically interpolates rates based on days to maturity.
- **Arbitrage Engine:** Calculates the annualized risk-adjusted yield for favorite outcomes and flags spreads exceeding a user-defined threshold.
- **AI Chat Assistant:** Query identified arbitrage opportunities using natural language via OpenRouter's free models.
- **Rich CLI UI:** OpenCode-inspired terminal aesthetics with colored tables, progress bars, and data exports (CSV/JSON).

## Installation
Ensure you have `uv` installed, then run:

```bash
uv sync
```

## Usage

### 1. Scan for Opportunities
Scan the market for spreads greater than 5%:
```bash
uv run python main.py scan --threshold 5.0
```

Export results to CSV or JSON:
```bash
uv run python main.py scan --threshold 3.0 --export csv
uv run python main.py scan --export json
```

### 2. AI Market Analyst
Chat with the AI to filter, query, and analyze the live arbitrage data:
```bash
# Requires an OpenRouter API key (free models supported)
export OPENROUTER_API_KEY="sk-or-v1-..."
uv run python main.py chat
```

## Architecture
- **`main.py`**: CLI routing via `typer` and terminal UI via `rich`.
- **`polymarket.py`**: Handles API requests to the Polymarket Gamma endpoint.
- **`tradfi.py`**: Manages the risk-free rate interpolation using `yfinance`.
- **`arbitrage.py`**: Contains the core logic for spread calculation and threshold filtering.
