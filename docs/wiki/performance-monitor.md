# Performance Monitor

## Bunnlinje

`performance_monitor_node` er et valgfritt måleverktøy for fysisk robot. Det
kjører bare når du eksplisitt aktiverer det, og logger:

- topic-rate og siste gap for `/teddy_detector/status`, `/lidar`, `/imu/data`,
  `/odom`, `/cmd_vel` og `/cmd_vel_teddy`
- detector-latency fra statusfelt: `age` og `infer_ms`
- Pi temperatur og throttling hvis `vcgencmd` finnes
- CPU/RAM for relevante ROS-, Python-, GStreamer- og Nav2-prosesser

## Start Med Monitor

På Pi:

```bash
WITH_PERF_MONITOR=1 make pi-bringup
```

Kort alias:

```bash
make pi-perf
```

Uten monitor:

```bash
make pi-bringup
```

Monitoren publiserer også samme linje på:

```bash
ros2 topic echo /performance/summary
```

## Hva Du Skal Se Etter

Eksempel på detector-delen:

```text
/teddy_detector/status 5.20Hz gap=0.10s age=0.170s infer_ms=162ms
```

Tolkning:

| Felt | Betyr | Problem hvis |
|---|---|---|
| `Hz` | faktisk rate på topic | lavere enn forventet |
| `gap` | tid siden siste melding | vokser eller hopper mye |
| `age` | alder på kamera-frame ved detector-publisering | høyere enn `infer_ms` med stor margin |
| `infer_ms` | YOLO inference + postprocess | høy og stabilt nær frame-perioden |

Ved `fps=6` er frame-perioden ca. `167 ms`. Hvis `infer_ms` ligger rundt
`160-280 ms`, er detectoren i praksis hovedflaskehalsen. Hvis `age` blir mye
større enn `infer_ms`, bygger kamera/decode/debugstream backlog.

## Før/Efter Test

Kjør samme scenario to ganger:

1. Baseline:

```bash
WITH_PERF_MONITOR=1 make pi-bringup
```

2. Etter endring:

```bash
WITH_PERF_MONITOR=1 make pi-bringup
```

Sammenlign disse:

- `/teddy_detector/status Hz`
- `age`
- `infer_ms`
- CPU-prosent for `teddy_detector`, `gst-launch`, `mega_driver`, Nav2-noder
- `temp=...`
- `throttled=0x0` eller ikke

## Typiske Konklusjoner

| Observasjon | Sannsynlig flaskehals |
|---|---|
| `teddy_detector` CPU høy, `infer_ms` høy | YOLO/model/imgsz/CPU |
| `age` høyere enn `infer_ms` | kamera/decode/debugstream/backlog |
| `gst-launch` CPU høy | H264 decode/encode eller debugstream |
| `/lidar` Hz lav/ustabil | LiDAR/serial/CPU |
| `/odom` Hz lav/ustabil | Mega serial/encoder polling |
| `get_throttled` ikke `0x0` | undervoltage eller thermal throttling |

## Lav Overhead

Monitoren gjør ikke tracing av hver callback. Den sampler topic-rate og `/proc`
hver `5 s` som standard. Det er godt nok for å finne store flaskehalser uten å
påvirke roboten nevneverdig.
