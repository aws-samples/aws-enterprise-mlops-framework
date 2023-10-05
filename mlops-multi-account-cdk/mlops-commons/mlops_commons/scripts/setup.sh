#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

# setting these environment variables to empty so that config don't complain, these are required for cdk context which will be populated by cdk from given aws profile, in current context of shell script execution, these are not required any default value, so just setting it to empty
export CDK_DEFAULT_ACCOUNT=""
export CDK_DEFAULT_REGION=""

# installing pre requisites
"$SCRIPT_PATH"/install-prerequisites-brew.sh "$@"

# preparing account for cdk application
"$SCRIPT_PATH"/cdk-account-setup.sh