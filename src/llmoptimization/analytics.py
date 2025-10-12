"""Portfolio analytics and statistical utilities."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


def downside_deviation(returns: Sequence[float], target: float = 0.0) -> float:
    """Calculate downside deviation relative to a target return."""

    returns_array = np.asarray(returns, dtype=float)
    downside = np.minimum(0.0, returns_array - target)
    if downside.size == 0:
        return float("nan")
    return math.sqrt(np.mean(np.square(downside)))


def sortino_ratio(returns: Sequence[float], target: float = 0.0) -> float:
    """Compute the Sortino ratio given periodic returns."""

    returns_array = np.asarray(returns, dtype=float)
    mean_excess = np.mean(returns_array - target)
    downside = downside_deviation(returns_array, target)
    if downside == 0:
        return float("inf")
    return mean_excess / downside


def annualized_return(returns: Sequence[float], periods_per_year: int = 52) -> float:
    """Compute annualized return from periodic returns."""

    returns_array = np.asarray(returns, dtype=float)
    compounded = np.prod(1 + returns_array)
    return compounded ** (periods_per_year / len(returns_array)) - 1


def max_drawdown(series: Sequence[float]) -> float:
    """Calculate maximum drawdown for a cumulative return series."""

    values = np.asarray(series, dtype=float)
    running_max = np.maximum.accumulate(values)
    drawdowns = (values - running_max) / running_max
    return float(np.min(drawdowns))


def calmar_ratio(returns: Sequence[float], periods_per_year: int = 52) -> float:
    """Calmar ratio = annualized return / |max drawdown|."""

    cumulative = np.cumprod(1 + np.asarray(returns, dtype=float))
    max_dd = abs(max_drawdown(cumulative))
    if max_dd == 0:
        return float("inf")
    return annualized_return(returns, periods_per_year) / max_dd


def weekly_returns_from_prices(prices: Sequence[float]) -> np.ndarray:
    """Compute simple weekly returns from a price series."""

    price_array = np.asarray(prices, dtype=float)
    return price_array[1:] / price_array[:-1] - 1


def pairwise_sortino(treatment: pd.Series, control: pd.Series, target: float = 0.0) -> pd.DataFrame:
    """Calculate Sortino ratios for matched treatment/control pairs."""

    records = []
    for pair_id in sorted(set(treatment.index.get_level_values(0))):
        t_returns = treatment.xs(pair_id, level=0).dropna().to_numpy()
        c_returns = control.xs(pair_id, level=0).dropna().to_numpy()
        if t_returns.size == 0 or c_returns.size == 0:
            continue
        records.append(
            {
                "pair_id": pair_id,
                "sortino_treatment": sortino_ratio(t_returns, target),
                "sortino_control": sortino_ratio(c_returns, target),
                "difference": sortino_ratio(t_returns, target) - sortino_ratio(c_returns, target),
            }
        )
    return pd.DataFrame.from_records(records)

