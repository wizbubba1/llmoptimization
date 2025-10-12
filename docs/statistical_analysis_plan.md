# Statistical Analysis Plan (SAP)

This Statistical Analysis Plan governs all inferential work for the LLM-optimized cryptocurrency experiment. It must be approved prior to data collection and deviations must be logged in the governance register.

## 1. Outcomes

### 1.1 Primary Outcome

- **Sortino Ratio Differential**: Difference between treatment and control portfolio Sortino ratios computed over the 52-week window using weekly returns and a 4% annual target rate.

### 1.2 Secondary Outcomes

1. **Total Return Differential**
2. **Annualized Alpha** vs. market-cap-weighted crypto benchmark
3. **Maximum Drawdown Differential**
4. **Calmar Ratio Differential**
5. **Weekly Win Rate** (treatment outperforming control)
6. **Downside Capture Ratio** relative to benchmark drawdowns
7. **Positive Month Frequency** differential

## 2. Data Preparation

- Weekly returns computed from Sunday 23:59 UTC NAV snapshots.
- Missing prices imputed using last observation carried forward for ≤3 days; otherwise mark week as missing and document.
- Winsorize weekly returns at 1st and 99th percentiles; record pre-/post-winsorized summaries.
- Align treatment/control portfolios at pair level to maintain matched design.

## 3. Primary Analysis

- Use paired t-test on Sortino ratio differences across 60 pairs.
- Verify normality via Shapiro-Wilk; if p < 0.05, switch to Wilcoxon signed-rank test.
- Report effect size as Cohen’s d with 95% bootstrap CI (10,000 resamples).
- Provide confidence intervals for Sortino ratios using block bootstrap (block length = 4 weeks).

## 4. Regression Models

### 4.1 Baseline Panel Regression

\[
R_{i,t} = \alpha + \beta_1 \text{LLOS}_i + \beta_2 \log(MCap_{i,t}) + \beta_3 Vol_{i,t} + \beta_4 \beta^{BTC}_{i,t} + \beta_5 Volume_{i,t} + \gamma_s + \delta_t + \epsilon_{i,t}
\]

- Cluster standard errors by asset.
- Include sector fixed effects (\(\gamma_s\)) and week fixed effects (\(\delta_t\)).

### 4.2 Time-Varying Effect Model

Add interaction term \(\beta_6 (\text{LLOS}_i \times Time_t)\) where Time is weeks since start (0–51). Significant positive coefficient indicates strengthening effect.

### 4.3 Non-Linear Model

Include quadratic term \(\text{LLOS}_i^2\) to test for thresholds.

## 5. Multiple Comparison Control

- Use Benjamini-Hochberg False Discovery Rate (FDR) at 5% across secondary outcomes.
- Report unadjusted and adjusted p-values.

## 6. Robustness Checks

1. **Subsamples**: Large-cap only, mid/small-cap, sector-based splits.
2. **Alternative LLOS thresholds**: 70/30, 75/25, 60/40.
3. **Weighting Schemes**: Risk parity vs. equal weight.
4. **Rebalancing Frequency**: Monthly and no-rebalance scenarios.
5. **Outlier Exclusion**: Remove weeks with >300% or <-80% returns and re-run analyses.
6. **Placebo Test**: Randomize treatment labels 1,000 times; compute empirical p-value.
7. **Hold-Out Validation**: Apply coefficients to reserved 12 matched pairs.

## 7. Interim Monitoring

- Interim descriptive review at Week 26 without hypothesis testing.
- Any request for inferential peeking requires governance approval and alpha-spending plan (e.g., O’Brien-Fleming).

## 8. Reporting Standards

- Provide full table of summary statistics, correlations, and covariance matrices.
- Publish regression tables with coefficient estimates, standard errors, t-stats, p-values, R².
- Include diagnostic plots: Q-Q plots, residual vs. fitted, leverage statistics.
- Release anonymized dataset with unique IDs, not ticker symbols, until public dissemination.

## 9. Software & Reproducibility

- Use Python (pandas, statsmodels) for data preparation and regression.
- Use R (optional) for cross-validation of key models.
- All scripts must be version-controlled and tagged at analysis freeze.
- Provide `analysis.yml` manifest capturing software versions and seeds.

## 10. Sign-Off

- SAP approved by Principal Investigator, Statistician, and Governance Chair prior to Week 1 data collection.
- Any deviations logged with timestamp, rationale, and impact assessment.

