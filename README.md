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

## Robot (Pi5 + Docker)

| Kommando | Hva den gjør |
|---|---|
| `ssh gruppe5@gruppe5pi5` | Logger inn på Pi. |
| `cd ~/Mekatronikk-4-MEPA2002` | Går til repoet på Pi. |
| `make build` | Bygger Docker-image (kun ved behov). |
| `make ws` | Bygger ROS-workspace i container. |
| `make up` | Starter ROS-container i bakgrunnen. |
| `make shell` | Åpner shell inne i containeren. |

Kjør Nav2 inne i container-shell:

| Kommando | Hva den gjør |
|---|---|
| `source /opt/ros/jazzy/setup.bash` | Laster ROS i container-shell. |
| `source /ws/install/setup.bash` | Laster workspace i container-shell. |
| `ros2 launch robot_bringup nav2_stack.launch.py use_sim_time:=false map:=/ws/maps/my_map.yaml params_file:=/ws/config/nav2_params.yaml` | Starter Nav2 på fysisk robotoppsett. |

`make down` stopper container.

## Vision og LiDAR

| Kommando | Hva den gjør |
|---|---|
| `make vision` | Starter vision-stream/oppsett. |
| `make lidar-setup` | Henter/bygger LiDAR-driver i workspace. |
| `make lidar-test` | Kjører enkel LiDAR-smoketest. |

Guide for LiDAR i RViz: [docs/lidar_rviz.md](/home/emiliam/Mekatronikk-4-MEPA2002/docs/lidar_rviz.md)

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
