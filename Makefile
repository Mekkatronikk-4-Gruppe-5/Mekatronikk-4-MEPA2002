SHELL := /bin/bash

.PHONY: build shell up down

build:
	docker compose build

shell:
	docker compose run --rm ros

up:
	docker compose up -d

down:
	docker compose down
