#!/usr/bin/env bash
set -euo pipefail

CONTAINER=osmpoicms
IMAGE=osmpoicms
PORT=8000

docker stop $CONTAINER 2>/dev/null || true
docker rm $CONTAINER 2>/dev/null || true

docker build -t $IMAGE .

docker run -d \
  --name $CONTAINER \
  --restart unless-stopped \
  --env-file .env \
  -p 127.0.0.1:$PORT:8000 \
  $IMAGE
