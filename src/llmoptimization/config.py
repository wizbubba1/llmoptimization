"""Configuration utilities for the LLM optimization experiment."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any, Mapping

import yaml


@dataclass
class Config:
    """Typed wrapper around experiment configuration values."""

    data: Mapping[str, Any]

    def get(self, path: str, default: Any = None) -> Any:
        """Retrieve a nested configuration value using dot-delimited paths."""

        node: Any = self.data
        for segment in path.split("."):
            if isinstance(node, Mapping) and segment in node:
                node = node[segment]
            else:
                return default
        return node


def load_config(path: str | pathlib.Path) -> Config:
    """Load configuration from a YAML file."""

    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, Mapping):
        raise ValueError("Configuration root must be a mapping")
    return Config(data=data)


DEFAULT_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "defaults.yaml"


def load_default_config() -> Config:
    """Load configuration from the repository default."""

    if not DEFAULT_CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Default configuration file not found. Copy config/defaults.example.yaml to config/defaults.yaml."
        )
    return load_config(DEFAULT_CONFIG_PATH)

