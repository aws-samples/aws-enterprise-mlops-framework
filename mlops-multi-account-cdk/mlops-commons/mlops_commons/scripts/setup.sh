#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

# installing pre requisites
"$SCRIPT_PATH"/install-prerequisites-brew.sh "$@"

# preparing account for cdk application
"$SCRIPT_PATH"/cdk-account-setup.sh