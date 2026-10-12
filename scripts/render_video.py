"""Render a video of the proposed handheld prototype: an orbit of the 3D model, then the
device in use, driven by a simulated walk (surgecast.hw.run_device_episode).

    python scripts/render_video.py out.mp4 [--seed 3] [--fps 24] [--voice VOICE.onnx --piper PIPER]

Needs matplotlib and ffmpeg. The model is a schematic 3D sketch of docs/layout.svg, in cm.
"""

from __future__ import annotations

import argparse
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.animation import FFMpegWriter  # noqa: E402
from mpl_toolkits.mplot3d import proj3d  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from surgecast.hw import Cuer, run_device_episode  # noqa: E402

W, H, DPI = 12.8, 7.2, 100
BG = "#fafafa"
STATE_COLORS = {"surge": "#d62728", "cast": "#1f77b4", "recover": "#ff7f0e"}
CAPTIONS = {  # short on-screen wording for each cue
    "surge": "odor → walk into the wind",
    "left": "turn left · cast across the wind",
    "right": "turn right · cast across the wind",
    "recover": "lost it → back off downwind",
}

# ---------------------------------------------------------------- geometry


def box(x0, x1, y0, y1, z0, z1):
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    return [v[f] for f in ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7])]


def cyl(cx, cy, z0, z1, r, n=18):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    bot = np.c_[cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z0)]
    top = bot.copy()
    top[:, 2] = z1
    return [np.array([bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]]) for i in range(n)] + [bot, top]


def rotz(faces, ang):
    c, s = math.cos(ang), math.sin(ang)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return [f @ R.T for f in faces]


def vane(phi):
    """Vane in its own frame: nose toward +x (into the wind), tail fin toward -x."""
    parts = box(-9, 6, -0.25, 0.25, 22.7, 23.3)
    parts.append(np.array([[-9, 0, 23], [-12.5, 0, 26.5], [-14.5, 0, 26.5],
                           [-13, 0, 23], [-14.5, 0, 19.5], [-12.5, 0, 19.5]], float))
    parts.append(np.array([[6, -1.0, 23], [9, 0, 23], [6, 1.0, 23]], float))
    parts.append(np.array([[6, 0, 22.0], [9, 0, 23], [6, 0, 24.0]], float))
    return rotz(parts, phi)


def model(heading=0.0, vane_rel=0.0, sensor_hot=False, buzzing=False):
    """Faces and colours of the handheld, yawed to `heading`; vane at `vane_rel` to the body."""
    parts = [
        (box(-8, 8, -5, 5, 0, 6), "#c8e6c9"),  # body: Pi 5 + power bank
        (box(-6, -2.5, -1.8, 1.8, 6, 6.6), "#64b5f6"),  # IMU
        (cyl(0, 0, -15, 0, 2.2), "#e0e0e0"),  # handle
        (cyl(0, 0, -8, -5, 2.45), "#ef5350" if buzzing else "#fff59d"),  # vibration motor
        (box(8, 28, -0.6, 0.6, 2.4, 3.6), "#bdbdbd"),  # boom
        (box(28, 32, -1.8, 1.8, 1.2, 4.8), "#ff7043" if sensor_hot else "#ffcc80"),  # BME688
        (cyl(0, 0, 6, 20, 0.5), "#bdbdbd"),  # mast
        (box(-1.8, 1.8, -1.8, 1.8, 20, 20.5), "#ce93d8"),  # AS5600
        (cyl(0, 0, 20.5, 23, 0.3), "#616161"),  # shaft + magnet
    ]
    faces, colors = [], []
    for fs, c in parts:
        fs = rotz(fs, heading)
        faces += fs
        colors += [c] * len(fs)
    vs = vane(heading + vane_rel)
    faces += vs
    colors += ["#ffab91"] * len(vs)
    return faces, colors


