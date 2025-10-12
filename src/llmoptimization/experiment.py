"""Command-line entry points for running experiment workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from . import analytics, scoring
from .config import Config, load_config, load_default_config

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


PROMPTS = {
    "explain": "Explain what {asset} is and its primary use case.",
    "investment": "I am researching {asset} as an investment. What should I know?",
    "risks": "What are the main risks associated with {asset}?",
}


async def run_llm_sampling(
    asset_list: List[str], config: Config, output_path: Path | None = None
) -> Path:
    from .llm_queries import PromptRunner

    runner = PromptRunner(config)
    iterations = config.get("llm.iterations", 5)
    LOGGER.info(
        "Running LLM prompts for %d assets across %d templates (%d iterations)",
        len(asset_list),
        len(PROMPTS),
        iterations,
    )
    results = await runner.run_prompts(PROMPTS, asset_list, iterations=iterations)
    LOGGER.info("Collected %d prompt results", len(results))

    if output_path is None:
        output_dir = Path(config.get("paths.llm_runs_dir", "data/llm_runs"))
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        output_path = output_dir / f"llm_prompts_{timestamp}.jsonl"

    with output_path.open("w", encoding="utf-8") as handle:
        for result in results:
            json.dump(asdict(result), handle, ensure_ascii=False)
            handle.write("\n")

    LOGGER.info("Saved prompt responses to %s", output_path)

    if results:
        df = pd.DataFrame(asdict(r) for r in results)
        summary = (
            df.groupby(["model", "prompt_id"]).size().rename("count").reset_index()
        )
        LOGGER.info("Sample prompt coverage:\n%s", summary.to_string(index=False))

    return output_path


def compute_example_llos() -> None:
    sample_scores = {
        "web_presence": 82.0,
        "llm_recommendation": 76.0,
        "documentation_quality": 90.0,
        "narrative_simplicity": 70.0,
        "social_community": 65.0,
        "developer_activity": 55.0,
    }
    llos = scoring.compute_llos(sample_scores)
    LOGGER.info("Example LLOS total: %.2f", llos.total)


def run_sortino_demo() -> None:
    import numpy as np

    treatment_returns = np.random.normal(0.02, 0.08, size=52)
    control_returns = np.random.normal(0.015, 0.08, size=52)
    treatment_series = pd.Series(treatment_returns, index=pd.Index(range(52), name="week"))
    control_series = pd.Series(control_returns, index=pd.Index(range(52), name="week"))
    sortino_t = analytics.sortino_ratio(treatment_series, target=0.04 / 52)
    sortino_c = analytics.sortino_ratio(control_series, target=0.04 / 52)
    LOGGER.info("Treatment Sortino: %.3f | Control Sortino: %.3f", sortino_t, sortino_c)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM optimization experiment utilities")
    parser.add_argument("--config", type=str, help="Path to configuration file", default=None)
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Execute LLM sampling workflow")
    run_parser.add_argument("assets", nargs="*", help="List of cryptocurrency identifiers")
    run_parser.add_argument(
        "--from-config",
        action="store_true",
        help="Load asset list from experiment.assets in the configuration file",
    )
    run_parser.add_argument(
        "--output",
        type=str,
        help="Optional path for saving prompt results (defaults to timestamped JSONL)",
    )

    subparsers.add_parser("llos", help="Compute sample LLOS")
    subparsers.add_parser("sortino-demo", help="Run Sortino ratio demonstration")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "run":
        config = load_config(args.config) if args.config else load_default_config()
        if args.from_config:
            assets = list(config.get("experiment.assets", []))
        else:
            assets = list(args.assets)
        if not assets:
            raise SystemExit(
                "Provide asset identifiers or populate experiment.assets in the configuration"
            )
        output_path = Path(args.output) if args.output else None
        asyncio.run(run_llm_sampling(assets, config, output_path=output_path))
    elif args.command == "llos":
        compute_example_llos()
    elif args.command == "sortino-demo":
        run_sortino_demo()
    else:
        raise SystemExit("No command provided")


if __name__ == "__main__":
    main()

