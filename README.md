# LLM-Optimized Cryptocurrencies Research Project

This repository implements the end-to-end research workflow for testing whether cryptocurrencies that are "LLM-optimized"—i.e., more legible and accessible to large language models—earn superior risk-adjusted returns. The project packages the full experimental design, data-collection tooling, scoring methodology, and statistical analysis framework required to execute the 52-week matched-pair study described in the accompanying documentation.

## Repository Structure

- `docs/`: Detailed research protocol, operational plans, and appendices.
- `src/llmoptimization/`: Python package implementing scoring, data ingestion, LLM evaluation, and analytics utilities.
- `config/`: YAML configuration files specifying API credentials, thresholds, and runtime parameters.
- `notebooks/` *(optional)*: Suggested location for exploratory work (not tracked by default).

## Getting Started

1. Create a Python 3.10+ virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy the configuration template and fill in credentials plus your asset universe:
   ```bash
   cp config/defaults.example.yaml config/defaults.yaml
   # edit config/defaults.yaml and replace placeholder API keys / asset IDs
   ```
4. Trigger the baseline LLM prompt battery using the CLI:
   ```bash
   python -m llmoptimization.experiment --config config/defaults.yaml run --from-config
   ```
   Results are written to `data/llm_runs/` (configurable via `paths.llm_runs_dir`).

The step-by-step operational guide in `docs/runbook.md` walks through environment setup, scoring workflows, weekly maintenance, and integration with the broader research design. See `docs/implementation_roadmap.md` for a phased rollout plan and `docs/statistical_analysis_plan.md` for detailed hypothesis testing procedures.

## Licensing

All original content in this repository is released under the MIT License. See `LICENSE` for details.
