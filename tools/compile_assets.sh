#!/bin/bash

# This script is intended to be run using Docker.
# From the root of the project, run the following command to compile the assets:
#
#   docker run -v $(pwd):/code node:10-buster /code/tools/compile_assets.sh
#
# See also INSTALL.md.

set -e

cd /code/tools/gulp
npm install
./node_modules/.bin/gulp
