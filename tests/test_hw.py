import math

import numpy as np

from surgecast.hw import Guide, OdorSignal, Reading, RiseDetector, run_device_episode
from surgecast.hw.guide import describe


def test_odor_signal_is_zero_in_clean_air_and_rises_with_odor():
    sig = OdorSignal(r_clean=50_000)
    assert sig.update(50_000, 0.1) == 0.0
    assert sig.update(25_000, 0.1) > 0.6  # ln 2


def test_odor_signal_baseline_survives_long_exposure():
    sig = OdorSignal(r_clean=50_000)
    for _ in range(300):  # 30 s in odor
        s = sig.update(25_000, 0.1)
    assert s > 0.5


def test_rise_detector_fires_on_onset_not_on_steady_level():
    det = RiseDetector(threshold=0.15, smooth_tau=0.3)
    det.update(0.0, 0.1)
    fired = [det.update(min(i * 0.05, 1.0), 0.1) for i in range(1, 80)]  # ramp then plateau
    assert any(fired[:15])
    assert not any(fired[-30:])


def test_guide_says_walk_into_the_wind_on_odor():
    g = Guide(signal=OdorSignal(r_clean=50_000))
    # Air moving toward the person's back (wind-to angle pi) means it comes from ahead.
    g.step(Reading(0.0, 50_000, math.pi, 0.0))
    ins = g.step(Reading(0.1, 20_000, math.pi, 0.0))
    assert ins.state == "surge" and "into the wind" in ins.text
    assert abs(ins.turn) < math.radians(10)


def test_cast_instruction_names_the_wind_side():
    # Wind blows toward -x (from +x). Walking toward +y, the wind comes from the right.
    assert "wind on your right" in describe("cast", math.pi / 2, math.pi, 0.0)
    assert "wind on your left" in describe("cast", -math.pi / 2, math.pi, 0.0)


def test_simulated_device_finds_source_with_slow_sensor():
    runs = [run_device_episode(s) for s in range(8)]
    assert sum(r.result.success for r in runs) >= 7


def test_log_round_trips_readings(tmp_path):
    from surgecast.hw.log import read_readings, write_csv

    run = run_device_episode(0)
    path = tmp_path / "session.csv"
    write_csv(str(path), run.readings, run.instructions)
    back = read_readings(str(path))
    assert len(back) == len(run.readings)
    assert abs(back[5].gas_resistance - run.readings[5].gas_resistance) < 1
    assert abs(back[5].heading - run.readings[5].heading) < 1e-3


def test_cli_guide(capsys):
    from surgecast.cli import main

    assert main(["guide", "--seed", "1"]) == 0
    assert "simulated walker" in capsys.readouterr().out


def test_replay_through_live_loop_reproduces_the_session(tmp_path):
    from surgecast.hw import Guide, ReplaySource, run_live
    from surgecast.hw.log import write_csv

    run = run_device_episode(3)
    path = tmp_path / "s.csv"
    write_csv(str(path), run.readings, run.instructions, r_clean=50_000, seed=3)
    src = ReplaySource(str(path))
    assert src.meta == {"r_clean": "50000", "seed": "3"}
    guide = Guide(seed=3, signal=OdorSignal(r_clean=50_000))
    replayed = run_live(src, guide, log_path=str(tmp_path / "again.csv"))
    # Logged values are rounded, so compare decisions, not floats.
    assert [i.state for i in replayed] == [i.state for i in run.instructions]
    assert (tmp_path / "again.csv").read_text().count("\n") == len(run.readings) + 1


def test_cuer_cues_only_on_changes():
    from surgecast.hw import Cuer
    from surgecast.hw.guide import Instruction

    def ins(state, turn, side="left"):
        return Instruction(0.0, state, 0.0, turn, f"x wind on your {side}", 0.0, False)

    c = Cuer()
    cues = [c.update(i) for i in [ins("surge", 0), ins("surge", 0), ins("cast", 1.2, "right"),
                                  ins("cast", 0.1, "right"), ins("cast", -1.2, "left")]]
    assert [x.name if x else None for x in cues] == ["surge", None, "left", None, "right"]


def test_cli_replay(tmp_path, capsys):
    from surgecast.cli import main

    log = tmp_path / "s.csv"
    assert main(["guide", "--seed", "3", "--log", str(log)]) == 0
    capsys.readouterr()
    assert main(["guide", "--replay", str(log)]) == 0
    out = capsys.readouterr().out
    assert "clean-air baseline 50000 ohm" in out and "SURGE" in out
