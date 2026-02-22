# LLM Optimization Agent - Refactor Plan

## Overview

Complete refactor from single-mode valuation bot to multi-mode LLM Optimization Agent with 4 distinct modes.

---

## Architecture

### New File Structure

```
src/llm_asset_oracle/
├── models/
│   └── registry.py          # NEW: 18 curated models with vision flags
├── engine/
│   └── query_engine.py      # NEW: Core LLM query engine (text + vision)
├── modes/
│   ├── __init__.py
│   ├── base.py              # NEW: Base mode class
│   ├── bullish_bearish.py   # NEW: Mode A
│   ├── multi_valuation.py   # NEW: Mode B
│   ├── solo_valuation.py    # NEW: Mode C
│   └── technical_analyst.py # NEW: Mode D
├── charts/
│   ├── __init__.py
│   ├── pie_chart.py         # NEW: For Mode A
│   ├── bar_chart.py         # NEW: For Modes B, C, D
│   └── utils.py             # Shared chart utilities
└── discord_bot/
    └── multi_mode_bot.py    # NEW: Refactored Discord bot
```

---

## Component Details

### 1. Model Registry (`models/registry.py`)

```python
@dataclass
class LLMModel:
    id: str           # OpenRouter ID
    name: str         # Display name
    provider: str     # Company
    supports_vision: bool

ALL_MODELS = [...]     # 18 models
VISION_MODELS = [...]  # 15 models (filtered)
```

**Models (18 total):**
| # | Name | ID | Vision |
|---|------|-----|--------|
| 1 | ChatGPT 5.2 | openai/gpt-5.2-chat | Yes |
| 2 | ChatGPT 5.2 Pro | openai/gpt-5.2-pro | Yes |
| 3 | Claude Opus 4.6 | anthropic/claude-opus-4.6 | Yes |
| 4 | Claude Opus 4.5 | anthropic/claude-opus-4.5 | Yes |
| 5 | Claude Sonnet 4.5 | anthropic/claude-sonnet-4.5 | Yes |
| 6 | Claude Sonnet 4.6 | anthropic/claude-sonnet-4.6 | Yes |
| 7 | Gemini 3 Flash Preview | google/gemini-3-flash-preview | Yes |
| 8 | Gemini 3 Pro Preview | google/gemini-3-pro-preview | Yes |
| 9 | Gemini 3.1 Pro Preview | google/gemini-3.1-pro-preview | Yes |
| 10 | Grok 4.1 Fast | x-ai/grok-4.1-fast | Yes |
| 11 | Grok 4 | x-ai/grok-4 | Yes |
| 12 | Grok 4 Fast | x-ai/grok-4-fast | Yes |
| 13 | Kimi K2.5 | moonshotai/kimi-k2.5 | Yes |
| 14 | GLM 5 | z-ai/glm-5 | No |
| 15 | Deepseek v3.2 | deepseek/deepseek-v3.2 | No |
| 16 | Qwen 3.5 | qwen/qwen3.5-397b-a17b | Yes |
| 17 | Qwen 3.5 Plus | qwen/qwen3.5-plus-02-15 | Yes |
| 18 | Qwen 3 Max Thinking | qwen/qwen3-max-thinking | No |

---

### 2. Query Engine (`engine/query_engine.py`)

Core async engine for querying OpenRouter:

```python
class QueryEngine:
    async def query_text(model_id, prompt) -> str
    async def query_vision(model_id, prompt, image_base64) -> str
    async def query_multiple(model_ids, prompt) -> list[Response]
    async def query_same_model(model_id, prompt, runs=5) -> list[Response]
```

---

### 3. Mode Implementations

#### Mode A: Bullish or Bearish (`modes/bullish_bearish.py`)

**Input:**
- Asset description (text)
- Time horizon (dropdown: 1 month, 3 months, 6 months, 1 year, 2 years)
- Models: All 18 (auto-selected)

**Process:**
1. Build prompt: "Given [asset description], are you BULLISH or BEARISH on this asset over [time horizon]? Answer only BULLISH or BEARISH."
2. Query all models
3. Parse responses for BULLISH/BEARISH
4. Count votes

**Output:**
- Pie chart: Bullish % vs Bearish %
- Model breakdown list

