"""Configuration loading from YAML and environment."""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@dataclass
class Weights:
    yield_: float = 0.30
    momentum: float = 0.25
    price_trend: float = 0.20
    volume: float = 0.15
    age: float = 0.10

    def as_dict(self) -> dict:
        return {
            "yield": self.yield_,
            "momentum": self.momentum,
            "price_trend": self.price_trend,
            "volume": self.volume,
            "age": self.age,
        }


@dataclass
class Config:
    rpc_endpoint: str = "wss://entrypoint-finney.opentensor.ai:443"
    network: str = "finney"
    weights: Weights = field(default_factory=Weights)
    top_n: int = 5
    rebalance_interval_days: int = 7
    dry_run: bool = True
    reference_url: str = "https://taostats.io"
    accuracy_margin: float = 0.05


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from YAML file, with env var overrides."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    data = {}
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
            data = raw

    # Build weights
    w = data.get("weights", {})
    weights = Weights(
        yield_=w.get("yield", 0.30),
        momentum=w.get("momentum", 0.25),
        price_trend=w.get("price_trend", 0.20),
        volume=w.get("volume", 0.15),
        age=w.get("age", 0.10),
    )

    config = Config(
        rpc_endpoint=os.environ.get("RPC_ENDPOINT", data.get("rpc_endpoint", "wss://entrypoint-finney.opentensor.ai:443")),
        network=os.environ.get("NETWORK", data.get("network", "finney")),
        weights=weights,
        top_n=int(os.environ.get("TOP_N", data.get("top_n", 5))),
        rebalance_interval_days=data.get("rebalance_interval_days", 7),
        dry_run=os.environ.get("DRY_RUN", str(data.get("dry_run", True))).lower() in ("true", "1", "yes"),
        reference_url=data.get("reference_url", "https://taostats.io"),
        accuracy_margin=data.get("accuracy_margin", 0.05),
    )

    return config
