# 🔮 LLM Asset Oracle

**A scientific trading tool that aggregates sentiment analysis from multiple Large Language Models to identify assets with the highest AI consensus ratings.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

LLM Asset Oracle queries multiple AI models (GPT-4, Claude, Gemini, Llama, Mistral) with standardized prompts about investment assets and calculates a consensus score. Assets that are positively rated across diverse AI systems are considered "LLM-optimized."

### Key Features

- **Multi-Model Analysis**: Query 5+ different LLM providers simultaneously
- **Scientific Scoring**: Statistical aggregation with confidence intervals
- **LLM Optimization Score (LOS)**: 0-100 score combining ratings and consensus
- **Discord Bot**: Full-featured bot with slash commands
- **CLI Interface**: Command-line tool for quick analysis
- **Real-time Data**: Integration with CoinGecko and Yahoo Finance
- **Caching**: SQLite-based caching for fast repeat queries

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-asset-oracle.git
cd llm-asset-oracle

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Add your API keys to `.env`:
```env
# At least one LLM provider is required
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
GOOGLE_API_KEY=your-google-key-here

# For Discord bot
DISCORD_BOT_TOKEN=your-bot-token
```

### Usage

#### Command Line

```bash
# Analyze a single asset
llm-oracle analyze BTC
llm-oracle analyze AAPL --detailed

# Compare two assets
llm-oracle compare BTC ETH

# Get top-rated assets
llm-oracle top --category crypto --limit 10

# Check status
llm-oracle status

# Run Discord bot
llm-oracle bot
```

#### Python API

```python
import asyncio
from llm_asset_oracle import LLMAssetOracle

async def main():
    oracle = LLMAssetOracle()
    await oracle.initialize()

    # Analyze an asset
    result = await oracle.analyze("BTC")
    print(f"LOS Score: {result.consensus.los_score}")
    print(f"Recommendation: {result.consensus.recommendation}")

    # Compare assets
    comparison = await oracle.compare("BTC", "ETH")
    print(f"Preferred: {comparison['preferred']}")

asyncio.run(main())
```

#### Discord Bot Commands

| Command | Description |
|---------|-------------|
| `/analyze <symbol>` | Full multi-model analysis |
| `/quick <symbol>` | Quick sentiment check |
| `/compare <a> <b>` | Compare two assets |
| `/top [category]` | Top-rated assets |
| `/picks [category]` | High-conviction picks |
| `/methodology` | Scoring explanation |
| `/status` | Bot status |
| `/help` | Help information |

## Methodology

### LLM Optimization Score (LOS)

The LOS is a 0-100 score that measures how positively and consistently an asset is rated across multiple AI models.

**Formula:**
```
LOS = (normalized_mean_score) × (consensus_multiplier)
```

**Components:**
- **Overall Rating** (25%): General investment attractiveness
- **Long-term Outlook** (15%): 1+ year perspective
- **Medium-term Outlook** (15%): 1-6 month perspective
- **Short-term Outlook** (10%): 1-30 day perspective
- **Fundamentals** (10%): Business/project strength
- **Momentum** (10%): Technical/price momentum
- **Bullish Sentiment** (10%): Overall bullishness
- **Market Sentiment** (5%): Current market feeling
- **Risk Adjustment**: Penalty for high-risk assets

### Consensus Strength

Measures model agreement using coefficient of variation:
- **80-100%**: Very High Consensus
- **60-80%**: High Consensus
- **40-60%**: Moderate Consensus
- **<40%**: Low/No Consensus

### Rating Scale

| LOS Score | Recommendation |
|-----------|----------------|
| 80-100 | STRONG BUY |
| 65-80 | BUY |
| 50-65 | HOLD |
| 35-50 | SELL |
| 0-35 | STRONG SELL |

## Supported LLM Providers

| Provider | Models | API Key Env Variable |
|----------|--------|---------------------|
| OpenAI | GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5, Claude 3 | `ANTHROPIC_API_KEY` |
| Google | Gemini Pro, Gemini Flash | `GOOGLE_API_KEY` |
| Together AI | Llama 3, Mixtral | `TOGETHER_API_KEY` |
| Mistral | Mistral Large, Medium | `MISTRAL_API_KEY` |

## Supported Assets

### Cryptocurrencies
BTC, ETH, SOL, XRP, ADA, DOGE, DOT, AVAX, LINK, MATIC, UNI, ATOM, LTC, NEAR, ARB

### Stocks
AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, BRK.B, JPM, V, JNJ, WMT, XOM, AMD, DIS

### ETFs
SPY, QQQ, VTI, IWM, GLD

*Custom symbols are also supported - the system will attempt to fetch data and analyze any valid ticker.*

## Architecture

```
src/llm_asset_oracle/
├── core/
│   ├── config.py      # Settings management
│   ├── models.py      # Data models (Asset, ConsensusScore, etc.)
│   └── oracle.py      # Main Oracle engine
├── llm/
│   ├── base.py        # LLM provider base class
│   ├── providers.py   # Provider implementations
│   └── factory.py     # Provider factory
├── analysis/
│   ├── prompts.py     # Standardized prompt templates
│   ├── scoring.py     # Consensus calculation
│   └── insights.py    # Insight extraction
├── data/
│   ├── assets.py      # Pre-defined asset lists
│   ├── fetchers.py    # Market data fetchers
│   └── cache.py       # SQLite caching
├── discord_bot/
│   └── bot.py         # Discord bot implementation
└── cli.py             # Command-line interface
```

## Configuration Options

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `ENABLED_PROVIDERS` | Comma-separated list of providers | `openai,anthropic,google` |
| `CONSENSUS_MODEL_COUNT` | Number of models to query | `3` |
| `CACHE_TTL_SECONDS` | How long to cache responses | `3600` |
| `DATABASE_PATH` | SQLite database location | `./data/llm_oracle.db` |
| `RATE_LIMIT_RPM` | Rate limit per provider | `20` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Type checking
mypy src/
```

## Disclaimer

⚠️ **This tool is for informational and entertainment purposes only.**

- This is NOT financial advice
- AI models can be wrong and biased
- Past ratings do not predict future performance
- Always do your own research (DYOR)
- Consult qualified financial advisors
- Never invest more than you can afford to lose

The creators and contributors of this tool are not responsible for any financial decisions made based on its output.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## Acknowledgments

- OpenAI, Anthropic, Google, Meta, and Mistral for their LLM APIs
- CoinGecko for cryptocurrency data
- Yahoo Finance for stock data
- The open-source community

---

*Built with 🔮 by the LLM Asset Oracle Team*
