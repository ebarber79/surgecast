import numpy as np

from surgecast import AGENTS, Observation, Plume, PlumeConfig, bench, run_episode
from surgecast.cli import main


def test_puffs_travel_downwind_and_leave_arena():
    plume = Plume(PlumeConfig(meander_sigma=0.0, turbulence=0.0), np.random.default_rng(0))
    for _ in range(100):
        plume.step(0.1)
    # 10 s at 1 m/s from x=5: the oldest puff is near x=15, all on the centreline.
    assert 14.5 < plume.pos[:, 0].max() < 15.5
    assert np.allclose(plume.pos[:, 1], 0.0)
    for _ in range(1000):
        plume.step(0.1)
    assert plume.pos[:, 0].max() <= PlumeConfig.bounds[1]


def test_concentration_peaks_on_plume_axis():
    plume = Plume(PlumeConfig(meander_sigma=0.0), np.random.default_rng(0))
    for _ in range(300):
        plume.step(0.1)
    on_axis = plume.concentration(np.array([15.0, 0.0]))
    off_axis = plume.concentration(np.array([15.0, 8.0]))
    assert on_axis > 10 * off_axis


def test_surgecast_surges_upwind_on_detection_then_casts_crosswind():
    agent = AGENTS["surgecast"]()
    agent.reset(np.random.default_rng(0))
    wind = np.array([1.0, 0.0])
    pos = np.zeros(2)
    h = agent.act(Observation(0.0, pos, wind, 1.0, True), 0.1)
    assert agent.state == "surge" and np.allclose(h, [-1.0, 0.0])
    h = agent.act(Observation(5.0, pos, wind, 0.0, False), 0.1)
    assert agent.state == "cast" and np.allclose(abs(h[1]), 1.0)


def test_cast_legs_alternate_and_widen():
    agent = AGENTS["surgecast"](cast_leg=1.0, cast_growth=2.0, max_leg=100.0)
    agent.reset(np.random.default_rng(0))
    wind = np.array([1.0, 0.0])
    dirs = []
    for i in range(80):
        h = agent.act(Observation(10 + i * 0.1, np.zeros(2), wind, 0.0, False), 0.1)
        dirs.append(np.sign(h[1]))
    turns = [i for i in range(1, len(dirs)) if dirs[i] != dirs[i - 1]]
    legs = np.diff(turns)
    assert len(legs) >= 2 and all(b > a for a, b in zip(legs, legs[1:]))


def test_episode_is_reproducible():
    a = run_episode("surgecast", 3)
    b = run_episode("surgecast", 3)
    assert a.success == b.success and np.array_equal(a.path, b.path)


def test_surgecast_beats_gradient_in_turbulence():
    rows = {r.agent: r for r in bench(["surgecast", "gradient"], trials=10)}
    assert rows["surgecast"].success_rate >= 0.7
    assert rows["surgecast"].success_rate > rows["gradient"].success_rate


def test_cli_run(capsys):
    assert main(["run", "--seed", "0", "--max-time", "20"]) == 0
    assert "surgecast seed=0" in capsys.readouterr().out
