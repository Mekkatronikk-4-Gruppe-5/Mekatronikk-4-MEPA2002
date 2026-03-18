# Mekatronikk-4-MEPA2002

Kort bruk av repoet.

## Formål

1. Simulering av robot (Gazebo + ROS 2).
2. Kjøring på fysisk robot (Pi5 + Docker + ROS 2).
3. Teddy-deteksjon (`/teddy_detector/status`).

## Bygg workspace (host)

| Kommando | Hva den gjør |
|---|---|
| `source /opt/ros/jazzy/setup.bash` | Laster ROS 2 Jazzy-miljø. |
| `cd ~/Mekatronikk-4-MEPA2002` | Går til repoet. |
| `colcon build --symlink-install` | Bygger pakkene i workspace. |
| `source install/setup.bash` | Laster de bygde pakkene i shellen. |

## Simulering (PC)

| Kommando | Hva den gjør |
|---|---|
| `make sim` | Starter simulering med Gazebo GUI + RViz. |
| `make sim-headless` | Starter simulering uten GUI. |
| `make sim-topics` | Viser sentrale sim-topics. |

## Nav2 i simulering

| Kommando | Hva den gjør |
|---|---|
| Terminal A: `make sim` | Starter selve simuleringen. |
| Terminal B: `make sim-nav2` | Starter Nav2 mot kart og params i repoet. |
| `ros2 launch robot_bringup nav2_stack.launch.py use_sim_time:=true map:=$PWD/maps/my_map.yaml params_file:=$PWD/config/nav2_params.yaml` | Direkte Nav2-launch (samme som `make sim-nav2`). |

I RViz:

1. Sett `Fixed Frame` til `map`.
2. Klikk `2D Pose Estimate`.
3. Klikk `2D Goal Pose`.

Merk:

1. `Timed out waiting for transform ... chassis to map` er normalt til `2D Pose Estimate` er satt.
2. Alle terminaler må ha samme `ROS_DOMAIN_ID`.

## Fysisk robot (Pi + PC)

Målet er at Pi-en kjører roboten autonomt, mens PC-en bare kobler seg på for RViz og debugging.

### Første gangs oppsett

Pi:

| Kommando | Hva den gjør |
|---|---|
| `ssh gruppe5@gruppe5pi5` | Logger inn på Pi. |
| `cd ~/Mekatronikk-4-MEPA2002` | Går til repoet på Pi. |
| `make build` | kun ved første gang eller etter Docker-endringer. Bygger Docker-image. |
| `make ws` | Bygger ROS-workspace i container. Kjør igjen hvis ROS-kode er endret. |

PC:

| Kommando | Hva den gjør |
|---|---|
| `source /opt/ros/jazzy/setup.bash` | Laster ROS 2 Jazzy-miljø. |
| `cd ~/Mekatronikk-4-MEPA2002` | Går til repoet på PC. |
| `colcon build --symlink-install` | Bygger PC-workspace. Kjør igjen hvis lokal ROS-kode er endret. |
| `source install/setup.bash` | Laster de bygde pakkene i shellen. |

### Standard workflow

Dette er den anbefalte oppskriften før dere har odometri og aktiv Nav2-bruk.

Pi, via SSH fra samme PC som skal bruke RViz:

```bash
cd ~/Mekatronikk-4-MEPA2002
WITH_NAV2=0 WITH_TEDDY=1 make pi-bringup
```

PC:

```bash
cd ~/Mekatronikk-4-MEPA2002
make pc-teddy-rviz
```

Dette skjer automatisk:

1. Pi finner PC-IP fra SSH-sesjonen.
2. Pi setter `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE` og `ROS_STATIC_PEERS`.
3. Pi starter samlet bringup i Docker med `robot_state_publisher`, LiDAR og teddy-detektor.
4. Pi sender annotert YOLO-video over UDP til PC hvis `teddy_detector.stream_debug_video: true` i [config/camera_params.yaml](/home/emiliam/Mekatronikk-4-MEPA2002/config/camera_params.yaml).
5. PC setter ROS discovery mot Pi automatisk, starter lokal UDP->ROS bridge for YOLO-debugbildet og åpner RViz med [pre_odom_lidar.rviz](/home/emiliam/Mekatronikk-4-MEPA2002/src/robot_bringup/rviz/pre_odom_lidar.rviz).

I denne RViz-konfigen er standarden:

1. `Fixed Frame = chassis`
2. `/lidar` vises som LaserScan
3. `/teddy_detector/debug_image` vises som Image
4. `TF` er dempet for å unngå støy før dere har odom

### Nyttige varianter

Pi:

| Kommando | Hva den gjør |
|---|---|
| `make pi-bringup` | Standard bringup med default-verdier i scriptet. |
| `WITH_NAV2=0 make pi-bringup` | Starter uten Nav2. Dette er anbefalt før dere har odometri. |
| `WITH_TEDDY=1 make pi-bringup` | Starter teddy-detektor på Pi. |
| `WITH_TEDDY=1 WITH_CAMERA_RVIZ=1 make pi-bringup` | Starter teddy på Pi og sender også rå H264-kamerastrøm til PC på port `5601`. |
| `PC_HOST=192.168.10.42 make pi-bringup` | Overstyr automatisk valgt PC-IP for ROS discovery og debug-stream. |

PC:

| Kommando | Hva den gjør |
|---|---|
| `make pc-teddy-rviz` | Standard: viser LiDAR + annotert YOLO-bilde i RViz. |
| `make pc-camera-rviz` | Valgfritt: viser rå `/camera` i RViz via lokal UDP->ROS bridge på PC. |
| `make pc-teddy-rviz PI_HOST=192.168.10.55` | Bruk Pi-IP direkte hvis `gruppe5pi5` ikke løses på PC. |


