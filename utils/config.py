"""
Load config.yaml and provide defaults.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class SearchConfig:
    max_results: int = 50


@dataclass
class RetrieverConfig:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    k: int = 5


@dataclass
class SummarizerConfig:
    model: str = "t5-small"
    t5: Dict[str, Any] = field(default_factory=lambda: {
        "max_length": 100, "min_length": 30, "num_beams": 4,
    })
    bart: Dict[str, Any] = field(default_factory=lambda: {
        "max_length": 150, "min_length": 40, "num_beams": 4, "length_penalty": 2.0,
    })


@dataclass
class Config:
    search: SearchConfig = field(default_factory=SearchConfig)
    retriever: RetrieverConfig = field(default_factory=RetrieverConfig)
    summarizer: SummarizerConfig = field(default_factory=SummarizerConfig)


def load_config(path: str = None) -> Config:
    """Load from YAML or return defaults if file missing."""
    p = Path(path) if path else _CONFIG_PATH
    if not p.exists():
        return Config()

    with open(p) as f:
        raw = yaml.safe_load(f) or {}

    cfg = Config()
    if "search" in raw:
        cfg.search = SearchConfig(**raw["search"])
    if "retriever" in raw:
        cfg.retriever = RetrieverConfig(**raw["retriever"])
    if "summarizer" in raw:
        s = raw["summarizer"]
        cfg.summarizer = SummarizerConfig(
            model=s.get("model", "t5-small"),
            t5=s.get("t5", cfg.summarizer.t5),
            bart=s.get("bart", cfg.summarizer.bart),
        )
    return cfg
