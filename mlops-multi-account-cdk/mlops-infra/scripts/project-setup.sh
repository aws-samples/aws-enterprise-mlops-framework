#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")
MLOPS_COMMONS_SCRIPTS_PATH="$SCRIPT_PATH"/../../mlops-commons
if [[ ! -d "$MLOPS_COMMONS_SCRIPTS_PATH" ]]; then
  MLOPS_COMMONS_SCRIPTS_PATH="$SCRIPT_PATH"/..
fi

# preparing account for cdk application
"$MLOPS_COMMONS_SCRIPTS_PATH"/mlops_commons/scripts/setup.sh "$SCRIPT_PATH/../"