### Fast SSH-navn for hele gruppa

Alle scripts antar at Pi kan nås som `gruppe5pi5`.

logg inn pi med ssh med:

```bash
ssh gruppe5@gruppe5pi5
```
passordet er 

```bash
qwerty
```

## Vision og LiDAR

| Kommando | Hva den gjør |
|---|---|
| `make lidar-setup` | Henter/bygger LiDAR-driver i workspace. |
| `make lidar-test` | Kjører enkel LiDAR-smoketest. |

Guide for LiDAR i RViz: [docs/lidar_rviz.md](/home/emiliam/Mekatronikk-4-MEPA2002/docs/lidar_rviz.md)

### Kamera- og YOLO-parametre

Kamera- og YOLO-parametre styres fra [config/camera_params.yaml](/home/emiliam/Mekatronikk-4-MEPA2002/config/camera_params.yaml).

Kort oppdeling:

1. `camera_stream.*` påvirker signalet som går inn til teddy-detektor på Pi.
2. `camera_stream.width/height/fps/bitrate_bps/intra/low_latency/denoise/...` er stedet å tune bildekvalitet og artifacts for YOLO-inputen.
3. `teddy_detector.*` påvirker YOLO-parametre og den annoterte debug-videoen som sendes til PC.
4. `teddy_detector.debug_stream_*` påvirker bare debug-visningen på PC, ikke hva YOLO faktisk ser.

### Kamera drift på Pi

| Kommando | Hva den gjør |
|---|---|
| `make camera-reload` | Restarter bare kamerastreamen med nye `camera_stream.*`-verdier fra [config/camera_params.yaml](/home/emiliam/Mekatronikk-4-MEPA2002/config/camera_params.yaml). Bruk denne etter tuning av farger, bitrate, intra, denoise osv. |
| `make camera-stop` | Stopper kamerastream/supervisor hvis noe henger igjen. Dette er en recovery-knapp, ikke vanlig workflow. |

### Arduino Mega upload fra Pi

Arduino-sketchene i repoet kan lastes opp direkte fra Pi-host. Dette bør kjøre på hosten, ikke i Docker, siden dagens container bare mapper inn LiDAR-porten og ikke Mega over USB.

hvis du skal oppdatere filen på megaen etter git pull bruk:

```bash
make mega-upload
```
hvis du skal endre filen som skal lastes opp. se eksempel:
```bash
MEGA_SKETCH=mega_keyboard_drive make mega-upload
```

Dette gjør:

1. finner `Mega`-porten automatisk (`/dev/serial/by-id`, `/dev/ttyACM*` eller `/dev/ttyUSB*`)
2. bygger med `arduino:avr:mega`
3. bruker en midlertidig build-katalog i `/tmp`
4. laster opp direkte fra Pi-host til Mega over USB

Hvis du vil overstyre port eller board:

```bash
MEGA_PORT=/dev/ttyACM0 make mega-upload
MEGA_FQBN=arduino:avr:mega make mega-upload
```

### Arduino Mega keyboard drive

Hvis du vil kjøre roboten manuelt med tastatur, bruk keyboard-firmwaren på Mega og start teleop fra Ubuntu-maskinen din, ikke fra SSH-terminalen på Pi.

```bash
make pc-mega-keyboard
```

Dette gjør:

1. åpner et lite GUI-vindu på Ubuntu-PC-en
2. kobler til Pi over SSH
3. starter en liten serial-bro på Pi som snakker med Mega over USB
4. sender tastaturkommandoer videre til Mega i sanntid

Taster i GUI-vinduet:

1. hold `W` for fremover
2. hold `S` for bakover
3. hold `A` og `D` for sving
4. `E` / `Q` øker og senker kjørehastighet
5. `P` / `O` øker og senker svinghastighet
6. `SPACE` stopper
7. `-` avslutter

Merk:

1. `make mega-keyboard` finnes fortsatt som terminal-variant, men anbefales ikke over SSH siden vanlige terminaler ikke håndterer samtidige hold av flere taster like robust som GUI-varianten.
2. Hvis GUI-broen faller ut, prøver den å koble opp SSH på nytt automatisk.


## Pi ytelse (host, ikke Docker)

| Kommando | Hva den gjør |
|---|---|
| `cpupower frequency-info` | Viser tilgjengelige governors og aktiv policy. |
| `sudo cpupower frequency-set -g performance` | Setter CPU i maks ytelse-modus. |
| `sudo cpupower frequency-set -g ondemand` | Setter CPU tilbake til dynamisk modus. |
| `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | Verifiserer aktiv governor. |
| `watch -n1 'vcgencmd measure_temp; vcgencmd measure_clock arm; vcgencmd get_throttled'` | Overvåker temperatur, klokke og throttling live. |


## Rydd lagring på Pi

| Kommando | Hva den gjør |
|---|---|
| `df -h` | Viser total diskbruk på Pi. |
| `docker system df` | Viser hvor mye plass Docker bruker. |
| `du -h --max-depth=1 ~/Mekatronikk-4-MEPA2002` | Viser store mapper i repoet. |
| `docker system prune -af` | Fjerner ubrukte containere/nettverk/images. |
| `docker builder prune -af` | Fjerner docker build-cache. |
| `sudo apt clean` | Fjerner apt-pakke-cache. |
| `sudo rm -rf /var/lib/apt/lists/*` | Fjerner lokale apt-indekser. |
| `rm -rf ~/Mekatronikk-4-MEPA2002/build ~/Mekatronikk-4-MEPA2002/log` | Fjerner lokale build/log-mapper. |
| `rm -rf ~/Mekatronikk-4-MEPA2002/install` | Valgfritt: frigjør mer, men krever ny `make ws`. |
