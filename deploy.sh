#!/bin/bash

REPO_URL="https://github.com/YOUR_USERNAME/bullspread.git"
PROJECT_NAME="bullspread"
IMAGE_NAME="spreadscanner"
CONTAINER_NAME="spreadbot"

export POLYGON_API_KEY="${POLYGON_API_KEY}"
export DISCORD_WEBHOOK="${DISCORD_WEBHOOK}"

apt update && apt install -y python3 python3-pip git docker.io
systemctl enable docker
usermod -aG docker $USER

git clone $REPO_URL $PROJECT_NAME || exit 1
cd $PROJECT_NAME

docker build -t $IMAGE_NAME .
docker run -d --name $CONTAINER_NAME \
  -e POLYGON_API_KEY=$POLYGON_API_KEY \
  -e DISCORD_WEBHOOK=$DISCORD_WEBHOOK \
  --restart=always $IMAGE_NAME

docker logs -f $CONTAINER_NAME