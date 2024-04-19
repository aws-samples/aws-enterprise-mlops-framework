#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

main() {


  cmd="$1"

  case $cmd in
    prerequisites|dependencies|install)
      echo "Start installing prerequisites like environments and it's dependencies, nodejs and it's dependencies"
      "$SCRIPT_PATH"/install-prerequisites-brew.sh
      ;;
    config)
      echo "Start preparing config as per user input"
      "$SCRIPT_PATH"/mlops-config.sh
      ;;
    bootstrap)
      echo "Start bootstrapping Aws accounts"
      "$SCRIPT_PATH"/bootstrap.sh
      ;;
    *) echo "Not supported command : $cmd!!!, Supported commands : [prerequisites|dependencies|install, config, bootstrap]"
  esac
}

main "$@"
