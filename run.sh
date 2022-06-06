#!/bin/bash

set -ex

docker build -t signal-msg-forwarder .

docker run -v ${PWD}/data:/usr/data \
           --env-file=.env \
           --restart=unless-stopped \
           signal-msg-forwarder