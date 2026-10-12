"""Plot an episode to PNG, or animate it to GIF. Needs the `render` extra (matplotlib)."""

from __future__ import annotations

import numpy as np

from .sim import EpisodeResult

STATE_COLORS = {"surge": "#d62728", "cast": "#1f77b4", "search": "#7f7f7f", "climb": "#2ca02c"}


def _setup(res: EpisodeResult):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xmin, xmax, ymin, ymax = res.bounds
    fig, ax = plt.subplots(figsize=(10, 10 * (ymax - ymin) / (xmax - xmin) + 0.6))
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_xlabel("downwind (m)")
    ax.set_ylabel("crosswind (m)")
    ax.plot(*res.source, marker="*", color="gold", markeredgecolor="k", markersize=16, zorder=5)
    ax.plot(*res.path[0], marker="o", color="k", markersize=6, zorder=5)
    outcome = f"found source in {res.time:.1f}s" if res.success else f"timed out at {res.time:.0f}s"
    ax.set_title(f"{res.agent} | seed {res.seed} | {outcome}")
    handles = [
        plt.Line2D([], [], color=STATE_COLORS[s], lw=2, label=s)
        for s in dict.fromkeys(res.states)
        if s in STATE_COLORS
    ]
    ax.legend(handles=handles, loc="upper right")
    fig.tight_layout()
    return fig, ax, plt


def _segments(res: EpisodeResult, upto: int):
    """Trajectory split into runs of the same state, for colouring."""
    path, states = res.path[: upto + 1], res.states[: upto + 1]
    start = 0
    for i in range(1, len(states) + 1):
        if i == len(states) or states[i] != states[start]:
            yield states[start], path[start : i + 1]
            start = i


def render_png(res: EpisodeResult, out: str) -> None:
    fig, ax, plt = _setup(res)
    if res.frames:
        puffs = res.frames[-1]
        ax.scatter(puffs[:, 0], puffs[:, 1], s=6, color="#9467bd", alpha=0.35, lw=0)
    for state, seg in _segments(res, len(res.path) - 1):
        ax.plot(seg[:, 0], seg[:, 1], color=STATE_COLORS.get(state, "k"), lw=1.6)
    fig.savefig(out, dpi=110)
    plt.close(fig)


def render_gif(res: EpisodeResult, out: str, record_every: int, fps: int = 20) -> None:
    from matplotlib.animation import FuncAnimation, PillowWriter

    fig, ax, plt = _setup(res)
    puffs = ax.scatter([], [], s=6, color="#9467bd", alpha=0.35, lw=0)
    lines = []

    def draw(k):
        for ln in lines:
            ln.remove()
        lines.clear()
        frame = res.frames[k]
        puffs.set_offsets(frame if len(frame) else np.empty((0, 2)))
        upto = min(k * record_every + 1, len(res.path) - 1)
        for state, seg in _segments(res, upto):
            (ln,) = ax.plot(seg[:, 0], seg[:, 1], color=STATE_COLORS.get(state, "k"), lw=1.6)
            lines.append(ln)
        return [puffs, *lines]

    anim = FuncAnimation(fig, draw, frames=len(res.frames), blit=False)
    anim.save(out, writer=PillowWriter(fps=fps), dpi=70)
    plt.close(fig)
