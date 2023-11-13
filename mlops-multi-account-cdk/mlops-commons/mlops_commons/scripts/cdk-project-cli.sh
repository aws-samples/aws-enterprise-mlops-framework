#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository
set -e

CLI_SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
CLI_SCRIPT_PATH=$(dirname "$CLI_SCRIPT")
PROJECT_SCRIPT=$(readlink -f "$0")
PROJECT_SCRIPT_PATH=$(dirname "$PROJECT_SCRIPT")
aws_cdk_mlops_home_path=~/aws_cdk_mlops
aws_cdk_mlops_profile="$aws_cdk_mlops_home_path/.aws_cdk_mlops_profile"

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
    if [[ -f "$aws_cdk_mlops_profile" ]]; then
      source "$aws_cdk_mlops_profile"
    fi
}

load_linux_profile(){
  source ~/.bashrc
  if [[ -f "$aws_cdk_mlops_profile" ]]; then
    source "$aws_cdk_mlops_profile"
  fi
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
    cdk_env="cdk-env"
    echo "Activating python env : $cdk_env"
    # conda doesn't initialize from shell, below step to fix that
    load_profile
    CONDA_BASE=$(conda info --base)
    source "$CONDA_BASE"/etc/profile.d/conda.sh
    conda init | grep -v -i -E "no change|action" || test $? = 1
    conda activate "$cdk_env"
}

get_governance_profile() {
  cd "$CLI_SCRIPT_PATH/../../" || exit
  profile="$(conda run -n $cdk_env python -m mlops_commons.utilities.config_helper get_governance_profile)"
  export GOVERNANCE_PROFILE="$profile"
}

execute_cdk_command() {
    cdk_cmd="${@:2}"
    echo "Executing cdk command : $cdk_cmd"
    activate_python_env
    get_governance_profile "$1"
    governance_profile="${GOVERNANCE_PROFILE:-}"
    echo  "Governance Profile : $governance_profile"
    cd "$PROJECT_SCRIPT_PATH/../" || exit
    cdk "${@:2}" --profile "$governance_profile"
}

execute_make_command(){
  make_cmd="${@:1}"
  echo "Executing make command : $make_cmd"
  cd "$PROJECT_SCRIPT_PATH/../" || exit
  make "$make_cmd"
}

start_project_setup() {
  # preparing account for cdk application
  project_base_path="$1"
  "$CLI_SCRIPT_PATH"/setup.sh "$project_base_path"
}

run_project_cli(){

  cdk_project_name="$1"
  cmd="$2"
  project_base_path="$PROJECT_SCRIPT_PATH/../"

  echo "CDK Project Name : $cdk_project_name"
  echo "Project Base Path : $project_base_path"

  case $cmd in
    setup)
      echo "Start setting $cdk_project_name for aws accounts, python environments and it's dependencies,
      nodejs and it's dependencies"
      start_project_setup "$project_base_path"
      ;;
    synth|deploy|destroy)
      execute_cdk_command "$CLI_SCRIPT_PATH" "${@:2}"
      ;;
    init|clean)
      execute_make_command "${@:2}"
      ;;
    *)
      echo "Not supported command : $cmd!!!, Supported commands : [setup, synth, deploy, destroy]"
      ;;
  esac

}
