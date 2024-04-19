#!/bin/bash
# This script setups the aws accounts with the required permissions for CDK deployments, the accounts are bootstrapped
# and configured to enable cross account access as per the architecture diagram

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

bootstrap_conf_file="$SCRIPT_PATH/../mlops-infra/mlops_infra/config/bootstrap.conf"


while read -r line; do

  parts=(${line//#/ })

  account="${parts[0]}"
  region="${parts[1]}"
  profile="${parts[2]}"
  trust_accounts="${parts[3]}"

  if [[ "$trust_accounts" != "" ]];then
    echo "Executing command cdk bootstrap aws://$account/$region --trust $trust_accounts --profile $profile"
    cdk bootstrap aws://$account/$region --trust $trust_accounts --profile $profile
  else
    echo "Executing command cdk bootstrap aws://$account/$region --profile $profile"
    cdk bootstrap aws://$account/$region --profile $profile
  fi

done < "$bootstrap_conf_file"