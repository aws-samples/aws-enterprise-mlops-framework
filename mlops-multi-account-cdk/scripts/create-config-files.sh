#!/bin/bash
# This script setups the aws accounts with the required permissions for CDK deployments, the accounts are bootstrapped
# and configured to enable cross account access as per the architecture diagram
SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

read -r -p 'Deployment region (aws regions i.e. us-east-1): ' region
read -r -p 'Governance Account (12-digits): ' gov_account
read -r -p 'Governance Account AWS Profile (used in ~/.aws/config): ' gov_profile

# We create a temporary file with information that will be used to bootstrap the accounts
bootstrap_conf_file="$SCRIPT_PATH/bootstrap_conf.tmp"
echo "$gov_account#$region#$gov_profile#" > "$bootstrap_conf_file"

infra_config_json='['
tmpl_config_json='['
tmpl_config_env_fmt='
    {
        "SET_NAME": "%s",
        "DEV_ACCOUNT": "%s"
    }
'

infra_config_env_fmt='
    {
        "SET_NAME": "%s",
        "DEV_ACCOUNT": "%s",
        "PREPROD_ACCOUNT": "%s",
        "PROD_ACCOUNT": "%s",
        "DEPLOYMENT_REGION": "%s"
    }
'

env_choice='y'

while [[ "$env_choice" == 'y' ]]
do

  read -r -p 'Do you want to add a new business unit details (set of dev/preprod/prod AWS accounts) [y/n] (Answer "n" once you have provided all your business units):' env_choice

  if [[ "$env_choice" == "y" ]];then

    if [[ "$infra_config_json" != '[' ]];then
      infra_config_json="$infra_config_json,"
      tmpl_config_json="$tmpl_config_json,"
    fi

    read -r -p 'Business Unit Name:' set_name
    read -r -p 'Dev Account (12-digits): ' dev_account
    read -r -p 'Dev Account AWS Profile (used in ~/.aws/config): ' dev_profile

    read -r -p 'PreProd Account (12-digits): ' preprod_account
    read -r -p 'PreProd Account AWS Profile (used in ~/.aws/config): ' preprod_profile

    read -r -p 'Prod Account (12-digits): ' prod_account
    read -r -p 'Prod Account AWS Profile (used in ~/.aws/config): ' prod_profile

    infra_config_json="$infra_config_json $(printf "$infra_config_env_fmt" "$set_name" "$dev_account" "$preprod_account" "$prod_account" "$region")"
    tmpl_config_json="$tmpl_config_json $(printf "$tmpl_config_env_fmt" "$set_name" "$dev_account")"
    echo 'Adding information for bootstrapping accounts to' $bootstrap_conf_file
    echo "$dev_account#$region#$dev_profile#$gov_account" >> "$bootstrap_conf_file"
    echo "$preprod_account#$region#$preprod_profile#$dev_account,$gov_account" >> "$bootstrap_conf_file"
    echo "$prod_account#$region#$prod_profile#$dev_account,$gov_account" >> "$bootstrap_conf_file"
  fi

done

infra_config_json="$infra_config_json
]"
tmpl_config_json="$tmpl_config_json
]"

echo 'Updating constants.py files with governance account and region details'
pattern="[0-9a-zA-Z\-]*"
sed -i '' -e "s/^PIPELINE_ACCOUNT = \"$pattern\"/PIPELINE_ACCOUNT = \"$gov_account\"/" \
            -e "s/^DEFAULT_DEPLOYMENT_REGION = \"$pattern\"/DEFAULT_DEPLOYMENT_REGION = \"$region\"/" \
            "$SCRIPT_PATH/../mlops-infra/mlops_infra/config/constants.py"

sed -i '' -e "s/^PIPELINE_ACCOUNT = \"$pattern\"/PIPELINE_ACCOUNT = \"$gov_account\"/" \
            -e "s/^DEFAULT_DEPLOYMENT_REGION = \"$pattern\"/DEFAULT_DEPLOYMENT_REGION = \"$region\"/" \
            "$SCRIPT_PATH/../mlops-sm-project-template/mlops_sm_project_template/config/constants.py"
            
echo 'Updating accounts.json files with business unit (dev/preprod/prod) accounts and region details'
echo "$infra_config_json" > "$SCRIPT_PATH/../mlops-infra/mlops_infra/config/accounts.json"
echo "$tmpl_config_json"  > "$SCRIPT_PATH/../mlops-sm-project-template/mlops_sm_project_template/config/accounts.json"
