# Experiment Design: LLM-Optimized Cryptocurrencies

This document operationalizes the 52-week matched-pair study evaluating whether cryptocurrencies optimized for large language model (LLM) accessibility deliver superior risk-adjusted returns. It expands the executive blueprint into concrete implementation steps, data schemas, and governance checkpoints for the research team.

## 1. Hypothesis Architecture

### 1.1 Primary Hypothesis

> **H₁**: Cryptocurrencies with high LLM Optimization Scores (LLOS ≥ 65) will achieve superior Sortino ratios over a 12-month horizon relative to matched controls with LLOS ≤ 35.

### 1.2 Null Hypotheses

- **H₀₁**: No Sortino ratio difference between treatment and control portfolios.
- **H₀₂**: LLOS does not predict returns after controlling for market cap, volatility, Bitcoin beta, sector, and trading volume.
- **H₀₃**: The LLOS effect does not strengthen over time as AI adoption increases.

### 1.3 Theoretical Mechanisms

1. **Information Availability Cascade**: LLMs amplify salient documentation, mirroring availability heuristics.
2. **Algorithmic Herding Amplification**: Shared LLM training data synchronizes AI-driven investment flows.
3. **Market Inefficiency Exploitation**: Crypto inefficiencies convert information transparency into alpha.
4. **Narrative Virality Advantage**: Simple narratives spread faster and are reinforced by LLM outputs.
5. **Self-Fulfilling Coordination**: LLM recommendations create demand loops via user adoption feedback.

## 2. LLM Optimization Score (LLOS)

### 2.1 Composite Score Definition

\[
\text{LLOS} = 0.25\times\text{WP} + 0.25\times\text{LLM} + 0.20\times\text{DOC} + 0.15\times\text{NAR} + 0.10\times\text{SOC} + 0.05\times\text{DEV}
\]

Each component is normalized to a 0–100 scale. LLOS calculations are stored with timestamps to enable time-series analysis.

### 2.2 Component Measurement

- **Web Presence (WP)**: Aggregates Wikipedia coverage, domain authority, SERP visibility, backlink quality, and indexed pages.
- **LLM Recommendation (LLM)**: Direct query-based assessment across GPT-4, Claude 3.5, Gemini Pro, and Llama 3.1 using 10 standardized prompts.
- **Documentation Quality (DOC)**: Evaluates completeness, readability, accessibility, recency, and depth of technical materials.
- **Narrative Simplicity (NAR)**: Scores consistency, simplicity, and uniqueness of value propositions using NLP similarity metrics.
- **Social/Community (SOC)**: Uses Reddit, Twitter, GitHub, Medium, and Stack Overflow activity to quantify community-generated text.
- **Developer Activity (DEV)**: Measures commits, contributors, issue response time, and repository engagement.

### 2.3 Validation Protocols