LABELS = [  # (anchor point in body frame, text, label position in axes fraction)
    ((30, 0, 4.8), "BME688 gas sensor\non a forward boom", (0.86, 0.50)),
    ((-12, 0, 24), "wind vane on an\nAS5600 angle sensor", (0.16, 0.86)),
    ((-8, -5, 3), "Raspberry Pi 5\n+ power bank", (0.14, 0.42)),
    ((-4, 0, 6.6), "BNO085 IMU (heading)", (0.15, 0.62)),
    ((0, -2.4, -6.5), "vibration motor\nin the handle", (0.84, 0.20)),
]


def draw_model(ax, heading, vane_rel, sensor_hot=False, buzzing=False, azim=-60, elev=22, labels=0,
               zoom=1.0, symmetric=False):
    ax.cla()
    faces, colors = model(heading, vane_rel, sensor_hot, buzzing)
    ax.add_collection3d(Poly3DCollection(faces, facecolors=colors, edgecolors="#37474f",
                                         linewidths=0.35))
    if symmetric:  # the device yaws freely, so leave room for the boom on every side
        ax.set_xlim(-34, 34)
        ax.set_ylim(-34, 34)
        ax.set_box_aspect((68, 68, 46), zoom=zoom)
    else:
        ax.set_xlim(-20, 34)
        ax.set_ylim(-27, 27)
        ax.set_box_aspect((54, 54, 46), zoom=zoom)
    ax.set_zlim(-16, 30)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_facecolor(BG)
    c, s = math.cos(heading), math.sin(heading)
    for (x, y, z), text, xy_label in LABELS[:labels]:
        # Project the 3D anchor to 2D, then label it from a fixed spot with a leader line.
        px, py, _ = proj3d.proj_transform(c * x - s * y, s * x + c * y, z, ax.get_proj())
        ax.annotate(text, xy=(px, py), xycoords="data", xytext=xy_label, textcoords="axes fraction",
                    fontsize=12, ha="center", va="center", color="#212121",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#9e9e9e"),
                    arrowprops=dict(arrowstyle="-", color="#616161", lw=1.0))


# ---------------------------------------------------------------- scenes


def card(fig, title, sub):
    fig.clf()
    fig.patch.set_facecolor(BG)
    fig.text(0.5, 0.58, title, ha="center", fontsize=30, fontweight="bold", color="#212121")
    fig.text(0.5, 0.45, sub, ha="center", va="top", fontsize=16, color="#555", linespacing=1.6)


def scene_card(fig, writer, fps, seconds, title, sub):
    card(fig, title, sub)
    for _ in range(int(round(seconds * fps))):
        writer.grab_frame()


def scene_orbit(fig, writer, fps, seconds):
    fig.clf()
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.0, 0.17, 1.0, 0.75], projection="3d")
    fig.text(0.5, 0.94, "The proposed handheld: one I²C bus, three sensors, a buzzer you feel",
             ha="center", fontsize=17, fontweight="bold", color="#212121")
    n = int(round(seconds * fps))
    for k in range(n):
        t = k / fps
        labels = min(len(LABELS), int(t / max(seconds / 8, 1.0)) + 1)
        draw_model(ax, 0.0, 0.35 * math.sin(1.3 * t), sensor_hot=(t % 3) < 0.4,
                   buzzing=(t % 4) < 0.3, azim=-65 + 35 * math.sin(2 * math.pi * k / n),
                   elev=18 + 6 * math.sin(t / 2), labels=labels, zoom=1.6)
        writer.grab_frame()


