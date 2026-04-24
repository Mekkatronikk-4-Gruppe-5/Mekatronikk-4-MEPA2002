# Systemoversikt

## Bunnlinje

Repoet inneholder både fysisk robot-runtime og simulering. Fysisk robot kjører
ROS 2 Jazzy i Docker på Pi. PC-en brukes hovedsakelig til RViz, kamera-visning,
ROS teleop og debugging.

## Pakker

| Pakke | Rolle | Viktige filer |
|---|---|---|
| `robot_bringup` | Launch, RViz og felles bringup | [`launch`](../../src/robot_bringup/launch), [`rviz`](../../src/robot_bringup/rviz) |
| `mekk4_bringup` | Hardware-nære ROS-noder | [`mega_driver_node.py`](../../src/mekk4_bringup/mekk4_bringup/mega_driver_node.py), [`bno085_node.py`](../../src/mekk4_bringup/mekk4_bringup/bno085_node.py) |
| `mekk4_perception` | Kamera bridge og teddy-detektor | [`udp_camera_bridge.py`](../../src/mekk4_perception/mekk4_perception/udp_camera_bridge.py), [`teddy_detector.py`](../../src/mekk4_perception/mekk4_perception/teddy_detector.py) |
| `robot_description` | URDF og meshes | [`tracked_robot.urdf`](../../src/robot_description/urdf/tracked_robot.urdf) |
| `robot_gz` | Gazebo world og SDF-modell | [`model.sdf`](../../src/robot_gz/models/tracked_robot/model.sdf), [`tracked_robot_world.sdf`](../../src/robot_gz/worlds/tracked_robot_world.sdf) |
| `robot_sim_control` | Sim-only tracked-drive adapter | [`tracked_cmd_vel_adapter.py`](../../src/robot_sim_control/robot_sim_control/tracked_cmd_vel_adapter.py) |

## Implementert Nå

- Docker Compose-runtime for Pi i [`compose.yml`](../../compose.yml).
- ROS workspace build i container via [`scripts/ws_build.sh`](../../scripts/ws_build.sh).
- Fysisk bringup via [`scripts/pi_bringup.sh`](../../scripts/pi_bringup.sh).
- LiDAR launch for LDLiDAR LD06 via [`lidar_nav2_compat.launch.py`](../../src/robot_bringup/launch/lidar_nav2_compat.launch.py).
- BNO085 IMU node.
- Arduino Mega serial-driver.
- Kamera H264/UDP pipeline.
- YOLO/NCNN teddy-detektor.
- Nav2 stack.
- EKF med `robot_localization`.
- Gazebo Sim med camera, IMU, LiDAR og tracked-drive plugin.

## Fysisk Dataflyt

```text
PC/RViz/teleop
    -> ROS discovery mot Pi
    -> /cmd_vel_manual
    -> cmd_vel_mux
    -> velocity_smoother
    -> collision_monitor
    -> /cmd_vel
    -> mega_driver_node
    -> Arduino Mega
    -> motor driver

Arduino Mega encodere
    -> mega_driver_node
    -> /wheel/odom når EKF er på
    -> EKF
    -> /odom

BNO085
    -> /imu/data
    -> EKF

LDLiDAR LD06
    -> /lidar
    -> Nav2 costmaps
    -> RViz

Pi camera
    -> rpicam-vid
    -> H264/RTP UDP
    -> teddy_detector
    -> /teddy_detector/status
    -> annotert debugvideo til PC
    -> udp_camera_bridge
    -> /camera
```

## Sim Dataflyt

```text
Gazebo Sim
    -> ros_gz_bridge
    -> /clock, /lidar, /imu/data, /camera, /joint_states

/cmd_vel
    -> tracked_cmd_vel_adapter
    -> /model/tracked_robot/cmd_vel
    -> Gazebo TrackedVehicle plugin
    -> /wheel/odom
    -> EKF
    -> /odom
```

## Ikke Implementert Som Standard

- Full SLAM workflow. [`config/slam_params.yaml`](../../config/slam_params.yaml) finnes, men launches ikke i standard `make pi-bringup`.
- Full `map -> odom -> base_link` lokaliseringskjede. Nav2-parametrene bruker `odom` som global frame.
- Full hardware-BOM for kamera, motorer og belter.
