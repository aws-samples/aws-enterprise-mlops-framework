#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

main() {

  SCRIPT=$(readlink -f "$0")
  SCRIPT_PATH=$(dirname "$SCRIPT")
  source "$SCRIPT_PATH"/install-prerequisites.sh

  # installing pre requisites
  install_prerequisites "$@"

}

main "$@"