def scene_walk(fig, writer, fps, run, seconds, hold=1.5):
    """Plays the simulated walk over `seconds`, slowed down if the narration needs longer."""
    res, readings, instr = run.result, run.readings, run.instructions
    xmin, xmax, ymin, ymax = res.bounds
    cuer = Cuer()
    cue_at = [cuer.update(ins) for ins in instr]
    rate = min(1.0, res.time / max(seconds - hold, 1e-6))

    fig.clf()
    fig.patch.set_facecolor(BG)
    fig.text(0.5, 0.955, "In use (simulation): following the cues through a box-fan plume",
             ha="center", fontsize=17, fontweight="bold", color="#212121")
    # The bottom ~18% stays clear for closed captions.
    ax_map = fig.add_axes([0.04, 0.47, 0.50, 0.44])
    ax_sig = fig.add_axes([0.04, 0.27, 0.50, 0.11])
    ax_dev = fig.add_axes([0.56, 0.32, 0.43, 0.62], projection="3d")
    caption = fig.text(0.775, 0.275, "", ha="center", fontsize=18, fontweight="bold")
    detail = fig.text(0.775, 0.23, "", ha="center", fontsize=11, color="#424242")
    clock = fig.text(0.04, 0.915, "", fontsize=12, color="#424242")
    speed = "" if rate >= 0.999 else f"   ({rate:.2g}× speed)"

    sig = np.array([i.signal for i in instr])
    ts = np.array([r.t for r in readings])
    n_steps = len(instr)
    n = int(round(seconds * fps))
    last_cue, last_cue_t = None, -9.0
    for k in range(n):
        t = k / fps * rate  # simulation time shown in this frame
        i = min(int(round(t / 0.1)), n_steps - 1)
        for j in range(max(0, i - 3), i + 1):
            if cue_at[j] is not None and ts[j] > last_cue_t:
                last_cue, last_cue_t = cue_at[j], ts[j]
        ins, r = instr[i], readings[i]

        # Map: puffs, fan, source, trail coloured by state, walker + heading arrow.
        ax_map.cla()
        ax_map.set_xlim(xmin, xmax)
        ax_map.set_ylim(ymin, ymax)
        ax_map.set_aspect("equal")
        ax_map.set_facecolor("white")
        ax_map.tick_params(labelsize=9)
        ax_map.set_xlabel("m", fontsize=9)
        puffs = res.frames[min(i, len(res.frames) - 1)]
        ax_map.scatter(puffs[:, 0], puffs[:, 1], s=9, color="#9467bd", alpha=0.35, lw=0)
        ax_map.add_patch(plt.Rectangle((0.05, -0.9), 0.25, 1.8, color="#90a4ae"))
        ax_map.text(0.18, 1.1, "fan", ha="center", fontsize=10)
        ax_map.plot(*res.source, marker="*", color="gold", markeredgecolor="k", markersize=18)
        ax_map.text(res.source[0], -0.55, "odor\nsource", ha="center", va="top", fontsize=9)
        path = res.path[: i + 2]
        start = 0
        for j in range(1, i + 2):
            if j == i + 1 or instr[j].state != instr[start].state:
                seg = path[start : j + 1]
                ax_map.plot(seg[:, 0], seg[:, 1], color=STATE_COLORS.get(instr[start].state, "k"), lw=2.2)
                start = j
        p = res.path[i + 1]
        ax_map.plot(*p, "o", color="k", markersize=8)
        ax_map.arrow(p[0], p[1], 0.45 * math.cos(r.heading), 0.45 * math.sin(r.heading),
                     head_width=0.15, color="k")
        for st, c in STATE_COLORS.items():
            ax_map.plot([], [], color=c, lw=2.5, label=st)
        ax_map.legend(loc="upper right", fontsize=9)

        # Gas signal strip: the slow sensor, with onsets marked.
        ax_sig.cla()
        ax_sig.plot(ts[: i + 1], sig[: i + 1], color="#e65100", lw=1.8)
        on = [ts[j] for j in range(i + 1) if instr[j].detected]
        ax_sig.vlines(on, 0, max(sig.max(), 0.1), color="#ffccbc", lw=2, zorder=0)
        ax_sig.set_xlim(0, res.time)
        ax_sig.set_ylim(0, sig.max() * 1.1 + 0.05)
        ax_sig.set_ylabel("gas\nsignal", fontsize=9)
        ax_sig.tick_params(labelsize=8)
        ax_sig.set_xlabel("s   (shaded = odor onset detected)", fontsize=9)

        # Device: yawed to the walker's heading, vane nose into the wind.
        vane_rel = r.wind_angle + math.pi
        buzzing = (ts[i] - last_cue_t) < 0.6
        draw_model(ax_dev, r.heading, vane_rel, sensor_hot=ins.detected, buzzing=buzzing,
                   azim=-90, elev=28, zoom=1.35, symmetric=True)

        if last_cue is not None:
            caption.set_text(f"{last_cue.pattern}   {CAPTIONS[last_cue.name]}")
            caption.set_color(STATE_COLORS.get(ins.state, "#212121"))
        detail.set_text(ins.text)
        done = i == n_steps - 1 and res.success
        clock.set_text(f"t = {ts[i]:4.1f} s{speed}   " + ("REACHED THE SOURCE" if done else ""))
        writer.grab_frame()


