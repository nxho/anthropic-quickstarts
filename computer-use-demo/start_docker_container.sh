#! /usr/bin/env bash

docker run \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ICLOUD_USER_EMAIL=$ICLOUD_USER_EMAIL \
  -e ICLOUD_APP_PASSWORD=$ICLOUD_APP_PASSWORD \
  -e EMAIL_ALIAS=$EMAIL_ALIAS \
  -v "$(pwd)/computer_use_demo:/home/computeruse/computer_use_demo/" \
  -v "$HOME/.anthropic:/home/computeruse/.anthropic" \
  -v "$(pwd)/public:/home/computeruse/public/" \
  -p 5900:5900 \
  -p 8501:8501 \
  -p 6080:6080 \
  -p 8080:8080 \
  -it --rm computer-use-demo:local
