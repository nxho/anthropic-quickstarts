#! /usr/bin/env bash

container_id=$(docker ps --filter "ancestor=computer-use-demo:local" --format "{{.ID}}")
docker kill "${container_id}"

web_app_pid=$(pgrep "npm run dev")
kill "${web_app_pid}"

