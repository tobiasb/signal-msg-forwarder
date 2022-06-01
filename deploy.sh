#!/bin/bash

CONTAINER_NAME=signalmsgforwarder
git pull
docker rm -f "$CONTAINER_NAME"
docker build -t signal-msg-forwarder . && docker run --add-host host.docker.internal:host-gateway --env-file=.env -d --restart=unless-stopped --name "$CONTAINER_NAME" signal-msg-forwarder
