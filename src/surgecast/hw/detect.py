"""Turn raw metal-oxide gas readings into odor detections.

MOX sensors like the BME688 respond over seconds, smearing each odor patch into a slow bump.
Thresholding the level then fires late and stays on long after the patch has passed. In
simulation that drops surge-cast's success from ~100% to 40-60% at a 2 s sensor time
constant. Detecting *onsets*, the signal rising quickly, restores it to ~97%. Insect olfactory
receptor neurons are phasic for the same reason: they report the arrival of odor, not its level.
"""

from __future__ import annotations

import math


class OdorSignal:
    """Gas resistance (ohm) -> odor signal s = ln(R_clean / R), about 0 in clean air.

    MOX resistance falls as reducing gases (alcohol, VOCs) rise. The clean-air baseline is
    tracked automatically: it follows rises in resistance quickly (air clearing) and falls
    only slowly (sensor drift), so a long odor exposure isn't absorbed into the baseline.
    """

    def __init__(self, rise_tau: float = 2.0, drift_tau: float = 120.0, r_clean: float | None = None):
        self.rise_tau = rise_tau
        self.drift_tau = drift_tau
        # Pass a clean-air calibration if you have one; otherwise the first reading is used.
        self.r_clean = r_clean

    def update(self, resistance: float, dt: float) -> float:
        if self.r_clean is None:
            self.r_clean = resistance
        tau = self.rise_tau if resistance > self.r_clean else self.drift_tau
        self.r_clean += (resistance - self.r_clean) * min(dt / tau, 1.0)
        return max(0.0, math.log(self.r_clean / resistance))


class RiseDetector:
    """Fires while the smoothed odor signal rises faster than `threshold` per second."""

    def __init__(self, threshold: float = 0.15, smooth_tau: float = 0.3):
        self.threshold = threshold
        self.smooth_tau = smooth_tau
        self.y: float | None = None
        self.rate = 0.0

    def update(self, signal: float, dt: float) -> bool:
        if self.y is None or dt <= 0:
            self.y = signal
            return False
        prev = self.y
        self.y += (signal - self.y) * min(dt / self.smooth_tau, 1.0)
        self.rate = (self.y - prev) / dt
        return self.rate > self.threshold
