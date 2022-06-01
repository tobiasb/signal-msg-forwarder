# Signal Message Forwarder

## Run locally

```bash
docker build -t signal-msg-forwarder . && docker run --env-file=.env --restart=unless-stopped signal-msg-forwarder
```