# ---------------------------------------------------------------- narration and captions


def narration(run) -> dict[str, list[tuple[str, str]]]:
    """Per scene: (what the voice says, what the caption shows)."""
    secs = round(run.result.time)
    return {
        "title": [
            ("This is surgecast: a handheld guide that finds the source of a smell, the way a moth does.",) * 2,
        ],
        "orbit": [
            ("A Raspberry Pi reads three sensors on a single I squared C bus.",
             "A Raspberry Pi reads three sensors on a single I²C bus."),
            ("A gas sensor sits on a forward boom, upwind of the Pi's heat.",) * 2,
            ("A wind vane on a magnetic angle sensor reads which way the air is moving, "
             "and an I M U tracks which way you're facing.",
             "A wind vane on a magnetic angle sensor reads which way the air is moving, "
             "and an IMU tracks which way you're facing."),
            ("A motor in the handle buzzes each cue, so you feel it instead of reading it.",) * 2,
        ],
        "how": [
            ("When odor arrives, it tells you to walk into the wind.",) * 2,
            ("When the odor is lost, it has you cast across the wind until you find it again.",) * 2,
        ],
        "walk": [
            ("Here's a simulated walk through a box fan plume, with a slow gas sensor "
             "and a person reacting to each cue.",
             "Here's a simulated walk through a box-fan plume, with a slow gas sensor "
             "and a person reacting to each cue."),
            ("Red stretches are surges upwind. Blue zigzags are casts across the wind.",) * 2,
            ("The slow sensor's level barely changes, so the guide fires on odor onsets, "
             "the shaded marks, not on the level.",) * 2,
            (f"In this run, the walker reaches the source in about {secs} seconds.",) * 2,
        ],
        "end": [
            ("The design and the simulation are open source. The sensors haven't been built yet.",) * 2,
        ],
    }


