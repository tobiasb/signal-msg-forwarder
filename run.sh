#!/bin/bash

git pull
docker build -t signal-msg-forwarder . && docker run --env-file=.env -d --restart=unless-stopped signal-msg-forwarder