- **Construct Validity**: Correlate LLOS with human expert familiarity ratings.
- **Predictive Validity**: Test out-of-sample prompt responses for detail and accuracy.
- **Inter-Rater Reliability**: Dual scoring on a 50-asset subset (target Cronbach's α ≥ 0.85).
- **Temporal Stability**: Quarterly rescoring with lagged performance tests.

## 3. Sample Selection & Matching

### 3.1 Universe Criteria

- Listed on ≥3 major exchanges.
- Market cap > $10M and operational for ≥6 months.
- English documentation available.
- Exclude stablecoins, wrapped assets, and exchange tokens.

### 3.2 Stratified Sampling Targets

| Tier | Market Cap Rank | Inclusion Rate | Expected Count |
| ---- | ---------------- | -------------- | -------------- |
| Large-cap | 1–20 | 100% | 20 |
| Mid-cap | 21–100 | 20% | 16 |
| Small-cap | 101–300 | 10% | 20 |
| Micro-cap | >300 (>$10M) | 5% | 10 |

### 3.3 Propensity Score Matching

1. Estimate high-LLOS propensity using logit model with market cap, volatility, Bitcoin beta, volume, age, sector.
2. Match within 0.1 SD caliper; enforce sector and exchange presence parity.
3. Validate standardized mean differences <0.1 and visually inspect pairs.
4. Maintain reserve list of alternates for attrition replacement.

## 4. Data Infrastructure

### 4.1 Storage Architecture

- **PostgreSQL**: Time-series market data, trades, portfolio weights.
- **MongoDB**: Raw LLM responses and metadata.
- **S3-compatible Object Store**: Document snapshots, model artifacts, audit logs.

### 4.2 Data Sources & Frequencies

| Stream | Source | Frequency | Notes |
| ------ | ------ | --------- | ----- |
| Prices & Volume | CoinGecko Pro, exchange APIs | Hourly | Redundant feeds, reconciliation checks |
| LLM Responses | OpenAI, Anthropic, Google, Meta APIs | Baseline + Monthly | 200 baseline queries; 50 monthly |
| Documentation | Custom scrapers + API data | Quarterly | Manual QA on 20% sample |
| Social Metrics | Reddit, Twitter, GitHub APIs | Weekly | Log-scaled normalization |
| Transaction Costs | Simulated orders | Weekly | Calibrate slippage per tier |

### 4.3 Data Quality Controls

- Flag >100% hourly price moves and >10× volume spikes.
- Cross-verify prices across ≥3 exchanges; reject divergence >2%.
- Track delistings and failure reasons to mitigate survivorship bias.

## 5. LLM Testing Protocol

### 5.1 Prompt Suite

Ten neutral templates covering explanations, rankings, comparisons, tokenomics, risks, and roadmap evaluation. Each cryptocurrency receives 200 baseline queries (4 models × 10 prompts × 5 iterations) and 50 monthly follow-up queries.

### 5.2 Response Scoring

- **Mention Frequency**
- **Detail Density** (entity counts, numerical facts)
- **Ranking Position**
- **Sentiment Balance**
- **Recommendation Strength** (manual coding)
- **Inter-Model Consistency**

### 5.3 Standardization Parameters

- Temperature 0.3, max tokens 1,000, top-p 1.0.
- Randomize cryptocurrency order to avoid position bias.
- Cache responses; implement exponential backoff on API errors.

### 5.4 Blinding Measures

- Operational team blinded to treatment assignment.
- LLM prompts avoid revealing research context.
- Store anonymized asset IDs during analysis phase.

## 6. Portfolio Construction

### 6.1 Baseline Strategy

- 60 treatment assets (LLOS ≥ 65) and 60 control assets (LLOS ≤ 35).
- Equal-weight portfolios rebalanced weekly (Sunday 23:59 UTC).
- Replacement protocol triggers for delistings or -40% stop-loss breaches.

### 6.2 Transaction Cost Assumptions

- Fees: 0.15% per trade.
- Slippage: 0.15% large-cap, 0.30% mid-cap, 0.50% small/micro.
- Total round-trip cost: 0.45–0.80% depending on tier.

### 6.3 Risk Controls

- Portfolio max drawdown trigger at -30%; initiate review if breached.
- Exchange diversification across Binance, Coinbase, Kraken.
- Position cap ≤5% of asset daily volume.

## 7. Statistical Analysis Plan

### 7.1 Primary Metric

- **Sortino Ratio** difference between treatment and control portfolios.
- Target difference ≥0.3 with p < 0.05 (paired t-test or Wilcoxon as fallback).

### 7.2 Secondary Metrics

- Total return, alpha vs. market-cap benchmark, max drawdown, Calmar ratio, weekly win rate, downside capture, positive month frequency.

### 7.3 Regression Specifications

1. **Baseline OLS** with clustered standard errors.
2. **Time Interaction Model** assessing effect growth.
3. **Non-linear Model** testing threshold effects.

### 7.4 Robustness & Sensitivity

- Subsample analyses (market-cap tiers, sectors, regimes).
- Alternative LLOS thresholds and component weights.
- Different rebalancing frequencies and weighting schemes.
- Placebo and permutation tests.
- K-fold cross-validation and hold-out evaluation.

## 8. Implementation Roadmap

| Phase | Weeks | Capital | Goals |
| ----- | ----- | ------- | ----- |
| Phase 1: Infrastructure & Paper Trading | 1–8 | $0 | Deploy pipelines, compute LLOS, validate matching |
| Phase 2: Pilot Deployment | 9–20 | $25k | Validate live execution, refine cost estimates |
| Phase 3: Full Study | 21–52 | $200k | Execute protocol, collect full dataset |
| Phase 4: Optional Extension | 53–78 | $200k | Test persistence and regime effects |

## 9. Governance & Ethics

- Pre-register on OSF and pursue registered report submission.
- Commit to publishing regardless of outcome.
- Require researchers to divest personal holdings in sample assets or use blind trusts.
- Monitor for strategic documentation manipulation and LLM prompt injection attempts.

## 10. Deliverables & Checklists

- Weekly: Portfolio report, risk dashboard, execution logs.
- Monthly: LLM re-testing summary, data quality audit.
- Quarterly: Documentation rescoring, governance review.
- Post-study: Full dataset, replication code, manuscript, practitioner brief.

## 11. Appendices

- **A. Budget Summary**: Personnel ($170k), data/LLM APIs ($31.2k), infrastructure ($2.4k), trading costs ($8k), capital ($200k).
- **B. Sample Size**: 60 matched pairs deliver ≥85% power for effect size d = 0.4.
- **C. Pre-Registration Template**: Included in `docs/preregistration_template.md`.

