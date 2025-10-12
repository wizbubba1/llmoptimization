# Implementation Roadmap

This roadmap translates the experimental blueprint into an actionable project plan with milestone gates, responsible roles, and tooling requirements.

## Phase 0 – Mobilization (Weeks 0-1)

- Finalize funding commitments ($200k capital + $180k operating budget).
- Hire/assign:
  - Portfolio manager (0.75 FTE)
  - Quantitative researcher (0.5 FTE)
  - Data engineer (0.5 FTE)
- Execute NDAs, conflict-of-interest disclosures, and personal wallet attestations.
- Establish governance committee for protocol deviations.

## Phase 1 – Infrastructure & Paper Trading (Weeks 1-8)

1. **Systems Setup**
   - Provision AWS accounts, configure VPC, IAM, and audit logging.
   - Deploy PostgreSQL (market data) and MongoDB (LLM responses).
   - Configure S3 bucket for documentation archives and backups.

2. **Data Pipelines**
   - Implement CoinGecko and exchange API collectors with redundancy and validation.
   - Build LLM query orchestrator with rate limiting, caching, and retry logic.
   - Develop documentation/scraping jobs with BeautifulSoup and Selenium fallbacks.

3. **Scoring & Matching**
   - Compute baseline LLOS for ≥400 assets.
   - Run propensity score matching, generate matched pairs, and create reserve list.
   - Perform balance diagnostics and document results.

4. **Paper Portfolio**
   - Execute weekly simulated rebalances.
   - Log all trades, slippage estimates, and deviations.
   - Validate Sortino ratio computation pipeline using historical data.

## Phase 2 – Pilot Deployment (Weeks 9-20)

- Deploy $25,000 capital split between treatment/control portfolios.
- Start weekly live rebalancing with limit orders.
- Measure actual slippage vs. model assumptions; recalibrate transaction cost model.
- Run first monthly LLM re-test cycle (50 queries × 120 assets).
- Conduct first quarterly documentation QA (20% manual review).
- Gate to Phase 3 requires:
  - Tracking error <3% vs. paper portfolio.
  - Operational uptime ≥99%.
  - No unresolved critical incidents.

## Phase 3 – Full Deployment (Weeks 21-52)

- Scale to $200,000 capital ($100k per portfolio).
- Continue weekly rebalancing, monthly LLM tests, quarterly documentation updates.
- Publish internal weekly dashboards covering performance, risk, and compliance.
- Conduct interim non-inferential review at Week 26.
- Begin drafting replication package and manuscript outline at Week 39.

## Phase 4 – Optional Extension (Weeks 53-78)

- Extend if primary analysis indicates significant or strengthening effects.
- Maintain same procedures; incorporate lessons learned from Phase 3.
- Evaluate regime-specific behavior (bull, bear, sideways).

## Cross-Phase Workstreams

- **Compliance**: Monitor evolving regulatory guidance (SEC, CFTC, MiCA). Maintain trade logs and audit trails.
- **Security**: Rotate API keys quarterly, enforce MFA on exchanges, perform penetration tests.
- **Risk Management**: Weekly review of stop-loss triggers, drawdown metrics, and exchange exposures.
- **Documentation**: Update runbooks, incident reports, and governance meeting minutes.

## Deliverables Timeline (Gantt Overview)

| Week | Deliverable |
| ---- | ----------- |
| 1 | Infrastructure blueprint, risk register |
| 4 | Operational data pipelines validated |
| 8 | Matched-pair book + paper trading report |
| 12 | Pilot performance review |
| 20 | Pilot close-out memorandum |
| 26 | Interim dashboard + sensitivity checks |
| 39 | Draft manuscript sections (Methods, Data) |
| 52 | Final dataset freeze, statistical analysis, manuscript draft |
| 56 | Replication package + OSF upload |

