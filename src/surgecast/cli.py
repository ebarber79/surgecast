"""surgecast command line: `run` one episode, or `bench` agents against each other."""

from __future__ import annotations

import argparse
import math
import sys

from .agents import AGENTS
from .plume import PlumeConfig
from .sim import EpisodeConfig, bench, run_episode


def _add_env_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("environment")
    g.add_argument("--wind", type=float, default=PlumeConfig.wind_speed, help="wind speed, m/s")
    g.add_argument(
        "--meander",
        type=float,
        default=PlumeConfig.meander_sigma,
        help="std of wind direction, rad (higher = snakier plume)",
    )
    g.add_argument(
        "--turbulence",
        type=float,
        default=PlumeConfig.turbulence,
        help="per-puff random-walk strength (higher = patchier plume)",
    )
    g.add_argument("--max-time", type=float, default=EpisodeConfig.max_time, help="seconds")


def _configs(args) -> tuple[PlumeConfig, EpisodeConfig]:
    return (
        PlumeConfig(wind_speed=args.wind, meander_sigma=args.meander, turbulence=args.turbulence),
        EpisodeConfig(max_time=args.max_time),
    )


def cmd_run(args) -> int:
    plume_cfg, ep_cfg = _configs(args)
    record_every = 0
    if args.out:
        record_every = 3 if args.out.endswith(".gif") else 1
    res = run_episode(args.agent, args.seed, plume_cfg, ep_cfg, record_every=record_every)
    outcome = f"found source in {res.time:.1f}s" if res.success else f"timed out at {res.time:.0f}s"
    print(f"{res.agent} seed={res.seed}: {outcome}, odor hits={res.hits}")
    if args.out:
        try:
            from . import render
        except ImportError:
            print("rendering needs matplotlib: pip install 'surgecast[render]'", file=sys.stderr)
            return 1
        if args.out.endswith(".gif"):
            render.render_gif(res, args.out, record_every)
        else:
            render.render_png(res, args.out)
        print(f"wrote {args.out}")
    return 0


def cmd_bench(args) -> int:
    plume_cfg, ep_cfg = _configs(args)
    rows = bench(args.agents, args.trials, plume_cfg, ep_cfg, seed0=args.seed)
    print(f"{'agent':<10} {'success':>8} {'median time (s)':>16}   ({args.trials} trials, same plumes)")
    for r in rows:
        t = "-" if math.isnan(r.median_time) else f"{r.median_time:.1f}"
        print(f"{r.agent:<10} {r.success_rate:>8.0%} {t:>16}")
    return 0


def cmd_guide(args) -> int:
    from .hw.simdevice import DeviceSimConfig, run_device_episode

    cfg = DeviceSimConfig(sensor_tau=args.sensor_tau, reaction=args.reaction)
    if args.trials > 1:
        runs = [run_device_episode(args.seed + s, cfg).result for s in range(args.trials)]
        times = [r.time for r in runs if r.success]
        med = f"{sorted(times)[len(times) // 2]:.1f}s" if times else "-"
        print(f"simulated handheld guide: {len(times) / len(runs):.0%} found source, median {med} "
              f"({args.trials} trials, sensor tau {args.sensor_tau}s, reaction {args.reaction}s)")
        return 0

    record_every = 0
    if args.out:
        record_every = 3 if args.out.endswith(".gif") else 1
    run = run_device_episode(args.seed, cfg, record_every=record_every)
    last = None
    for ins in run.instructions:
        if ins.state != last:
            print(f"{ins.t:6.1f}s  {ins.state.upper():<7}  {ins.text}")
            last = ins.state
    res = run.result
    outcome = f"reached the source in {res.time:.1f}s" if res.success else f"timed out at {res.time:.0f}s"
    print(f"simulated walker {outcome}")
    if args.log:
        from .hw.log import write_csv

        write_csv(args.log, run.readings, run.instructions)
        print(f"wrote {args.log}")
    if args.out:
        try:
            from . import render
        except ImportError:
            print("rendering needs matplotlib: pip install 'surgecast[render]'", file=sys.stderr)
            return 1
        if args.out.endswith(".gif"):
            render.render_gif(res, args.out, record_every)
        else:
            render.render_png(res, args.out)
        print(f"wrote {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="surgecast", description="Moth-style odor source search in a simulated turbulent plume."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run one episode")
    run.add_argument("--agent", choices=sorted(AGENTS), default="surgecast")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out", help="write a .png plot or .gif animation")
    _add_env_args(run)
    run.set_defaults(func=cmd_run)

    b = sub.add_parser("bench", help="compare agents on the same plume realizations")
    b.add_argument("--agents", nargs="+", choices=sorted(AGENTS), default=["surgecast", "upwind", "gradient"])
    b.add_argument("--trials", type=int, default=50)
    b.add_argument("--seed", type=int, default=0, help="first seed")
    _add_env_args(b)
    b.set_defaults(func=cmd_bench)

    g = sub.add_parser("guide", help="handheld guide on a simulated device in an indoor fan plume")
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--trials", type=int, default=1, help=">1 prints a success summary instead")
    g.add_argument("--sensor-tau", type=float, default=2.0, help="gas sensor response time, s")
    g.add_argument("--reaction", type=float, default=0.7, help="walker reaction delay, s")
    g.add_argument("--log", help="write readings and instructions to CSV")
    g.add_argument("--out", help="write a .png plot or .gif animation")
    g.set_defaults(func=cmd_guide)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
