#! /usr/bin/env bash

container_id=$(./start_docker_container.sh)
docker logs -f "${container_id}" > container.log 2>&1 &
./start_web_app.sh > web_app.log 2>&1 &

