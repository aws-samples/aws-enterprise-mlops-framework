#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

create_cdk_app_yml_file(){
  CONDA_BASE=$(conda info --base)
  source "$CONDA_BASE"/etc/profile.d/conda.sh
  env_name=cdk-env
  conda init | grep -v -i -E "no change|action" || test $? = 1
  conda activate "$env_name" || exit

  echo --gov_account "$1"  --gov_region "$2" --gov_profile "$3" --dev_account  "$4" --dev_profile  "$5" --preprod_account  "$6" --preprod_profile  "$7" --prod_account  "$8" --prod_profile "$9"
  python -m mlops_commons.utilities.config_helper "create_config_file" --gov_account "$1"  --gov_region "$2" --gov_profile "$3" --dev_account  "$4" --dev_profile  "$5" --preprod_account  "$6" --preprod_profile  "$7" --prod_account  "$8" --prod_profile "$9"
}

main() {

  SCRIPT=$(readlink -f "$0")
  SCRIPT_PATH=$(dirname "$SCRIPT")
  cd "$SCRIPT_PATH/../../" || exit

  export PYTHONIOENCODING=utf-8

  echo "Before proceeding, please re-authenticate through midway "
  mwinit

  random="$RANDOM"

  default_region="eu-west-1"
  echo "Enter Region[default: $default_region] :"
  read -r region
  if [[ -z "$region" ]]; then
    region="$default_region"
  fi

  echo "Enter your manager's alias to use as secondary owner of this account :"
  read -r secondary_owner

  gov_account=""
  gov_profile=""
  dev_account=""
  dev_profile=""
  preprod_account=""
  preprod_profile=""
  prod_account=""
  prod_profile=""

  for stage in governance dev preprod prod
    do
      unique_user="$USER"-mlops-$stage-"$random"
      email="$unique_user"@amazon.com
      echo "Start creating new aws account using email : $email, region : $region , secondary_owner : $secondary_owner"
      isengardcli create "$email" --noconfirm --title "$USER"-mlops-$stage-"$random" --description "MLOps multi account for $USER"-mlops-$stage-"$random" --region "$region"   --secondary-owner "$secondary_owner"
      echo "Creating aws iam role for account by $email"
      isengardcli add-role "$email"
      echo "Creating aws profile for account by $email"
      isengardcli add-profile "$email" --region "$region" --nocache

      profile="$unique_user"-Admin
      echo "profile : $profile"
      account=$(aws sts get-caller-identity --query 'Account' --output text --profile "$profile")
      echo "Account : $account"
      if [[ "$stage" = "governance" ]]; then
        gov_account="$account"
        gov_profile="$profile"
      elif [[ "$stage" = "dev" ]]; then
        dev_account="$account"
        dev_profile="$profile"
      elif [[ "$stage" = "preprod" ]]; then
        preprod_account="$account"
        preprod_profile="$profile"
      elif [[ "$stage" = "prod" ]]; then
        prod_account="$account"
        prod_profile="$profile"
      fi
    done

    create_cdk_app_yml_file "$gov_account" "$region" "$gov_profile" "$dev_account" "$dev_profile" "$preprod_account" "$preprod_profile" "$prod_account" "$prod_profile"

}

main "$@"