SHELL := /bin/bash

.PHONY: build shell up down ws vision lidar-setup lidar-test

build:
	docker compose build

shell:
	docker compose run --rm ros

up:
	docker compose up -d

down:
	docker compose down
# Build ROS workspace + fix console_script shebang to venv python (PEP668-safe)
ws:
	docker compose run --rm ros bash -lc '/ws/scripts/ws_build.sh'

vision:
	./scripts/vision_stream.sh

lidar-setup:
	docker compose run --rm ros bash -lc '/ws/scripts/setup_ldlidar_driver.sh'

lidar-test:
	docker compose run --rm ros bash -lc '/ws/scripts/lidar_smoketest.sh'

