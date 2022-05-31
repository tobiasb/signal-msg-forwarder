#!/bin/bash

git pull
docker build -t signal-msg-forwarder . && docker run --env-file=.env -d signal-msg-forwarder
