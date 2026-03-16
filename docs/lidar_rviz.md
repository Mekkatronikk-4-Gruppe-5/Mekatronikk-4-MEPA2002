# LiDAR + RViz (Pi + PC)

Kort oppskrift for å se LiDAR live i RViz.

## 1) Start robotstack på Pi

```bash
cd ~/Mekatronikk-4-MEPA2002
make pi-bringup
```

Dette scriptet:

1. finner PC-IP fra SSH-sesjonen
2. setter `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE` og `ROS_STATIC_PEERS`
3. starter `robot_state_publisher`, LiDAR og Nav2 i samme Docker-kjoering

Hvis du bare vil se LiDAR + TF og ikke starte Nav2:

```bash
WITH_NAV2=0 make pi-bringup
```

## 2) Sett ROS discovery på PC

Fra PC-en:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Mekatronikk-4-MEPA2002
eval "$(bash scripts/ros_discovery_env.sh pc gruppe5pi5)"
```

Hvis hostnavnet ikke virker, bruk IP direkte:

```bash
eval "$(bash scripts/ros_discovery_env.sh pc 192.168.10.55)"
```

## 3) Verifiser fra PC

```bash
ros2 topic list | grep lidar
ros2 topic hz /lidar
ros2 topic echo --once /tf_static
```

## 4) Start RViz på PC

```bash
rviz2
```

I RViz:

1. `Global Options -> Fixed Frame = odom` eller `map`
2. `Add -> LaserScan`
3. `Topic = /lidar`
4. Under `Topic` (utvid feltet):  
   `Reliability Policy = Best Effort`  
   `Durability Policy = Volatile`
5. Valgfritt: `Add -> RobotModel` og bruk `/robot_description`

## Feilsøking (kort)

- `empty topicname`: `LaserScan`-display har tom `Topic`. Sett `/lidar`.
- Ingen topic på PC: kjør `eval "$(bash scripts/ros_discovery_env.sh pc <pi-host-eller-ip>)"` på nytt og sjekk at `make pi-bringup` fortsatt kjører på Pi.
- Hvis `/dev/ttyAMA0` ikke virker: test `port_name:=/dev/serial0`.
- Hvis auto-detection på Pi bommer: bruk `PC_HOST=<pc-ip> make pi-bringup`.
