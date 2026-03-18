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
| `make build` | Bygger Docker-image (kun ved første gang eller etter Docker-endringer). |
| `make ws` | Bygger ROS-workspace i container. Kjør igjen hvis ROS-kode er endret. |

PC:

| Kommando | Hva den gjør |
|---|---|
| `source /opt/ros/jazzy/setup.bash` | Laster ROS 2 Jazzy-miljø. |
| `cd ~/Mekatronikk-4-MEPA2002` | Går til repoet på PC. |
| `colcon build --symlink-install` | Bygger PC-workspace. Kjør igjen hvis lokal ROS-kode er endret. |
| `source install/setup.bash` | Laster de bygde pakkene i shellen. |

### Standard workflow nå

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

### ROS discovery og IP

I normal bruk trenger du ikke å kjøre `scripts/ros_discovery_env.sh` manuelt.

Det er bare nyttig hvis du vil feilsøke:

```bash
bash scripts/ros_discovery_env.sh pi
bash scripts/ros_discovery_env.sh pc gruppe5pi5
```

Automatikken fungerer best når:

1. du SSH-er inn på Pi fra samme PC som skal bruke RViz
2. Pi og PC faktisk når hverandre på samme nett
3. PC kan løse `gruppe5pi5`, eller du overstyrer med IP

### Fast SSH-navn for hele gruppa

Repoet setter ikke opp SSH-navnet selv. Alle scripts antar bare at Pi allerede kan naaes som `gruppe5pi5`.

Det er to ulike ting som skjer:

1. `ssh gruppe5@gruppe5pi5` krever at PC-en kan resolve `gruppe5pi5` til riktig adresse.
2. `make pi-bringup` bruker den aktive SSH-sesjonen til aa lese klient-IP fra `SSH_CONNECTION` eller `SSH_CLIENT`, slik at ROS discovery og UDP-streamen peker tilbake til riktig PC.

Hvis samme kommando bare virker paa noen maskiner, er det normalt et navneoppslag-problem, ikke et ROS-problem.

Anbefalt permanent oppsett:

1. installer Tailscale paa Pi og alle PC-er
2. gi Pi et stabilt navn, for eksempel `gruppe5pi5`
3. bruk MagicDNS eller Tailscale sitt fulle vertsnavn som faktisk resolver i tailnettet
4. legg samme alias i `~/.ssh/config` paa alle klient-PC-er

Eksempel paa klient-PC:

```sshconfig
Host gruppe5pi5
  HostName gruppe5pi5.<tailnet-navn>.ts.net
  User gruppe5
```

Da kan alle bruke samme kommando:

```bash
ssh gruppe5@gruppe5pi5
```

Alternativer:

1. `gruppe5pi5.local` via mDNS/Avahi kan fungere paa et vanlig lokalt nett, men er ofte upaalitelig paa Eduroam fordi multicast og klient-til-klient-trafikk kan vaere begrenset.
2. `/etc/hosts` paa hver PC fungerer, men maa oppdateres manuelt hvis adressen endrer seg.

Kort sagt: hvis dere vil slippe aa finne IP hver gang og vaere uavhengige av hvordan Eduroam oppfoerer seg, er Tailscale + felles `~/.ssh/config` den mest robuste loesningen.

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

Arduino-sketchene i repoet kan lastes opp direkte fra Pi-host. Dette bør kjøre paa hosten, ikke i Docker, siden dagens container bare mapper inn LiDAR-porten og ikke Mega over USB.

Første gang paa Pi-host:

```bash
sudo apt update
sudo apt install curl
mkdir -p ~/bin
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=~/bin sh
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
arduino-cli version
arduino-cli core update-index
arduino-cli core install arduino:avr
```

Hvis USB-porten senere gir `Permission denied`, legg brukeren i `dialout`:

```bash
sudo usermod -aG dialout $USER
newgrp dialout
```

Vanlig upload:

