# ROS Interfaces

## Bunnlinje

Før du endrer launch, Nav2, EKF eller hardware-noder: sjekk topics og frames her.
Dette er kontraktene resten av systemet forventer.

## Frames

| Frame | Rolle | Kilde |
|---|---|---|
| `odom` | Lokal odometriframe | Mega-driver eller EKF |
| `base_link` | Nav2 robotbase | URDF og Nav2 config |
| `chassis` | Fysisk chassislink | URDF |
| `lidar_link` | LiDAR mount | URDF |
| `base_laser` | LaserScan frame | LiDAR launch og Gazebo |
| `imu_link` | IMU frame | URDF og BNO085 node |
| `camera_link` | Kamera frame | URDF og camera bridge |
| `map` | Kartframe | SLAM/EKF config, ikke hovedframe i Nav2 default |

Viktig mismatch å være klar over:

- [`config/nav2_params.yaml`](../../config/nav2_params.yaml) bruker `robot_base_frame: base_link`.
- [`scripts/pi_bringup.sh`](../../scripts/pi_bringup.sh) setter `BASE_FRAME=chassis` som default til Mega-driver.
- [`config/ekf.yaml`](../../config/ekf.yaml) bruker `base_link_frame: base_link`.

Verifiser TF før fysisk Nav2-kjøring:

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo odom chassis
ros2 run tf2_ros tf2_echo chassis base_laser
```

## Topics

| Topic | Type | Produsent | Bruk |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Collision monitor eller manuell test | Sluttkommando til Mega/sim |
| `/cmd_vel_manual` | `geometry_msgs/msg/Twist` | `ros_keyboard_teleop` | Manuell override |
| `/cmd_vel_nav_auto` | `geometry_msgs/msg/Twist` | Nav2 controller/behavior | Rå Nav2 output |
| `/cmd_vel_nav` | `geometry_msgs/msg/Twist` | `cmd_vel_mux_node` | Valgt nav/manual input til smoother |
| `/cmd_vel_smoothed` | `geometry_msgs/msg/Twist` | `velocity_smoother` | Smoothed cmd_vel |
| `/cmd_vel_nav_flipped` | `geometry_msgs/msg/Twist` | `nav_cmd_vel_flip_node` | Input til collision monitor |
| `/cmd_vel_mux_active` | `std_msgs/msg/String` | `cmd_vel_mux_node` | `manual`, `nav` eller `idle` |
| `/odom` | `nav_msgs/msg/Odometry` | Mega-driver eller EKF | Nav2 og RViz |
| `/wheel/odom` | `nav_msgs/msg/Odometry` | Mega-driver når EKF er på | EKF input |
| `/imu/data` | `sensor_msgs/msg/Imu` | BNO085 eller Gazebo bridge | EKF input |
| `/lidar` | `sensor_msgs/msg/LaserScan` | LDLiDAR eller Gazebo bridge | Nav2 costmaps og RViz |
| `/lidar/points` | `sensor_msgs/msg/PointCloud2` | Gazebo bridge | Sim debug |
| `/camera` | `sensor_msgs/msg/Image` | UDP camera bridge eller Gazebo bridge | RViz image |
| `/teddy_detector/status` | `std_msgs/msg/String` | `teddy_detector` | Teddy count/offset/FPS |

## Nodes

| Node | Pakke | Rolle |
|---|---|---|
| `robot_state_publisher` | `robot_state_publisher` | Publiserer URDF TF |
| `zero_joint_state_publisher` | `mekk4_bringup` | Publiserer null joint states |
| `ldlidar` | `ldlidar_stl_ros2` | LiDAR driver |
| `bno085` | `mekk4_bringup` | IMU driver |
| `mega_driver` | `mekk4_bringup` | Serial motor/odom driver |
| `ekf_filter_node` | `robot_localization` | EKF |
| `teddy_detector` | `mekk4_perception` | YOLO teddy detector |
| `udp_camera_bridge` | `mekk4_perception` | UDP H264 til ROS image |
| `cmd_vel_mux` | `mekk4_bringup` | Manual override over Nav2 |
| `nav_cmd_vel_flip` | `mekk4_bringup` | Valgfri angular flip |
| `tracked_cmd_vel_adapter` | `robot_sim_control` | Sim cmd_vel til tracked plugin |

## Nav2 Command Chain

Definert i [`nav2_stack.launch.py`](../../src/robot_bringup/launch/nav2_stack.launch.py):

```text
controller_server / behavior_server
  -> cmd_vel_nav_auto
  -> cmd_vel_mux_node
  -> cmd_vel_nav
  -> velocity_smoother
  -> cmd_vel_smoothed
  -> nav_cmd_vel_flip_node
  -> cmd_vel_nav_flipped
  -> collision_monitor
  -> cmd_vel
```

Manual override:

```text
ros_keyboard_teleop
  -> /cmd_vel_manual
  -> cmd_vel_mux_node
  -> cmd_vel_nav
```

`cmd_vel_mux_node` prioriterer manual input i `0.25 s`. Når manuell input stopper,
går den tilbake til Nav2 hvis Nav2-input fortsatt er fersk.

## Verifikasjonskommandoer

```bash
ros2 node list
ros2 topic list
ros2 topic hz /lidar
ros2 topic hz /odom
ros2 topic hz /imu/data
ros2 topic echo --once /cmd_vel_mux_active
ros2 topic echo --once /teddy_detector/status
```
