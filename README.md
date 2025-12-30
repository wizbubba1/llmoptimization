# 🔮 LLM Asset Oracle

**A scientific trading tool that queries 15-20 AI models with factual-only prompts and aggregates their consensus to identify which assets the AI community rates most favorably.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## The Concept

What if you could ask every major AI model the same question about an asset and see where they agree?

LLM Asset Oracle does exactly that. It sends **factual-only prompts** (no leading language or bias) to 15-20 diverse AI models through [OpenRouter](https://openrouter.ai), collects their independent BUY/SELL votes with confidence scores, and aggregates them using statistical consensus methods.

**The result?** A heatmap showing which direction each AI leans, a consensus strength score, and a final grade from A+ to F.

## Key Features

- **🤖 20 AI Models**: GPT-4, Claude, Gemini, Llama, Mistral, Qwen, DeepSeek, and more
- **📊 Factual-Only Prompts**: No bias-inducing language, just objective facts
- **🔢 Simple Outputs**: BUY/SELL + Confidence (1-100) + One-line view
- **📈 Statistical Consensus**: Weighted voting, agreement metrics, confidence intervals
- **🎨 Visual Heatmaps**: See exactly how each model voted
- **💬 Discord Bot**: Full slash command integration
- **⚡ OpenRouter Integration**: Single API key for all models

## Quick Start

### 1. Get an OpenRouter API Key

Sign up at [openrouter.ai](https://openrouter.ai) and get your API key. This single key gives you access to 100+ models.

### 2. Install

```bash
git clone https://github.com/yourusername/llm-asset-oracle.git
cd llm-asset-oracle
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### 4. Run

```bash
# Analyze an asset
python -m llm_asset_oracle.cli_v2 analyze BTC

# Show model heatmap
python -m llm_asset_oracle.cli_v2 analyze BTC --heatmap

# Compare assets
python -m llm_asset_oracle.cli_v2 compare BTC ETH

# Rank multiple assets
python -m llm_asset_oracle.cli_v2 rank BTC,ETH,SOL,AVAX,LINK

# Run Discord bot
python -m llm_asset_oracle.cli_v2 bot
```

## Example Output

```
┌────────────────────────────────────────────────────┐
│ 🔮 Multi-Model Consensus                           │
│ BTC - BUY                                          │
│ Grade: A (78/100)                                  │
└────────────────────────────────────────────────────┘

Model Votes:
  🟢 BUY: 12 (80%)
  🔴 SELL: 2 (13%)
  ⚪ NEUTRAL: 1 (7%)

Metrics:
  Weighted Score: +42.3
  Consensus Strength: 80%
  Avg Confidence: 71%

By Provider:
  OpenAI: 🟢3 🔴0 ⚪0
  Anthropic: 🟢2 🔴1 ⚪0
  Google: 🟢2 🔴0 ⚪0
  Meta: 🟢3 🔴0 ⚪1
```

### Heatmap

```
MODEL HEATMAP
──────────────────────────────────────────────────
▸ OpenAI
  GPT-4 Turbo        [██████████] BUY   85% 🟢
  GPT-4o             [████████░░] BUY   72% 🟢
  GPT-4o Mini        [███████░░░] BUY   68% 🟢

▸ Anthropic
  Claude 3.5 Sonnet  [██████████] BUY   90% 🟢
  Claude 3 Opus      [░░░░░░████] SELL  65% 🔴

▸ Google
  Gemini Pro 1.5     [████████░░] BUY   75% 🟢
  Gemini Flash 1.5   [██████░░░░] BUY   60% 🟢

▸ Meta
  Llama 3.1 405B     [███████░░░] BUY   70% 🟢
  Llama 3.1 70B      [░░░░░│░░░░] NEUT  50% ⚪
```

## Methodology

### 1. Factual-Only Prompts

We send **only objective facts** to each model:

```
Asset Profile:
- Symbol: BTC
- Name: Bitcoin
- Type: Cryptocurrency
- Founded: 2009
- Consensus: Proof of Work
- Max Supply: 21,000,000
- Current Price: $67,432
- 24h Change: +2.34%

Based solely on these facts, provide your assessment:
DIRECTION: [BUY or SELL - one word only]
CONFIDENCE: [1-100]
VIEW: [One sentence]
```

**Why?** By avoiding leading questions like "What do you think about..." or "Is this a good investment?", we get the model's genuine assessment rather than an echo of perceived expectations.

### 2. Multi-Model Voting

Each model independently returns:
- **DIRECTION**: BUY or SELL (no maybes)
- **CONFIDENCE**: 1-100 (how sure they are)
- **VIEW**: One sentence of reasoning

### 3. Consensus Math

**Weighted Score** (-100 to +100):
```
Σ(direction × confidence) / n
```
Where direction is +1 for BUY, -1 for SELL.

**Consensus Strength** (0-100%):
```
(max_same_direction / total_votes) × 100
```

**Signal Clarity**:
```
consensus_strength × avg_confidence / 100
```

### 4. Final Grade

| Grade | Meaning |
|-------|---------|
| A+ | Very strong consensus + direction + confidence |
| A | Strong signal |
| B | Moderate signal |
| C | Weak/mixed signal |
| D | Very weak signal |
| F | No clear consensus |

## Active Models (20)

| Provider | Models |
|----------|--------|
| OpenAI | GPT-4 Turbo, GPT-4o, GPT-4o Mini |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku |
| Google | Gemini Pro 1.5, Gemini Flash 1.5 |
| Meta | Llama 3.1 405B, Llama 3.1 70B, Llama 3.1 8B |
| Mistral | Mistral Large, Mixtral 8x22B, Mistral Nemo |
| Cohere | Command R+, Command R |
| Alibaba | Qwen 2.5 72B |
| DeepSeek | DeepSeek V2.5 |
| Perplexity | Sonar Large (Online) |
| Nous Research | Hermes 3 405B |

## Discord Commands

| Command | Description |
|---------|-------------|
| `/analyze <symbol>` | Full multi-model analysis |
| `/quick <symbol>` | Quick sentiment check |
| `/heatmap <symbol>` | Visual model breakdown |
| `/compare <a> <b>` | Compare two assets |
| `/rank <a,b,c>` | Rank multiple assets |
| `/top_crypto` | Top crypto picks |
| `/models` | List active AI models |
| `/methodology` | How scoring works |

## Cost

Using OpenRouter with 15 models typically costs:
- **~$0.01-0.02** per analysis (budget mode)
- **~$0.05-0.10** per analysis (all models)

The actual cost depends on which models are queried. Budget mode prioritizes cheaper models like GPT-4o Mini, Claude Haiku, and Gemini Flash.

## Architecture

```
src/llm_asset_oracle/
├── core/
│   └── multi_model_oracle.py  # Main oracle engine
├── llm/
│   └── openrouter.py          # OpenRouter client + 20 model configs
├── analysis/
│   ├── factual_prompts.py     # Bias-free prompt builder
│   └── consensus_math.py      # Statistical aggregation
├── data/
│   ├── assets.py              # Asset fact database
│   └── fetchers.py            # Market data (CoinGecko, Yahoo)
└── discord_bot/
    └── new_bot.py             # Discord integration
```

## Disclaimer

⚠️ **THIS IS NOT FINANCIAL ADVICE**

- AI models can be wrong, biased, or hallucinate
- Past consensus does not predict future performance
- This tool is for entertainment and educational purposes
- Always do your own research (DYOR)
- Never invest more than you can afford to lose

The creators are not responsible for any financial decisions made based on this tool.

## License

MIT License - see [LICENSE](LICENSE)

---

*Built with 🔮 by exploring what happens when you ask 20 AIs the same question*
