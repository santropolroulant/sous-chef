#!/bin/bash
PROJECT_ROOT_DIR="$(dirname $0)/.."
pushd $PROJECT_ROOT_DIR > /dev/null
docker run -v $(pwd):/code node:10-buster /code/tools/compile_assets_docker.sh
