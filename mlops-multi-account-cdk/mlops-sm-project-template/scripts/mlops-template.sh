#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository
set -e

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")
source "$SCRIPT_PATH/project-setup.sh"

cd "$SCRIPT_PATH/../" || exit
cdk_env="cdk-env"
cmd="$1"
echo "template command : $cmd"

get_os_type(){
    case "$OSTYPE" in
      darwin*)  echo "MacOSX" ;;
      linux*)   echo "Linux" ;;
      solaris*) echo "Linux" ;;
      bsd*)     echo "Linux" ;;
      cygwin*)  echo "Linux" ;; # windows
      msys*)    echo "Linux" ;; # windows
      *)        echo "$OSTYPE" ;;
    esac
}

load_mac_profile(){
    case "$SHELL" in
      */zsh) source ~/.zprofile ;;
      */bash) source ~/.bash_profile ;;
      *) echo "not supported shell" ;;
    esac
}

load_linux_profile(){
  source ~/.bashrc
}

load_profile(){
  os_type=$(get_os_type)
  case "$os_type" in
    MacOSX) load_mac_profile ;;
     Linux) load_linux_profile ;;
      *) echo "unable to load profile as $os_type is not supported os"
  esac

}



activate_python_env() {
    echo "Activating python env : $cdk_env"
    # conda doesn't initialize from shell, below step to fix that
    load_profile
    CONDA_BASE=$(conda info --base)
    source "$CONDA_BASE"/etc/profile.d/conda.sh
    conda init | grep -v -i -E "no change|action" || test $? = 1
    conda activate "$cdk_env"
}

get_governance_profile() {
  # echo "MLOPS_COMMONS_SCRIPTS_PATH : $MLOPS_COMMONS_SCRIPTS_PATH"
  cd "$MLOPS_COMMONS_SCRIPTS_PATH/" || exit
  profile="$(conda run -n $cdk_env python -m mlops_commons.utilities.config_helper get_governance_profile)"
  export GOVERNANCE_PROFILE="$profile"
  cd "$SCRIPT_PATH/../" || exit
}

execute_cdk_command() {
    cdk_cmd=$@
    echo "Executing cdk command : $cdk_cmd"
    activate_python_env
    get_governance_profile
    governance_profile="${GOVERNANCE_PROFILE:-}"
    echo  "Governance Profile : $governance_profile"
    cdk "$@" --profile "$governance_profile"
}

case $cmd in
  setup)
    echo "Start setting mlops project template for aws accounts, python environments and it's dependencies,
    nodejs and it's dependencies"
    start_project_setup
    ;;
  synth|deploy|destroy)
    execute_cdk_command "${@:1}"
    ;;
  *)
    echo "not supported command : $cmd"
    ;;
esac