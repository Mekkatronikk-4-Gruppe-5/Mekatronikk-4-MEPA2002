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

### Encoder-kalibrering på Pi-host

Kalibrering mot Mega kjøres på Pi-hosten, ikke i Docker. Dette verktøyet er laget for `mega_keyboard_drive`-firmwaren og bruker de eksisterende kommandoene `ENC1`, `ENC2`, `RESET ENC1`, `RESET ENC2`, `STATE`, `BOTH` og `STOP`.

Ta et snapshot av dagens tellere:

```bash
make mega-calibrate ARGS="snapshot"
```

Kjør en rettlinjet kalibreringsrun og regn ut meter per tick etter at du har målt faktisk distanse:

```bash
make mega-calibrate ARGS="straight --pwm 90 --duration 1.6 --distance-m 2.0"
```

Kalibreringsverktøyet antar nå som standard at venstre/høyre er byttet mellom Mega (`M1/ENC1`, `M2/ENC2`) og roboten. Hvis dere senere rewierer riktig fysisk, bruk `--no-swap-sides`.

Dette:

1. verifiserer at Mega kjører `mega_keyboard_drive`
2. resetter encoderne
3. kjører begge belter likt i valgt retning med watchdog-sikre repetisjoner
4. stopper roboten og skriver ut encoder-delta
5. beregner `left_m_per_tick` og `right_m_per_tick` hvis `--distance-m` er satt

Hvis roboten trekker til en side, kan dere kjøre en egen trim-test som foreslår `LEFT_CMD_SCALE` og `RIGHT_CMD_SCALE` for Mega-driveren:

```bash
make mega-calibrate ARGS="straight-trim --pwm 90 --duration 10.4 --left-m-per-tick 0.000057460 --right-m-per-tick 0.000051824"
```

Dette:

1. kjører samme type rettlinjetest
2. sammenligner venstre og høyre bevegelse
3. foreslår nye `left_cmd_scale` og `right_cmd_scale` uten å endre encoder-odometrien

De samme trim-verdiene kan deretter brukes direkte i `straight` og `spin`, for eksempel:

```bash
make mega-calibrate ARGS="straight --pwm 90 --duration 10.4 --left-cmd-scale 0.91 --right-cmd-scale 1.0 --distance-m 2.0"
```

Kjør en spinn-kalibrering når du allerede har meter-per-tick og har målt faktisk rotasjon:

```bash
make mega-calibrate ARGS="spin --pwm 75 --duration 1.2 --angle-deg 360 --left-m-per-tick 0.000500000 --right-m-per-tick 0.000505000"
```

Dette beregner `track_width_eff_m`, som er den effektive sporvidden dere bør bruke i encoder-odometri for en belterobot.

Nyttige flagg:

1. `--direction reverse` på `straight` for bakoverkalibrering
2. `--left-cmd-scale` og `--right-cmd-scale` kan brukes på `straight`, `straight-trim` og `spin`
3. `--direction ccw` på `spin` for motsatt spinnretning
4. `MEGA_PORT=/dev/ttyACM0 make mega-calibrate ARGS="snapshot"` hvis port-auto-detect bommer

Kalibreringsscriptet skriver nå som standard resultatene tilbake til [robot_calibration.yaml](/home/emiliam/Mekatronikk-4-MEPA2002/config/robot_calibration.yaml). Det betyr at:

1. `straight-trim` oppdaterer `left_cmd_scale` og `right_cmd_scale`
2. `straight --distance-m ...` oppdaterer `left_m_per_tick` og `right_m_per_tick`
3. `spin --angle-deg ...` oppdaterer `track_width_eff_m`

Hvis dere bare vil teste uten å lagre, bruk `--no-write-config`.

### ROS Mega-driver på Pi

Repoet har nå også en ROS 2 Mega-driver som kan brukes i Docker-bringup. Den:

1. abonnerer på `/cmd_vel`
2. sender `BOTH` og `STOP` til Mega over serial
3. publiserer rå hjulodometri som `/odom` når EKF er av
4. publiserer rå hjulodometri som `/wheel/odom` når EKF er på

Eksempel:

```bash
WITH_IMU=1 WITH_MEGA_DRIVER=1 \
SWAP_SIDES=1 \
LEFT_CMD_SCALE=1.000000 \
RIGHT_CMD_SCALE=1.000000 \
LEFT_M_PER_TICK=0.000500000 \
RIGHT_M_PER_TICK=0.000505000 \
TRACK_WIDTH_EFF_M=0.340000000 \
make pi-bringup
```

