# Pre-Registration Template

Complete this template on the Open Science Framework (OSF) prior to commencing data collection. Update the `Version` field with the Git commit hash corresponding to the locked protocol.

## Study Overview

- **Title**: LLM-Optimized Cryptocurrencies: Testing AI Accessibility as a Return Driver
- **Investigators**: _Names, affiliations, contact information_
- **Version**: _Git commit hash_
- **Date**: _YYYY-MM-DD_

## Hypotheses

1. **Primary Hypothesis (H₁)**: Treatment portfolio (LLOS ≥ 65) exhibits higher Sortino ratio than control portfolio (LLOS ≤ 35).
2. **Secondary Hypotheses**:
   - H₂: LLOS predicts weekly returns after controls.
   - H₃: LLOS effect strengthens over time with AI adoption proxies.

## Outcomes

- **Primary Outcome**: Sortino ratio differential over 52-week horizon.
- **Secondary Outcomes**: As specified in `docs/statistical_analysis_plan.md` Section 1.2.

## Sample & Design

- **Universe Criteria**: Market cap > $10M, ≥3 exchanges, ≥6 months history, English documentation, excludes stablecoins/wrapped/exchange tokens.
- **Sample Size**: 60 matched pairs (treatment and control).
- **Sampling Procedure**: Stratified by market cap tier; propensity score matching with 0.1 SD caliper.
- **Assignment Rule**: Treatment if LLOS ≥ 65; Control if LLOS ≤ 35.

## Data Collection

- **Price Data**: CoinGecko Pro API + exchange redundancies.
- **LLM Data**: GPT-4, Claude 3.5 Sonnet, Gemini Pro, Llama 3.1 via standardized prompts.
- **Documentation Data**: Automated scraping with quarterly manual QA.
- **Social/Dev Data**: Reddit, Twitter, GitHub APIs.

## Analysis Plan

- **Primary Test**: Paired t-test (or Wilcoxon) on Sortino ratio differences.
- **Regression Models**: Baseline OLS, time interaction, quadratic specification.
- **Multiple Testing**: Benjamini-Hochberg FDR at 5%.
- **Robustness**: Subsamples, alternative thresholds, placebo tests, hold-out validation.

## Deviations Policy

- Document deviations within 24 hours in governance log.
- Material deviations require committee approval.

## Data Sharing

- Release anonymized dataset and code within 60 days of final analysis.
- Embargo period for public release (if any): _Specify_ (max 18 months recommended).

## Conflicts of Interest

- Declare personal holdings in sample cryptocurrencies.
- Outline mitigation steps (e.g., blind trusts, divestiture).

## Signatures

- Principal Investigator: ____________________ Date: _______
- Statistician: _____________________________ Date: _______
- Governance Chair: ________________________ Date: _______

