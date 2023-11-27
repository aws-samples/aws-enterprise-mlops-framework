#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

main() {


  cmd="$1"

  echo "Main command : $cmd"

  case $cmd in

    setup)
      echo "Start setting up aws accounts, python environments and it's dependencies, nodejs and it's dependencies, cdk app config and bootstrapping"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/prerequisites.sh "$SCRIPT_PATH/mlops-infra" "$SCRIPT_PATH/mlops-sm-project-template"
      echo ""
      echo "Now start preparing cdk app config"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/config.sh
      echo ""
      echo "Now start bootstrapping aws accounts"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/bootstrap.sh
      ;;
    prerequisites|dependencies|install)
      echo "Start installing prerequisites like environments and it's dependencies, nodejs and it's dependencies"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/prerequisites.sh "$SCRIPT_PATH/mlops-infra" "$SCRIPT_PATH/mlops-sm-project-template"
      ;;
    config)
      echo "Start preparing config as per user input"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/config.sh
      ;;
    bootstrap)
      echo "Start bootstrapping Aws accounts"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/bootstrap.sh
      ;;
    infra)
      echo "Start executing mlops infra"
      "$SCRIPT_PATH"/mlops-infra/scripts/mlops-infra.sh "${@:2}"
      ;;
    template)
      echo "Start executing mlops project template"
      "$SCRIPT_PATH"/mlops-sm-project-template/scripts/mlops-template.sh "${@:2}"
      ;;
    *) echo "Not supported command : $cmd!!!, Supported commands : [prerequisites|dependencies|install, config, bootstrap, setup, infra, template]"
  esac
}

main "$@"
