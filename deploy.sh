#!/bin/bash

set -ex

CONTAINER_NAME=signalmsgforwarder

docker stop "$CONTAINER_NAME"
docker rm -f "$CONTAINER_NAME"
docker build -t signal-msg-forwarder .

docker run --add-host host.docker.internal:host-gateway \
           -v ${PWD}/data:/usr/data \
           --env-file=.env \
           --detach \
           --restart=unless-stopped \
           --name "$CONTAINER_NAME" \
           signal-msg-forwarder
