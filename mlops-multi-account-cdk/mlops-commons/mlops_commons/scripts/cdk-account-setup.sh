#!/bin/bash
# This script setups the aws accounts with the required permissions for CDK deployments, the accounts are bootstrapped
# and configured to enable cross account access as per the architecture diagram
set -e


cdk_account_setup(){
  SCRIPT=$(readlink -f "$0")
  SCRIPT_PATH=$(dirname "$SCRIPT")
  cd "$SCRIPT_PATH/../../" || exit



  CONDA_BASE=$(conda info --base)
  source "$CONDA_BASE"/etc/profile.d/conda.sh
  env_name=cdk-env
  conda init | grep -v -i -E "no change|action" || test $? = 1
  conda activate "$env_name" || exit

  python -m mlops_commons.utilities.account_setup
}