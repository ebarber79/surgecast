# v1 hardware: handheld guide

A handheld device that tells you which way to walk to find an odor source, using the same
surge-cast logic as the simulation. First test: indoors, a box fan for wind and an alcohol
swab or a dish of vinegar as the source.

```
 gas sensor ──┐
 wind vane  ──┼── I²C ── Raspberry Pi ── Guide ── "Walk into the wind" / "Walk across…"
 IMU (yaw)  ──┘                                     (tones or vibration, see below)
```

## Parts (~$60–80)

| part | what it does | I²C address | notes |
|---|---|---|---|
| **BME688** breakout (Adafruit or Pimoroni) | Gas resistance; falls as alcohol/VOCs rise | 0x76 or 0x77 (board-dependent) | Metal-oxide sensor with a seconds-scale response. The rise detector handles that (see below). |
| **AS5600** magnetic angle sensor + diametric magnet | Reads the angle of a small wind vane | 0x36 (fixed) | Many cheap boards default to 5 V. Check that yours runs at 3.3 V before wiring it to the Pi. |
| **BNO085** IMU breakout | Device heading (yaw) | 0x4A (or 0x4B) | Use the gyro-only "game rotation vector", not the compass: indoors, and next to the vane's magnet, a magnetometer is unreliable. |
| Vibration motor or piezo buzzer | Feedback you don't have to read | GPIO | See *Feedback* below. |
| STEMMA QT / Qwiic cables, jumper wires | Daisy-chain the I²C boards | | |
| USB-C power bank | Makes it handheld | | |

All three sensors have different addresses, so they share one I²C bus.

**Wind vane:** a light card or foam fin on a low-friction shaft, with the magnet glued to the
shaft end 0.5–3 mm above the AS5600 chip. It has to swing reliably in ~1 m/s of fan air.
Making that work is the main mechanical job.

## Wiring

Pi header I²C (bus 1): 3V3 → pin 1, SDA → pin 3, SCL → pin 5, GND → pin 6. Chain the three
boards. The vibration motor needs a transistor (or a motor driver board) on a GPIO pin; don't
drive it straight from the pin.

Enable the header bus (it's off on this Pi today), then check that the boards show up:

```bash
sudo raspi-config nonint do_i2c 0   # then reboot
i2cdetect -y 1                      # expect 0x36, 0x4a and 0x76/0x77
```

## What the simulation already tells us

`surgecast guide` runs this exact software path on a simulated device: a slow, noisy gas
sensor, noisy vane and IMU, and a person following the instructions with a reaction delay.

- **Detect odor onsets, not levels.** With a 2 s sensor response, a level threshold drops
  surge-cast to 40–60% success. Firing on a fast rise keeps it at ~97–100%, even with an 8 s
  sensor. Insect odor neurons work the same way.
- **Recover from overshoot.** Indoors the source has the fan or a wall behind it. After 10 s
  without odor, the guide backs off downwind while sweeping. Without that, ~1 in 3 simulated
  walks ended pinned behind the source.
- **Your reaction time matters more than the sensor's.** Going from a 0.7 s to a 1.5 s
  reaction roughly doubles the search time, while a sensor 4× slower costs only a few seconds.

Simulated results, 50 runs each:

| sensor response | reaction 0.7 s | reaction 1.5 s |
|---|---|---|
| 1 s | 100%, 14 s | 100%, 25 s |
| 2 s | 100%, 15 s | 100%, 32 s |
| 8 s | 100%, 20 s | 100%, 27 s |

## Feedback

Because reaction time dominates, instructions should register without reading: for example,
one buzz for "odor, go into the wind" and a left/right pattern for which way to cast. A screen
or spoken text can show the details, but shouldn't be what you have to wait for.

## Logging

Every session can be saved with `--log session.csv`. The real device will use the same format,
so a real walk can be replayed through a retuned guide (`surgecast.hw.log.read_readings`) and
compared with the simulation.

## Still to do when the parts arrive

1. Drivers for the three sensors, each checked against the real chip (not written yet).
2. Calibrate the vane zero against the device's forward direction, and the clean-air gas
   resistance.
3. Measure the BME688's actual response time and achievable sample rate, then tune
   `RiseDetector.threshold` on real logs.
4. A `surgecast guide --device` mode that runs the loop live with buzzer feedback.
5. Possible issue: on older Pis, the BNO085 has trouble with I²C clock stretching. If it misbehaves on the
   Pi 5, lower the bus speed or use its UART-RVC mode.