def synthesize(lines, piper: str, voice: str, workdir: str) -> list[tuple[str, float]]:
    """Speak each line to a wav with Piper; returns (path, seconds) per line."""
    import os
    import subprocess
    import wave

    out = []
    for n, text in enumerate(lines):
        path = os.path.join(workdir, f"line{n:02d}.wav")
        subprocess.run([piper, "-m", voice, "-f", path], input=text.encode(), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(path) as w:
            out.append((path, w.getnframes() / w.getframerate()))
    return out


def split_cue(start: float, dur: float, text: str, max_chars: int = 84) -> list[tuple[float, float, str]]:
    """Break a long line into caption cues of at most two short lines, timed by length."""
    import textwrap

    chunks = textwrap.wrap(text, max_chars)
    total = sum(len(c) for c in chunks)
    cues, t = [], start
    for c in chunks:
        d = dur * len(c) / total
        cues.append((t, t + d, c))
        t += d
    return cues


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_captions(cues, srt_path: str, vtt_path: str) -> None:
    import textwrap

    srt, vtt = [], ["WEBVTT", ""]
    for n, (start, end, text) in enumerate(cues, 1):
        body = "\n".join(textwrap.wrap(text, 44))
        srt += [str(n), f"{srt_time(start)} --> {srt_time(end)}", body, ""]
        vtt += [f"{srt_time(start).replace(',', '.')} --> {srt_time(end).replace(',', '.')}", body, ""]
    with open(srt_path, "w") as f:
        f.write("\n".join(srt))
    with open(vtt_path, "w") as f:
        f.write("\n".join(vtt))


def mix_audio(placed, total: float, path: str) -> None:
    """Lay each (wav path, start seconds) onto one silent mono track."""
    import wave

    rate, track = None, None
    for wav, start in placed:
        with wave.open(wav) as w:
            if rate is None:
                rate = w.getframerate()
                track = np.zeros(int(total * rate) + 1, dtype=np.int16)
            clip = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        a = int(start * rate)
        clip = clip[: max(0, len(track) - a)]
        track[a : a + len(clip)] = clip
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(track.tobytes())


# ---------------------------------------------------------------- main

BASE = {"title": 2.5, "orbit": 11.0, "how": 3.0, "end": 2.5}  # seconds without narration
LEAD, GAP, TAIL = 0.4, 0.35, 0.7  # around narration lines within a scene


def main():
    import os
    import subprocess
    import tempfile

    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--voice", help="Piper voice model (.onnx) to narrate with; omit for a silent video")
    ap.add_argument("--piper", default="piper", help="path to the piper executable")
    args = ap.parse_args()

    run = run_device_episode(args.seed, record_every=1)
    scenes = ["title", "orbit", "how", "walk", "end"]
    base = dict(BASE, walk=run.result.time + 1.5)
    durations, placed, cues = dict(base), [], []
    tmp = tempfile.mkdtemp(prefix="surgecast-video-")

    if args.voice:
        script = narration(run)
        spoken = synthesize([sp for sc in scenes for sp, _ in script[sc]], args.piper, args.voice, tmp)
        k, t0 = 0, 0.0
        for sc in scenes:
            t = t0 + LEAD
            for _, cap in script[sc]:
                wav, dur = spoken[k]
                k += 1
                placed.append((wav, t))
                cues += split_cue(t, dur, cap)
                t += dur + GAP
            durations[sc] = max(base[sc], t - GAP + TAIL - t0)
            t0 += durations[sc]

    fig = plt.figure(figsize=(W, H), dpi=DPI)
    video = os.path.join(tmp, "video.mp4") if args.voice else args.out
    writer = FFMpegWriter(fps=args.fps, codec="libx264",
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "23"])
    with writer.saving(fig, video, DPI):
        scene_card(fig, writer, args.fps, durations["title"], "surgecast · handheld odor-source guide",
                   "proposed prototype: a moth's surge-and-cast search in your hand")
        scene_orbit(fig, writer, args.fps, durations["orbit"])
        scene_card(fig, writer, args.fps, durations["how"], "How it's used",
                   "odor onset → walk into the wind  ·  lost it → cast across the wind\n"
                   "the vane, IMU and gas sensor decide; the handle buzzes the cue")
        scene_walk(fig, writer, args.fps, run, durations["walk"])
        scene_card(fig, writer, args.fps, durations["end"], "github.com/ebarber79/surgecast",
                   "simulation and design sketch · sensors not yet built")

    if args.voice:
        total = sum(durations[sc] for sc in scenes)
        audio = os.path.join(tmp, "narration.wav")
        mix_audio(placed, total, audio)
        stem = os.path.splitext(args.out)[0]
        write_captions(cues, stem + ".srt", stem + ".vtt")
        # Closed captions: a soft subtitle track, on by default, plus .srt/.vtt sidecars.
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-i", stem + ".srt",
                        "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "96k", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
                        "-disposition:s:0", "default", args.out], check=True)
        print(f"wrote {args.out} (+ {stem}.srt, {stem}.vtt), {total:.1f} s")
    else:
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
