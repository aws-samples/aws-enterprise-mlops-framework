#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

main() {

  SCRIPT=$(readlink -f "$0")
  SCRIPT_PATH=$(dirname "$SCRIPT")
  source "$SCRIPT_PATH"/cdk-account-setup.sh

  # preparing account for cdk application
  cdk_account_setup
}

main "$@"