---

#### Mode B: Multi-Valuation (`modes/multi_valuation.py`)

**Input:**
- Asset description (text)
- Target quarter/year (e.g., "Q3 2026")
- Model selection (up to 8 from 18)

**Process:**
1. Build prompt: "What is your best-estimate market cap for [asset] by [target time]? End with VERDICT: $[X]B"
2. Query selected models
3. Parse market cap values

**Output:**
- Bar chart: Each model's estimate
- Mean/median lines marked
- Statistics summary

---

#### Mode C: Solo-Valuation (`modes/solo_valuation.py`)

**Input:**
- Asset description (text)
- Target quarter/year
- Single model selection (from 18)
- Number of runs (1-5)

**Process:**
1. Build same prompt as Mode B
2. Query same model N times
3. Collect all responses

**Output:**
- Bar chart: Each run's estimate
- Mean/median lines marked
- Consistency analysis (std dev, range)

---

#### Mode D: Technical Analyst (`modes/technical_analyst.py`)

**Input:**
- Candlestick chart screenshot (image upload)
- Timeframe (e.g., "4H", "1D", "1W")
- Model selection (up to 8 from 15 vision-capable)

**Process:**
1. Build prompt: "Analyze this [timeframe] candlestick chart. Based purely on technical analysis, would you go LONG or SHORT? Answer only LONG or SHORT."
2. Query vision models with image
3. Parse LONG/SHORT responses

**Output:**
- Bar chart: Long count vs Short count
- Model breakdown list

---

### 4. Discord Bot (`discord_bot/multi_mode_bot.py`)

**Flow:**

```
/analyze → Mode Selection Dropdown
    ↓
Mode A selected → Time Horizon Dropdown → Asset Modal → Results
Mode B selected → Model Multi-Select (max 8) → Asset + Target Modal → Results
Mode C selected → Model Single-Select → Runs Dropdown → Asset + Target Modal → Results
Mode D selected → Vision Model Multi-Select (max 8) → Timeframe Dropdown → Image Upload Prompt → Results
```

**UI Components:**

1. **Mode Select** (discord.ui.Select)
   - Options: A, B, C, D with descriptions

2. **Model Select** (discord.ui.Select with max_values)
   - Mode A: Skip (uses all)
   - Mode B: Multi-select, max 8
   - Mode C: Single-select
   - Mode D: Multi-select, max 8 (vision only)

3. **Modals** (discord.ui.Modal)
   - Asset description field
   - Target time field (for B, C)

4. **Image Upload** (Mode D)
   - Prompt user to attach image
   - Wait for message with attachment

---

### 5. Charts

#### Pie Chart (`charts/pie_chart.py`)
- For Mode A
- Two slices: Bullish (green) / Bearish (red)
- Percentages labeled

#### Bar Chart (`charts/bar_chart.py`)
- For Modes B, C, D
- Horizontal bars for each model/run
- Mean/median lines
- Color coding

---

## Implementation Order

1. **Phase 1: Foundation**
   - [ ] Create `models/registry.py` with 18 models
   - [ ] Create `engine/query_engine.py` with text + vision support

2. **Phase 2: Modes**
   - [ ] Create `modes/base.py` base class
   - [ ] Implement Mode A (Bullish/Bearish)
   - [ ] Implement Mode B (Multi-Valuation)
   - [ ] Implement Mode C (Solo-Valuation)
   - [ ] Implement Mode D (Technical Analyst)

3. **Phase 3: Charts**
   - [ ] Create pie chart generator
   - [ ] Create bar chart generator (reuse existing where possible)

4. **Phase 4: Discord Bot**
   - [ ] Create new `multi_mode_bot.py`
   - [ ] Implement mode selection flow
   - [ ] Implement model selection
   - [ ] Implement modals for each mode
   - [ ] Implement image upload handling for Mode D

5. **Phase 5: Testing & Polish**
   - [ ] Test each mode end-to-end
   - [ ] Error handling
   - [ ] Clean up old code

---

## Notes

- Keep existing valuation code for reference but build new clean implementation
- Discord select menus max 25 options (18 models fits fine)
- Image handling: Convert Discord attachment to base64 for OpenRouter
- PFT fee integration: Stub for now, add hooks later
