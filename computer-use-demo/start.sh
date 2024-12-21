#! /usr/bin/env bash

./start_docker_container.sh &
./start_web_app.sh > web_app.log 2>&1 &

