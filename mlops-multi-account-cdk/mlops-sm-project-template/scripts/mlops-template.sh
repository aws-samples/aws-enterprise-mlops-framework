#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository
set -e

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")
source "$SCRIPT_PATH/project-setup.sh"
source "$MLOPS_COMMONS_SCRIPTS_PATH/mlops_commons/scripts/cdk-project-cli.sh"

cdk_project_name="mlops-sm-project-template"

# run project for cli command like , setup, synth, deploy, destroy
run_project_cli "$cdk_project_name" "$@"
