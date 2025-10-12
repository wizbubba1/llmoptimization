"""Computation utilities for the LLM Optimization Score (LLOS)."""

from __future__ import annotations

import dataclasses
from typing import Dict, Iterable, Mapping

import numpy as np


@dataclasses.dataclass(slots=True)
class ScoreComponent:
    """Represents a component of the composite LLOS."""

    name: str
    weight: float
    value: float

    def normalized(self) -> float:
        """Ensure the value is clipped to the 0–100 scoring range."""

        return float(np.clip(self.value, 0.0, 100.0))

    def weighted(self) -> float:
        """Return the weighted contribution of the component."""

        return self.weight * self.normalized()


@dataclasses.dataclass(slots=True)
class LLOS:
    """Container for the LLM Optimization Score breakdown."""

    components: Iterable[ScoreComponent]

    @property
    def total(self) -> float:
        return sum(component.weighted() for component in self.components)

    def as_dict(self) -> Dict[str, float]:
        return {component.name: component.normalized() for component in self.components}


DEFAULT_WEIGHTS: Mapping[str, float] = {
    "web_presence": 0.25,
    "llm_recommendation": 0.25,
    "documentation_quality": 0.20,
    "narrative_simplicity": 0.15,
    "social_community": 0.10,
    "developer_activity": 0.05,
}


def compute_llos(raw_scores: Mapping[str, float], weights: Mapping[str, float] | None = None) -> LLOS:
    """Compute the composite LLOS from raw component scores.

    Parameters
    ----------
    raw_scores:
        Mapping of component names to 0–100 raw values.
    weights:
        Optional mapping overriding the default weight allocation.
    """

    weights = weights or DEFAULT_WEIGHTS
    components = []
    for name, weight in weights.items():
        if name not in raw_scores:
            raise KeyError(f"Missing score component: {name}")
        components.append(ScoreComponent(name=name, weight=weight, value=float(raw_scores[name])))
    return LLOS(components=components)


def summarize_llos(llos: LLOS) -> Dict[str, float]:
    """Return a dictionary containing component and total scores."""

    summary = llos.as_dict()
    summary["total"] = llos.total
    return summary

