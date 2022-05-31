#!/bin/bash

git pull
docker rm -f signalmsgforwarder
docker build -t signal-msg-forwarder . && docker run --env-file=.env -d --restart=unless-stopped --name signalmsgforwarder signal-msg-forwarder
