#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

main() {


  cmd="$1"

  case $cmd in
    prerequisites)
      echo "Start installing prerequisites like environments and dependencies"
      "$SCRIPT_PATH"/install-prerequisites-brew.sh
      ;;
    config)
      echo "Start updating config files with user inputs"
      "$SCRIPT_PATH"/create-config-files.sh
      ;;
    bootstrap)
      echo "Start bootstrapping Aws accounts"
      "$SCRIPT_PATH"/cdk-bootstrap-accounts.sh
      ;;
    *) echo "Not supported command : $cmd!!!, Supported commands : [prerequisites, config, bootstrap]"
  esac
}

main "$@"
