# Kalibrering

## Bunnlinje

Kalibreringen brukes av ROS Mega-driveren for å oversette encoder ticks til meter
og cmd_vel til PWM. Verdiene lagres i
[`config/robot_calibration.yaml`](../../config/robot_calibration.yaml).

## Nåværende Kalibrering

```yaml
mega_driver:
  swap_sides: true
  left_cmd_sign: 1
  right_cmd_sign: 1
  left_cmd_scale: 1.0
  right_cmd_scale: 0.95
  left_tick_sign: 1
  right_tick_sign: -1
  left_m_per_tick: 5.4302082484863296e-05
  right_m_per_tick: 5.5104008816641413e-05
  track_width_eff_m: 0.24644042850855596
```

[`scripts/robot_calibration_env.py`](../../scripts/robot_calibration_env.py)
eksporterer disse som env-vars for `make pi-bringup`.

## Før Du Kalibrerer

1. Stopp alt annet som bruker Mega-porten.
2. Sørg for at Mega kjører runtime firmware:

```bash
MEGA_SKETCH=mega_keyboard_drive make mega-upload
```

3. Verifiser kontakt:

```bash
make mega-calibrate ARGS="snapshot"
```

## Clean Slate

Nullstill bare verdiene som skal måles på nytt. Behold mapping/sign hvis wiring
ikke er endret.

```yaml
mega_driver:
  left_cmd_scale: 1.0
  right_cmd_scale: 1.0
  left_m_per_tick: 0.0
  right_m_per_tick: 0.0
  track_width_eff_m: 0.35
```

## Steg 1: Straight-trim

Brukes for å få roboten til å kjøre rettere før meter-per-tick måles.

```bash
make mega-calibrate ARGS="straight-trim --pwm 160 --duration 3.0 --left-cmd-scale 1.0 --right-cmd-scale 1.0"
```

Resultat:

- `left_cmd_scale`
- `right_cmd_scale`

## Steg 2: Straight

Mål faktisk kjørt distanse og sett `--distance-m`.

```bash
make mega-calibrate ARGS="straight --pwm 160 --duration 11.15 --left-cmd-scale 1.0 --right-cmd-scale 0.95 --distance-m 4"
```

Resultat:

- `left_m_per_tick`
- `right_m_per_tick`

## Steg 3: Spin

Mål faktisk rotasjon og sett `--angle-deg`.

```bash
make mega-calibrate ARGS="spin --pwm 90 --duration 18.8 --left-cmd-scale 1.0 --right-cmd-scale 0.95 --left-m-per-tick 0.000054302 --right-m-per-tick 0.000055104 --angle-deg 1440"
```

Resultat:

- `track_width_eff_m`

## Nyttige Flagg

```bash
make mega-calibrate ARGS="snapshot"
make mega-calibrate ARGS="straight --help"
make mega-calibrate ARGS="spin --help"
make mega-calibrate ARGS="straight --direction reverse ..."
make mega-calibrate ARGS="spin --direction ccw ..."
make mega-calibrate ARGS="snapshot --no-swap-sides"
MEGA_PORT=/dev/ttyACM0 make mega-calibrate ARGS="snapshot"
```

Default i wrapperen er `--swap-sides`, fordi dagens wiring antar at Mega
`M1/ENC1` og `M2/ENC2` er byttet relativt til robotens venstre/høyre.

Hvis roboten rewires fysisk riktig, bruk `--no-swap-sides` og oppdater
[`config/robot_calibration.yaml`](../../config/robot_calibration.yaml).

## Etter Kalibrering

Test odometri uten EKF først:

```bash
WITH_EKF=0 WITH_MEGA_DRIVER=1 make pi-bringup
ros2 topic echo --once /odom
```

Deretter med EKF:

```bash
WITH_EKF=1 WITH_IMU=1 WITH_MEGA_DRIVER=1 make pi-bringup
ros2 topic echo --once /wheel/odom
ros2 topic echo --once /odom
```
