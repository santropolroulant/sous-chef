#!/bin/bash

# This script is intended to be run via a Docker node image.
# Do not use this script directly; use `compile_assets.sh` instead, which will
# run the proper Docker image for these commands to complete successfully.
# See `INSTALL.md` for the complete instructions.

set -e

cd /code/tools/gulp
npm install
./node_modules/.bin/gulp
