# Nav2 og EKF

## Bunnlinje

Nav2-oppsettet bruker `odom` som global frame og `/lidar` som obstacle source.
EKF-oppsettet fuser hjulodometri som forward velocity og BNO085 som yaw
orientation.

## Nav2 Launch

Nav2 startes fra
[`nav2_stack.launch.py`](../../src/robot_bringup/launch/nav2_stack.launch.py).

Start i fysisk bringup:

```bash
WITH_NAV2=1 make pi-bringup
```

Start i normal sim:

```bash
make sim
```

`make sim` starter Nav2 allerede, fordi
[`minimal_all.launch.py`](../../src/robot_bringup/launch/minimal_all.launch.py)
har `use_nav2:=true` som default.

Start bare Nav2 mot en sim som allerede kjører uten Nav2:

```bash
make sim-nav2
```

## Nav2 Noder

| Node | Rolle |
|---|---|
| `controller_server` | Følger path og lager cmd_vel |
| `planner_server` | Planlegger path |
| `behavior_server` | Backup/spin/wait/drive-on-heading |
| `bt_navigator` | NavigateToPose / NavigateThroughPoses |
| `cmd_vel_mux` | Manual override over Nav2 |
| `velocity_smoother` | Accel/decel limiting |
| `nav_cmd_vel_flip` | Valgfri angular flip |
| `collision_monitor` | Stop/slowdown fra LiDAR |
| `lifecycle_manager_navigation` | Lifecycle bringup |

## Nav2 Parametre

Kilde: [`config/nav2_params.yaml`](../../config/nav2_params.yaml)

Viktige valg:

| Felt | Verdi |
|---|---|
| `global_frame` | `odom` |
| `robot_base_frame` | `base_link` |
| `odom_topic` | `/odom` |
| LaserScan topic | `/lidar` |
| Controller | `nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController` |
| Planner | `nav2_smac_planner::SmacPlannerLattice` |
| Local costmap | rolling, `5 x 5 m`, `0.05 m` resolution |
| Global costmap | rolling, `8 x 8 m`, `0.05 m` resolution |
| Footprint | `[[0.180, 0.106], [0.180, -0.106], [-0.209, -0.106], [-0.209, 0.106]]` |

## Collision Monitor

Input:

```text
cmd_vel_nav_flipped
```

Output:

```text
cmd_vel
```

LiDAR source:

```text
/lidar
```

`FrontSlow` er aktivert. `FrontStop` og `FootprintApproach` er definert, men
deaktivert i nåværende config.

## EKF

Kilde: [`config/ekf.yaml`](../../config/ekf.yaml)

Når `WITH_EKF=1`:

```text
/wheel/odom + /imu/data
    -> ekf_filter_node
    -> /odom
```

Konfig:

| Felt | Verdi |
|---|---|
| `frequency` | `50.0` |
| `two_d_mode` | `true` |
| `map_frame` | `map` |
| `odom_frame` | `odom` |
| `base_link_frame` | `base_link` |
| `world_frame` | `odom` |
| `odom0` | `/wheel/odom` |
| `imu0` | `/imu/data` |

Fusjon:

- Wheel odom: forward velocity.
- IMU: yaw orientation.
- Ikke full wheel pose.
- Ikke gyro z, før stabilitet er verifisert.

## Bringup Eksempler

```bash
# Full standard
WITH_IMU=1 WITH_MEGA_DRIVER=1 WITH_EKF=1 WITH_NAV2=1 make pi-bringup

# Uten EKF
WITH_EKF=0 make pi-bringup

# Uten Nav2
WITH_NAV2=0 make pi-bringup
```

## Verifikasjon

```bash
ros2 topic hz /wheel/odom
ros2 topic hz /imu/data
ros2 topic echo --once /odom
ros2 run tf2_ros tf2_echo odom base_link
ros2 lifecycle nodes
ros2 topic echo --once /cmd_vel_mux_active
```

## Viktig Risiko

Frame-bruken må verifiseres før hard Nav2 på fysisk robot. Nåværende kode setter
`BASE_FRAME=base_link` i [`scripts/pi_bringup.sh`](../../scripts/pi_bringup.sh),
og Nav2/EKF forventer også `base_link`.
