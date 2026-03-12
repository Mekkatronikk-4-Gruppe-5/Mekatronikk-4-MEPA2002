# Mekatronikk-4-MEPA2002

## Komme i gang

### 1. Koble til Pi-en

```bash
ssh gruppe5@gruppe5pi5
passord: qwerty
cd ~/Mekatronikk-4-MEPA2002
```

### 2. Bygg Docker-imaget

Dette gjøres kun første gang, eller når `docker/Dockerfile` er endret.

```bash
docker compose build
```

### 3. Bygg ROS-workspace

Dette gjøres første gang og etter kodeendringer i `src/`.

```bash
docker compose run --rm ros bash -lc '/ws/scripts/ws_build.sh'
```

### 4. Start containeren

```bash
docker compose up -d
```

### 5. Åpne shell i containeren

```bash
docker compose run --rm ros
```

### 6. Stopp containeren

```bash
docker compose down
```

## Vision-stream

Startes fra host (krever `rpicam-apps` og `gstreamer1.0-tools` på Pi-en):

```bash
make vision
```

Dette starter kameraet og launcher `teddy_detector`-noden inni containeren.

## Når må jeg kjøre `docker compose build`?

| Endring | Hva du trenger |
|---|---|
| Kode i `src/` | Bare `ws_build.sh` |
| Ny ROS-pakke eller avhengighet i `package.xml` | Bare `ws_build.sh` |
| Endring i `docker/Dockerfile` | `docker compose build` |
| Ny `pip`/`apt`-avhengighet | `docker compose build` |

Koden mountes inn i containeren fra hosten, så endringer i `src/` krever aldri rebuild av Docker-imaget.

## YOLO-modell

Prosjektet bruker `yolo26n_ncnn_model` — nano-varianten, som er den minste og raskeste. For brukstilfellet (finne teddybjørn og beregne senter) er dette riktig valg på Pi.

Modellen legges i én av disse plasseringene (prioritert rekkefølge):

1. Satt via miljøvariabelen `MEKK4_NCNN_MODEL`
2. `/ws/models/yolo26n_ncnn_model`
3. `/ws/yolo26n_ncnn_model`

## Spare plass på Pi-en

Docker kan fort spise opp diskplass. Sjekk hva som brukes:

```bash
docker system df
```

**Fjern stoppede containere, ubrukte images og build-cache i én kommando:**
```bash
docker system prune
```

Legg til `-a` for å også fjerne images som ikke er i bruk (inkludert det dere har bygget):
```bash
docker system prune -a
```

**Fjern bare build-cache (vanligvis den største synderen):**
```bash
docker builder prune
```

**Fjern ROS build-output fra workspace:**
```bash
rm -rf build/ install/ log/
```
Disse regenereres av `ws_build.sh` og trenger ikke lagres.

**Sjekk hva som tar plass generelt:**
```bash
df -h          # diskbruk totalt
du -sh ~/*     # hva i hjemmemappa som er størst
```

> Kjør `docker compose down` før du sletter images, ellers er imaget i bruk.

## Feilsøking

**Docker-tjenesten kjører ikke:**
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

**Permission denied på Docker:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

## LIDAR inn i Nav2

Nav2- og SLAM-parametrene i dette repoet forventer LaserScan pa topic `/lidar`.

Start LIDAR-driveren med kompatibel topic/frame fra bringup-pakken:

```bash
ros2 launch robot_bringup lidar_nav2_compat.launch.py
```

Hvis du bruker en annen port eller modell, overstyr launch-argumentene:

```bash
ros2 launch robot_bringup lidar_nav2_compat.launch.py \
	product_name:=LDLiDAR_STL27L \
	port_name:=/dev/ttyUSB0 \
	port_baudrate:=230400 \
	topic_name:=/lidar \
	frame_id:=base_laser \
	base_frame:=chassis
```

Hvis Nav2 klager pa transform mellom base og laser, juster `tf_x/tf_y/tf_z/tf_roll/tf_pitch/tf_yaw` i samme launch-kommando.

## Testguide for LD06 pa Pi

Bruk denne guiden hvis du tror sensoren er LD06, men ikke husker riktig serial-enhet.

### 1) Oppdater kode pa Pi

```bash
cd ~/Mekatronikk-4-MEPA2002
git checkout main
git pull origin main
```

### 2) Start docker og bygg workspace

```bash
docker compose up -d
docker compose run --rm ros bash -lc '/ws/scripts/ws_build.sh'
```

### 3) Finn riktig /dev/tty

Koble fra og koble til LIDAR, og sjekk hva som dukker opp:

```bash
ls -l /dev/ttyAMA* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
ls -l /dev/serial/by-id 2>/dev/null
dmesg | tail -n 60
```

Vanlige kandidater er `/dev/ttyAMA0` (GPIO/UART) eller `/dev/ttyUSB0` (USB-serial).

### 4) Sjekk tilgang til serial-port

```bash
groups
```

Hvis `dialout` mangler:

```bash
sudo usermod -aG dialout $USER
newgrp dialout
```

### 5) Start LIDAR med LD06-profil

Test kandidat 1:

```bash
docker compose run --rm ros bash -lc "source /opt/ros/jazzy/setup.bash && source /ws/install/setup.bash && ros2 launch robot_bringup lidar_nav2_compat.launch.py product_name:=LDLiDAR_LD06 port_name:=/dev/ttyAMA0 port_baudrate:=230400"
```

Hvis ingen data, stopp og test kandidat 2:

```bash
docker compose run --rm ros bash -lc "source /opt/ros/jazzy/setup.bash && source /ws/install/setup.bash && ros2 launch robot_bringup lidar_nav2_compat.launch.py product_name:=LDLiDAR_LD06 port_name:=/dev/ttyUSB0 port_baudrate:=230400"
```

### 6) Verifiser at data kommer

I et nytt terminalvindu pa Pi:

```bash
docker compose run --rm ros bash -lc "source /opt/ros/jazzy/setup.bash && source /ws/install/setup.bash && ros2 topic hz /lidar"
docker compose run --rm ros bash -lc "source /opt/ros/jazzy/setup.bash && source /ws/install/setup.bash && ros2 topic echo /lidar --once"
```

Hvis dette virker, er port og modell riktig satt.

### 7) Verifiser TF mellom base og laser

```bash
docker compose run --rm ros bash -lc "source /opt/ros/jazzy/setup.bash && source /ws/install/setup.bash && ros2 run tf2_ros tf2_echo chassis base_laser"
```

Hvis TF ikke stemmer fysisk, juster launch-argumentene `tf_x`, `tf_y`, `tf_z`, `tf_roll`, `tf_pitch`, `tf_yaw`.

### 8) Koble mot Nav2/SLAM

Denne launchen publiserer pa `/lidar`, som matcher eksisterende `config/nav2_params.yaml` og `config/slam_params.yaml`.
Nar steg 6 fungerer, kan LIDAR brukes direkte av Nav2/SLAM.
