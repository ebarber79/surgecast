# moth-firefly → `surgecast`

Find the source of a smell, leak or plume the way a male moth finds a female: **surge upwind
when you smell it, cast crosswind when you lose it.** Not a metaphor, the actual algorithm.

![surge-cast agent tracking a turbulent plume](docs/surgecast.gif)

## Why not just follow the gradient?

In turbulent air, odor arrives as patches with gaps between them. Two samples a moment apart
say almost nothing about which way the source is, so "go where it's stronger" wanders around
inside the plume and never closes in. Moths ignore the concentration level. They use only
*odor present / absent* plus the *wind direction* they feel on their antennae:

- **Surge:** odor detected → fly upwind.
- **Cast:** odor lost → zigzag crosswind, with each leg wider than the last, until it's back.

Two refinements make it faster:

- **Upwind means the recent average wind**, not the current gust. The odor reaching you left
  the source seconds ago on the wind of that time, so the averaged wind points back along the
  plume.
- **Casting keeps edging upwind** (about 20% of its effort). Any more than that and the agent
  overshoots the source, and nothing upwind of the source ever smells of anything.

Same 50 simulated plumes for every strategy (`surgecast bench`):

| agent | strategy | success | median time |
|---|---|---|---|
| `surgecast` | surge upwind on contact, cast crosswind on loss | **98%** | 56 s |
| `upwind` | surge on contact, random walk on loss (no casting) | 52% | 53 s |
| `gradient` | klinotaxis: keep heading while concentration rises | 0% | – |

The `upwind` row shows that casting is what makes this work. Surging alone loses the plume and
rarely finds it again (its median time is lower only because it succeeds just on the easy runs).

The refinements cut surgecast's median time from 78 s to 56 s on these seeds. The cost is
one near-miss in 50: a plume so sparse that the agent edged past it to finish level with the
source but 2.6 m to the side. In snakier wind (`--meander 0.6`) they help across the board,
raising success from 50% to 82% and cutting the median from 108 s to 74 s. Parameters were
tuned on seeds 100–149, which the benchmark seeds 0–49 don't overlap.

| surgecast | gradient (same plume) |
|---|---|
| ![](docs/surgecast.png) | ![](docs/gradient.png) |

The puffs show the plume at the end of the run. The gradient agent spent most of its 150 s
*inside* the odor and still never reached the source.

## Use it

```bash
pip install -e '.[render]'        # numpy core; matplotlib only for plots

surgecast bench --trials 50                     # compare agents
surgecast run --seed 2 --out run.png            # plot one episode (.gif animates)
surgecast run --agent gradient --meander 0.6    # snakier wind
```

Environment knobs: `--wind` (m/s), `--meander` (wind direction wobble, rad), `--turbulence`
(puff patchiness), `--max-time`.

From Python:

```python
from surgecast import run_episode, bench, PlumeConfig
res = run_episode("surgecast", seed=0, plume_cfg=PlumeConfig(meander_sigma=0.5))
res.success, res.time, res.path
```

## Handheld guide (v1, in progress)

The same logic, packaged as a device you carry: a gas sensor, a wind vane and an IMU tell it
what you smell and which way the air moves, and it tells you which way to walk. Parts, wiring
and what the simulation says about the design are in [`docs/hardware.md`](docs/hardware.md),
with a [wiring schematic](docs/schematic.svg) and a [layout sketch](docs/layout.svg). A narrated,
captioned [video of the proposed prototype](docs/video/surgecast-prototype.mp4) shows the 3D model
and a simulated walk (rebuild it with `scripts/render_video.py`).
Until the parts arrive, `surgecast guide` runs the whole software path on a simulated device
in an indoor fan plume, with a slow gas sensor and a person reacting to the instructions:

```
$ surgecast guide --seed 3
cues: - surge | .. left | ... right | -- recover
    0.0s  ..   LEFT     Lost it. Walk across the wind, wind on your right (turn left 87°)
    0.3s  -    SURGE    Odor! Walk into the wind
    3.0s  ..   LEFT     Lost it. Walk across the wind, wind on your right (turn left 82°)
    3.5s  -    SURGE    Odor! Walk into the wind
   ...
simulated walker reached the source in 11.0s

$ surgecast guide --trials 50
simulated handheld guide: 100% found source, median 14.4s (50 trials, sensor tau 2.0s, reaction 0.7s)
```

Cues are patterns you can act on without reading (`-` long buzz, `.` short): `-` odor, walk
into the wind; `..` / `...` turn left / right and walk across the wind; `--` lost it for a while,
back off downwind. The buzzer will play the same patterns.

Sessions log to CSV with `--log`. `--replay session.csv` runs a log back through the same live
loop the device uses (`--realtime` for recorded speed), which is how a real walk will be
reviewed and the detector retuned.

![simulated walker following the guide](docs/guide.png)

## The model

- **Plume** (`plume.py`): puffs leave the source at 5/s, ride a wind whose direction wanders
  (Ornstein-Uhlenbeck), random-walk individually, and spread as they age. This is a simplified
  version of the filament model from Farrell et al. 2002, *Filament-based atmospheric
  dispersion model to achieve short time-scale structure of odor plumes*.
- **Sensing:** binary detection above a threshold, plus the local wind vector.
- **Agent:** 0.8 m/s ground speed, starts 25–35 m downwind, wins within 1 m of the source.

## Roadmap

- v0: simulation, three agents, benchmark, plots.
- v1 (in progress): handheld guide. Done: rise detector, guide, simulated device, live loop,
  cues, logging and replay. Next: sensor drivers and buzzer once the parts arrive
  ([`docs/hardware.md`](docs/hardware.md)).
- Later: several cheap nodes that share hits (the firefly half of the idea map; see
  [`ideas.md`](ideas.md)).

## Dev

```bash
uv venv && uv pip install -e '.[render,dev]' && .venv/bin/pytest
```
