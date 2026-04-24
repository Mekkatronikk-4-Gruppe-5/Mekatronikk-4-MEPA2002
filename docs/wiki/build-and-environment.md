# Bygg og Miljø

## Bunnlinje

PC/sim bygges normalt direkte med colcon. Pi/runtime bygges normalt inne i Docker.
Source order betyr noe utenfor Docker.

## Host / PC Build

```bash
cd ~/Mekatronikk-4-MEPA2002
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Bruk dette for:

- Gazebo simulering.
- RViz.
- PC UDP camera bridge.
- PC ROS keyboard teleop.

## Pi / Docker Build

```bash
cd ~/Mekatronikk-4-MEPA2002
make build
make ws
```

| Kommando | Effekt |
|---|---|
| `make build` | `docker compose build` |
| `make ws` | Kjører [`scripts/ws_build.sh`](../../scripts/ws_build.sh) i container |
| `make shell` | Åpner shell i container |
| `make up` | Starter compose service detached |
| `make down` | Stopper compose service |

Kjør `make build` etter endringer i:

- [`docker/Dockerfile`](../../docker/Dockerfile)
- Docker dependencies.

Kjør `make ws` etter endringer i:

- ROS Python/C++ kode.
- Launch-filer.
- Package metadata.
- Config som installeres av `robot_bringup`.

## Docker Image

[`docker/Dockerfile`](../../docker/Dockerfile) bruker:

- Base image: `ros:jazzy-ros-base`
- ROS packages:
  - `ros-jazzy-navigation2`
  - `ros-jazzy-cv-bridge`
  - `ros-jazzy-robot-localization`
  - `ros-dev-tools`
- Python venv i `/opt/venv`
- Python packages:
  - `numpy==1.26.4`
  - `pyserial==3.5`
  - `ultralytics==8.4.12`
  - `ncnn==1.0.20260114`
  - `lgpio`
  - `adafruit-blinka`
  - `adafruit-circuitpython-bno08x`
  - `adafruit-extended-bus`

## Workspace Build Script

[`scripts/ws_build.sh`](../../scripts/ws_build.sh):

1. Fjerner stale Python package state i `/ws/build/<pkg>` og `/ws/install/<pkg>`.
2. Kjører `colcon build --symlink-install`.
3. Patcher console script shebang fra `/usr/bin/python3` til `/opt/venv/bin/python3`.

Dette er nødvendig fordi containerens pip-pakker ligger i venv.

## Source Order Uten Docker

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Hvis du får `package not found` eller gamle launch-filer:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## ROS Nettverk

ROS discovery styres av [`scripts/ros_discovery_env.sh`](../../scripts/ros_discovery_env.sh).

Variabler:

| Variabel | Bruk |
|---|---|
| `ROS_DOMAIN_ID` | DDS domain, default `0` |
| `ROS_AUTOMATIC_DISCOVERY_RANGE` | Discovery scope |
| `ROS_STATIC_PEERS` | Peer-IP mellom Pi og PC |

Manuell sjekk:

```bash
eval "$(bash scripts/ros_discovery_env.sh pc gruppe5pi5)"
env | grep ROS_
```
