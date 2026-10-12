"""Moth-style surge-cast odor source search in a simulated turbulent plume."""

from .agents import AGENTS, Observation
from .plume import Plume, PlumeConfig
from .sim import EpisodeConfig, EpisodeResult, bench, run_episode

__all__ = [
    "AGENTS",
    "EpisodeConfig",
    "EpisodeResult",
    "Observation",
    "Plume",
    "PlumeConfig",
    "bench",
    "run_episode",
]
__version__ = "0.1.0"
