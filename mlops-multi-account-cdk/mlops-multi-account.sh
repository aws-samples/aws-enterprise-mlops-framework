#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

main() {


  cmd="$1"

  echo "Project Type : $cmd"

  case $cmd in
    create_accounts)
      echo "Start creating aws account using isengard and then create cdk app config"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/isen.sh
      ;;
    setup)
      echo "Start setting up aws accounts, python environments and it's dependencies, nodejs and it's dependencies"
      "$SCRIPT_PATH"/mlops-commons/mlops_commons/scripts/setup.sh "$SCRIPT_PATH/mlops-infra" "$SCRIPT_PATH/mlops-sm-project-template"
      ;;
    infra)
      echo "Start executing mlops infra"
      "$SCRIPT_PATH"/mlops-infra/scripts/mlops-infra.sh "${@:2}"
      ;;
    template)
      echo "Start executing mlops project template"
      "$SCRIPT_PATH"/mlops-sm-project-template/scripts/mlops-template.sh "${@:2}"
      ;;
    *) echo "Not supported command : $cmd!!!, Supported commands : [create_accounts, setup, infra, template]"
  esac
}

main "$@"
