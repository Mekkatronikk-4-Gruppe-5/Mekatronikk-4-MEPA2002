# LiDAR + RViz (Pi + PC)

Kort oppskrift for å se LiDAR live i RViz.

## 1) Start LiDAR på Pi

```bash
cd ~/Mekatronikk-4-MEPA2002
make up
make shell
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
ros2 launch robot_bringup lidar_nav2_compat.launch.py \
  port_name:=/dev/ttyAMA0 \
  topic_name:=/lidar \
  frame_id:=base_laser \
  base_frame:=chassis
```

## 2) Sett ROS discovery mellom Pi og PC

Finn IP:

```bash
# på Pi
hostname -I

# på PC
hostname -I
```

Sett miljøvariabler:

```bash
# på Pi (bytt ut <PC_IP>)
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_STATIC_PEERS=<PC_IP>

# på PC (bytt ut <PI_IP>)
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_STATIC_PEERS=<PI_IP>
source /opt/ros/jazzy/setup.bash
```

## 3) Verifiser fra PC

```bash
ros2 topic list | grep lidar
ros2 topic hz /lidar
```

## 4) Start RViz på PC

```bash
rviz2
```

I RViz:

1. `Global Options -> Fixed Frame = base_laser`
2. `Add -> LaserScan`
3. `Topic = /lidar`
4. Under `Topic` (utvid feltet):  
   `Reliability Policy = Best Effort`  
   `Durability Policy = Volatile`

## Feilsøking (kort)

- `empty topicname`: `LaserScan`-display har tom `Topic`. Sett `/lidar`.
- Ingen topic på PC: sjekk `ROS_DOMAIN_ID`, `ROS_STATIC_PEERS` og at LiDAR-launch fortsatt kjører på Pi.
- Hvis `/dev/ttyAMA0` ikke virker: test `port_name:=/dev/serial0`.