Merk:

1. `pc-mega-keyboard` og ROS Mega-driveren kan ikke bruke samme serial-port samtidig.
2. Hvis `LEFT_M_PER_TICK` og `RIGHT_M_PER_TICK` står på `0.0`, kjører driveren fortsatt motorstyring fra `/cmd_vel`, men `/odom` blir deaktivert.
3. `MEGA_PORT=/dev/ttyACM0` og `MEGA_BAUDRATE=115200` kan overstyres i samme kommando hvis auto-defaulten ikke passer.
4. `LEFT_CMD_SCALE` og `RIGHT_CMD_SCALE` kan brukes til å få roboten til å gå rettere uten å endre encoder-odometrien. Start med små justeringer som `LEFT_CMD_SCALE=0.98` eller `RIGHT_CMD_SCALE=0.98`.
5. `SWAP_SIDES=1` er nå default i Pi-bringup og bytter venstre/høyre mapping i Mega-driveren. Hvis dere rewierer fysisk senere, kan dere overstyre med `SWAP_SIDES=0`.
6. Pi-bringup leser nå default kalibreringsverdier fra [robot_calibration.yaml](/home/emiliam/Mekatronikk-4-MEPA2002/config/robot_calibration.yaml), så dere slipper å lime inn alle `LEFT_*`/`RIGHT_*`-verdiene hver gang. Manuelle env-vars overstyrer fortsatt YAML-fila hvis dere vil teste noe midlertidig.

### `robot_localization` EKF på Pi

Repoet har nå også en enkel EKF-bane for å flette rå hjulodometri fra Mega med `/imu/data` fra BNO085.

Når `WITH_EKF=1`:

1. Mega-driveren remappes til å publisere rå odometri på `/wheel/odom`
2. Mega-driveren slutter å publisere `odom -> chassis` TF direkte
3. `robot_localization` leser `/wheel/odom` og `/imu/data`
4. EKF publiserer filtrert `/odom` og `odom -> chassis`

Eksempel:

```bash
WITH_IMU=1 WITH_MEGA_DRIVER=1 WITH_EKF=1 \
LEFT_CMD_SCALE=0.937 \
RIGHT_CMD_SCALE=1.000 \
LEFT_M_PER_TICK=0.000051019 \
RIGHT_M_PER_TICK=0.000055084 \
TRACK_WIDTH_EFF_M=0.186605297 \
make pi-bringup
```

Merk:

1. Dette krever `ros-jazzy-robot-localization` i Docker-imaget, så første gang etter denne endringen må dere kjøre `make build`.
2. EKF-konfigen ligger i [ekf.yaml](/home/emiliam/Mekatronikk-4-MEPA2002/config/ekf.yaml) og kan overstyres med `EKF_PARAMS_FILE=/ws/config/ekf.yaml`.
3. Nav2 kan fortsette å bruke `/odom`; når EKF er på, er det den filtrerte odometrien.


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
| `cd ~/Mekatronikk-4-MEPA2002` | Gå til repoet før ryddekommandoene under. |
| `docker compose down --remove-orphans` | Første anbefalte steg før ny `make build`: stopper prosjektcontainere og rydder orphan-containere. |
| `docker container prune -f` | Neste anbefalte steg: fjerner stoppede containere. |
| `docker image rm mekk4/ros2-jazzy-dev:local \|\| true` | Neste anbefalte steg: fjerner det lokale ROS-imaget hvis det finnes. |
| `docker system prune -af` | Fjerner ubrukte containere/nettverk/images. |
| `docker builder prune -af` | Fjerner docker build-cache. |
| `sudo apt clean` | Fjerner apt-pakke-cache. |
| `sudo rm -rf /var/lib/apt/lists/*` | Fjerner lokale apt-indekser. |
| `rm -rf ~/Mekatronikk-4-MEPA2002/build ~/Mekatronikk-4-MEPA2002/log` | Fjerner lokale build/log-mapper. |
| `rm -rf ~/Mekatronikk-4-MEPA2002/install` | Neste anbefalte steg hvis dere trenger mer plass: frigjør mer, men krever ny `make ws`. |
| `docker system df` | Kjør dette etter rydde-sekvensen for å se om dere har nok plass før `make build`. |
| `docker builder prune -af` | Neste steg hvis det fortsatt er for lite plass etter sekvensen over; sletter build-cache. |
| `docker system prune -af` | Siste utvei hvis dere bare må få bygget og er ok med å miste ubrukte images og cache. |
