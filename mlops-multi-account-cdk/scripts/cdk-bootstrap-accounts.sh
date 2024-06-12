#!/bin/bash
# This script setups the aws accounts with the required permissions for CDK deployments, the accounts are bootstrapped
# and configured to enable cross account access as per the architecture diagram

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

bootstrap_conf_file="$SCRIPT_PATH/bootstrap_conf.tmp"

read -r -p 'Have you already created AWS profiles for all accounts that you would like to bootstrap (they should match the names found in bootstrap_conf.tmp - See README) [y/n]:' env_choice

if [[ "$env_choice" != "y" ]];then
    echo "Please create AWS profiles first and rerun this command"
    exit
fi

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