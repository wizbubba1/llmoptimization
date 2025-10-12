# Experiment Operations Runbook

This runbook explains how to take the repository from a clean checkout to a running instance of the 52-week LLM-optimized cryptocurrency experiment. Follow the sections in order; each stage links back to the detailed design documents when additional context is helpful.

## 1. Prerequisites

- Python 3.10 or newer with `pip` available.
- Accounts and API keys for the providers listed in `config/defaults.example.yaml` (LLM vendors, CoinGecko Pro, SEO data, social data, storage).
- Access to a PostgreSQL instance and a MongoDB instance if you plan to persist market/LLM data as described in `docs/data_pipeline.md`.
- (Optional) AWS or S3-compatible object storage for raw data archives.

## 2. Set up the Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If you intend to run notebooks, install your preferred Jupyter environment separately; notebooks are ignored by Git by default.

## 3. Configure the experiment

1. Copy the example configuration and edit it with real credentials plus the asset universe you plan to study.
   ```bash
   cp config/defaults.example.yaml config/defaults.yaml
   ```
2. In `config/defaults.yaml`:
   - Replace every `YOUR_*` placeholder with an actual API key or secret.
   - Update `experiment.assets` with the list of cryptocurrency identifiers (CoinGecko slugs) that constitute your initial prompt battery universe.
   - Adjust `llm.iterations`, prompt weights, or storage locations as needed.
   - Ensure `paths.llm_runs_dir` points to a writable directory (defaults to `data/llm_runs`).
3. Store the filled file securely—`config/defaults.yaml` is already git-ignored.

## 4. Bootstrap storage locations

Create any directories referenced in the config (the CLI will create `paths.llm_runs_dir` automatically, but doing so manually confirms permissions):

```bash
mkdir -p data/llm_runs
```

If you are using local PostgreSQL or MongoDB instances, confirm connectivity before moving on.

## 5. Build the asset universe and baseline scores

1. Use the helpers in `llmoptimization.data_sources` to collect market, documentation, and community data. For example, to pull 90 days of CoinGecko prices for a candidate asset:
   ```bash
   python - <<'PYTHON'
   import asyncio
   from llmoptimization.config import load_default_config
   from llmoptimization.data_sources import CoinGeckoSource, close_sources

   async def main():
       cfg = load_default_config()
       source = CoinGeckoSource(cfg)
       data = [point async for point in source.fetch("bitcoin", days=90)]
       print(f"Fetched {len(data)} price points for bitcoin")
       await close_sources(source)

   asyncio.run(main())
   PYTHON
   ```
2. Calculate LLM optimization scores with `llmoptimization.scoring`. The snippet below shows how to aggregate component scores pulled from your data pipeline:
   ```bash
   python - <<'PYTHON'
   from llmoptimization.scoring import compute_llos

   component_scores = {
       "web_presence": 82.0,
       "llm_recommendation": 76.0,
       "documentation_quality": 90.0,
       "narrative_simplicity": 70.0,
       "social_community": 65.0,
       "developer_activity": 55.0,
   }
   llos = compute_llos(component_scores)
   print(f"Total LLOS: {llos.total:.2f}")
   print("Weighted components:")
   for name, value in llos.components.items():
       print(f"  {name}: {value:.2f}")
   PYTHON
   ```
3. Persist the computed scores (CSV, database, or data lake) for downstream matching and analytics.

## 6. Run the standardized LLM prompt battery

With the configuration in place, execute the CLI to gather baseline LLM responses:

```bash
python -m llmoptimization.experiment --config config/defaults.yaml run --from-config
```

- The command reads the asset list from `experiment.assets` and queries each configured model for every prompt template.
- Results are stored as newline-delimited JSON in `paths.llm_runs_dir` (e.g., `data/llm_runs/llm_prompts_YYYYMMDDTHHMMSSZ.jsonl`).
- Use `--output /custom/path.jsonl` to override the destination or add tickers inline (`... run bitcoin ethereum`).

Import the JSONL file into your database or analytics environment to perform detail scoring, sentiment analysis, and ranking extraction per the methodology in `docs/data_pipeline.md`.

## 7. Weekly operational cycle

Repeat the following steps every rebalance window (default: Sundays at 23:59 UTC):

1. **Refresh documentation and web metrics** using your scraping/SEO scripts and recompute component scores.
2. **Re-run the LLM prompt battery**:
   ```bash
   python -m llmoptimization.experiment --config config/defaults.yaml run --from-config
   ```
   Archive each JSONL output with the corresponding week identifier.
3. **Update matched pairs and portfolio weights** using the latest scores and market data.
4. **Execute simulated or live rebalances**; log executed trades alongside transaction costs.
5. **Generate performance diagnostics** using the analytics helpers. For example:
   ```bash
   python - <<'PYTHON'
   import pandas as pd
   from llmoptimization.analytics import sortino_ratio

   treatment = pd.read_csv("data/weekly_returns_treatment.csv", parse_dates=["week"])
   control = pd.read_csv("data/weekly_returns_control.csv", parse_dates=["week"])
   target = 0.04 / 52
   print("Treatment Sortino:", sortino_ratio(treatment.set_index("week")["return"], target))
   print("Control Sortino:", sortino_ratio(control.set_index("week")["return"], target))
   PYTHON
   ```
6. **Document anomalies** (API outages, exchange issues, scoring changes) in an operations log for auditability.

## 8. Linking back to the research protocol

- `docs/experiment_design.md` – hypotheses, sampling plan, and statistical guardrails.
- `docs/data_pipeline.md` – architecture for persisting market, LLM, and documentation data.
- `docs/implementation_roadmap.md` – phased rollout from paper trading to full deployment.
- `docs/statistical_analysis_plan.md` – hypothesis tests, regression specifications, and robustness checks.
- `docs/preregistration_template.md` – fill this out before collecting live data to lock the analysis plan.

By following this runbook you move from raw code to a reproducible, instrumented experiment that mirrors the design presented in the documentation suite. Tailor each step to your infrastructure while keeping the pre-registered methodology intact.