```bash
make mega-upload
MEGA_SKETCH=mega_keyboard_drive make mega-upload
MEGA_SKETCH=mega_dfr0601_test make mega-upload
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

### Arduino Mega smoke test

Hvis du vil verifisere at Pi-en faktisk kan snakke med en Arduino Mega over USB, finnes det nå en enkel smoke test.

1. Last opp [mega_smoketest.ino](/home/emiliam/Mekatronikk-4-MEPA2002/arduino/mega_smoketest/mega_smoketest.ino) til Mega, for eksempel med `make mega-upload`.
2. Sørg for at Pi-host har `python3-serial` tilgjengelig.
3. Kjør testen på Pi:

```bash
make mega-test
```

Dette gjør:

1. finner `Mega`-porten automatisk (`/dev/serial/by-id`, `/dev/ttyACM*` eller `/dev/ttyUSB*`)
2. åpner USB-serial direkte på Pi-host
3. sender `ID`, `PING`, `LED ON`, `LED OFF`
4. forventer svar tilbake fra Mega og bekrefter at link fungerer

Hvis `python3-serial` mangler på Pi-host:

```bash
sudo apt install python3-serial
```

Hvis auto-detection bommer:

```bash
MEGA_PORT=/dev/ttyACM0 make mega-test
```

### Arduino Mega keyboard drive

Hvis du vil kjøre roboten manuelt med tastatur, bruk keyboard-firmwaren på Mega og start teleop fra Ubuntu-maskinen din, ikke fra SSH-terminalen på Pi.

1. Last opp [mega_keyboard_drive.ino](/home/emiliam/Mekatronikk-4-MEPA2002/arduino/mega_keyboard_drive/mega_keyboard_drive.ino) til Mega, for eksempel med `MEGA_SKETCH=mega_keyboard_drive make mega-upload`.
2. Sørg for at Pi-host har `python3-serial`.
3. Sørg for at Ubuntu-PC-en har `python3-tk` og `sshpass`.
4. Start kjøring fra Ubuntu-PC:

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

Hvis du trenger å overstyre SSH-host eller Mega-port:

```bash
PI_HOST=gruppe5@gruppe5pi5 MEGA_PORT=/dev/ttyACM0 make pc-mega-keyboard
```

Hvis repoet ligger et annet sted på Pi:

```bash
REMOTE_REPO=~/Mekatronikk-4-MEPA2002 make pc-mega-keyboard
```

Merk:

1. `make mega-keyboard` finnes fortsatt som terminal-variant, men anbefales ikke over SSH siden vanlige terminaler ikke håndterer samtidige hold av flere taster like robust som GUI-varianten.
2. Hvis GUI-broen faller ut, prøver den å koble opp SSH på nytt automatisk.

### Arduino Mega + DFR0601 motor test

Det finnes også en enkel motor-test for en Arduino Mega koblet til DFR0601 med denne pin-mappingen:

1. `INA1 = 22`
2. `INB1 = 23`
3. `INA2 = 24`
4. `INB2 = 25`
5. `PWM1 = 5`
6. `PWM2 = 4`
7. `Encoder 1 A = 3`
8. `Encoder 1 B = 2`
9. `Encoder 2 A = 18`
10. `Encoder 2 B = 19`

Test-firmwaren støtter begge encoderne, men [mega_motor_test.py](/home/emiliam/Mekatronikk-4-MEPA2002/scripts/mega_motor_test.py) validerer foreløpig `ENC1` eksplisitt i den automatiske sekvensen.

Last opp [mega_dfr0601_test.ino](/home/emiliam/Mekatronikk-4-MEPA2002/arduino/mega_dfr0601_test/mega_dfr0601_test.ino) til Mega, for eksempel med `MEGA_SKETCH=mega_dfr0601_test make mega-upload`, løft roboten opp fra gulvet, og kjør:

```bash
make mega-motor-test
```

Dette gjør en kort sekvens:

1. `M1` fremover
2. `M1` bakover
3. `M2` fremover
4. `M2` bakover
5. begge fremover
6. begge bakover
7. `STOP` mellom hvert steg
8. leser `ENC1` før og etter `M1`-steppene for å verifisere at hall-sensoren teller

Standardverdier:

1. `PWM_VALUE=80`
2. `STEP_DURATION=0.8`

Du kan overstyre dem:

```bash
PWM_VALUE=60 STEP_DURATION=0.5 make mega-motor-test
```

Hvis auto-detection bommer:

```bash
MEGA_PORT=/dev/ttyACM0 make mega-motor-test
```

Praktisk:

1. Etter endring av farger, eksponering, bitrate, intra eller denoise i `camera_stream.*`, prøv `make camera-reload` på Pi.
2. Hvis du endrer `camera_stream.width/height`, porter eller `teddy_detector.*`, gjør full restart av `make pi-bringup`.
3. `make camera-stop` er bare en recovery-knapp hvis gamle kameraprosesser henger igjen.
4. Du kan fortsatt overstyre midlertidig med env vars, for eksempel `WIDTH=640 FPS=10 SATURATION=1.2 make pi-bringup`.

## Pi ytelse (host, ikke Docker)

| Kommando | Hva den gjør |
|---|---|
| `cpupower frequency-info` | Viser tilgjengelige governors og aktiv policy. |
| `sudo cpupower frequency-set -g performance` | Setter CPU i maks ytelse-modus. |
| `sudo cpupower frequency-set -g ondemand` | Setter CPU tilbake til dynamisk modus. |
| `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | Verifiserer aktiv governor. |
| `watch -n1 'vcgencmd measure_temp; vcgencmd measure_clock arm; vcgencmd get_throttled'` | Overvåker temperatur, klokke og throttling live. |

Gjør `performance` permanent etter reboot:

| Kommando | Hva den gjør |
|---|---|
| `sudo nano /etc/systemd/system/cpu-governor-performance.service` | Oppretter systemd-service for governor ved boot. |
| `sudo systemctl daemon-reload` | Leser inn ny servicefil. |
| `sudo systemctl enable --now cpu-governor-performance.service` | Aktiverer service nå og ved neste reboot. |
| `sudo systemctl status cpu-governor-performance.service --no-pager` | Sjekker at service kjører uten feil. |
| `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | Verifiserer at governor fortsatt er `performance`. |

Service-innhold:

```ini
[Unit]
Description=Set CPU governor to performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/cpupower frequency-set -g performance
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Tilbake til `ondemand` permanent:

| Kommando | Hva den gjør |
|---|---|
| `sudo systemctl disable --now cpu-governor-performance.service` | Skrur av permanent `performance`-service. |
| `sudo cpupower frequency-set -g ondemand` | Setter governor tilbake med en gang. |

Valgfritt (mer aktiv viftekurve):

| Kommando | Hva den gjør |
|---|---|
| `sudo nano /boot/firmware/config.txt` | Åpner Pi-bootconfig for vifteparametre. |
| `sudo reboot` | Rebooter Pi etter endringer i `config.txt`. |

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
