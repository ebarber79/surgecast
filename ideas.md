# Idea map: anatomy → mechanism → utility

Each row is a real biological trick with a known engineering analog. "Pi-buildable" = doable
here with software and/or cheap hardware (camera, mic, LEDs, a gas sensor).

## Moth

| Anatomy | What it actually does | Utility candidate | Pi-buildable? |
|---|---|---|---|
| **Antennae + plume-tracking behavior** | Detects a few pheromone molecules; finds the source by *surge* upwind on contact, *cast* side-to-side on loss | **Leak/source finder:** a gas/smoke/odor sensor on a rover or handheld that guides you to the source with surge-cast logic, not gradient-following (which fails in turbulent air) | Yes, MQ-series gas sensor + simulation first |
| **Compound eye nanostructure ("moth-eye")** | Sub-wavelength bumps grade the refractive index, so almost no reflection | Anti-glare for camera lenses/screens/solar. This is a materials problem, not software | No (fab needed) |
| **Wing scales (acoustic camouflage)** | Scales resonate and absorb bat ultrasound | Thin sound-absorbing panels, again materials | Partially (3D-printed resonator panels) |
| **Ears tuned to bat calls** | A few neurons; triggers evasive dive when a bat's sonar ramps up | **Ultrasonic/approach alarm:** cheap detector that fires only on a specific ramping signature | Yes, ultrasonic mic |
| **Transverse orientation** | Holds a fixed angle to a distant light (why they spiral into lamps) | Mostly a cautionary tale, or a low-cost heading-hold for a robot using a sky light source | Yes, but niche |

## Firefly

| Anatomy | What it actually does | Utility candidate | Pi-buildable? |
|---|---|---|---|
| **Synchronous flashing** (pulse-coupled oscillators) | Thousands sync with no leader: each nudges its phase when it sees a neighbor flash | **Leaderless clock sync** for sensor nodes/IoT/LED arrays, or a "firefly scheduler" that spreads or aligns cron jobs across machines without a coordinator | Yes, pure software, or ESP32s + LEDs |
| **Species flash codes** | Each species has a timing pattern; females answer with a delay; some predators fake other codes | **Optical signaling protocol:** device pairing or data by blink timing via LED + camera, with spoofing detection | Yes, LED + Pi camera |
| **Lantern (luciferase, near-lossless "cold light")** | Chemical light with almost no heat | Chemistry, not buildable here | No |
| **Lantern cuticle microstructure** | Tapered scales boost light extraction, and this was copied into LED lenses | Optics fab | No |
| **Firefly algorithm** | Metaheuristic optimizer (brighter attracts dimmer) | A library/tool, but it's already a well-known algorithm and isn't novel | Yes, but low novelty |

## Combined (moth + firefly)

- **Moth-to-flame + firefly sync = swarm search.** Cheap nodes cast for a signal, moth-style, and
  flash-sync to share the find, firefly-style. Good for finding a leak, a lost device, or the
  noisiest spot in a building.

## Shortlist (my take)

1. **Surge-cast source finder.** Clear real-world use (gas leaks, smells, RF/sound sources), the
   algorithm is well documented in insect literature, and it can start as a simulation on the Pi.
2. **Leaderless firefly sync.** Useful for distributed jobs/IoT, pure software, easy to demo
   visually.
3. **Blink-code pairing/messaging.** Fun, demonstrable, and it has a security angle (spoof detection).

## Open questions

- Software-only, or some hardware?
- Who uses it: you, a client, the public as open source?
- What does "done" look like for v0?
