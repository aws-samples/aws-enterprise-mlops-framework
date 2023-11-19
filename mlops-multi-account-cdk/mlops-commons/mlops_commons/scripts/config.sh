#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository
# set -e

create_cdk_app_yml_file(){
  # echo --gov_account "$1"  --gov_region "$2" --gov_profile "$3" --dev_account  "$4" --dev_profile  "$5" --preprod_account  "$6" --preprod_profile  "$7" --prod_account  "$8" --prod_profile "$9"
  python -m mlops_commons.utilities.config_helper "create_config_file" --gov_account "$1"  --gov_region "$2" --gov_profile "$3" --dev_account  "$4" --dev_profile  "$5" --preprod_account  "$6" --preprod_profile  "$7" --prod_account  "$8" --prod_profile "$9"
}

create_using_new_aws_isen_accounts(){

  export PYTHONIOENCODING=utf-8

  echo ""
  echo "Before proceeding, please re-authenticate through midway "
  mwinit

  region="$1"

  random="$RANDOM"

  # echo -n "Enter your manager's alias to use as secondary owner of this account:"
  # read -r secondary_owner

  secondary_owner="$(python -m mlops_commons.utilities.user_details "$USER" )"

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
      echo ""
      echo "Start creating new aws account using email : $email, region : $region , secondary_owner : $secondary_owner"
      isengardcli create "$email" --noconfirm --title "$USER"-mlops-$stage-"$random" --description "MLOps multi account for $USER"-mlops-$stage-"$random" --region "$region"   --secondary-owner "$secondary_owner"
      echo ""
      echo "Creating aws iam role for account by $email"
      isengardcli add-role "$email"
      echo ""
      echo "Creating aws profile for account by $email"
      isengardcli add-profile "$email" --region "$region" --nocache

      profile="$unique_user"-Admin
      echo ""
      echo "profile : $profile"
      account=$(aws sts get-caller-identity --query 'Account' --output text --profile "$profile")
      echo ""
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

create_using_user_provided_details(){

  region="$1"
  gov_account=""
  gov_profile=""
  dev_account=""
  dev_profile=""
  preprod_account=""
  preprod_profile=""
  prod_account=""
  prod_profile=""
  aws_profile_choice="n"

  echo ""
  echo -n "Have you configured Aws Profile for all the Aws Accounts [y/n]:"
  read -r aws_profile_choice

  if [[ "$aws_profile_choice" = "y" ]]; then
    for stage in governance dev preprod prod
      do
        echo ""
        echo -n "Enter $stage profile name: "
        read -r profile
        account=$(aws sts get-caller-identity --query 'Account' --output text --profile "$profile")
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
  else
    echo ""
    echo "Please first configure Aws profiles for governance, dev, preprod, prod accounts and then continue!!!"
    echo ""
    exit 1
  fi

  create_cdk_app_yml_file "$gov_account" "$region" "$gov_profile" "$dev_account" "$dev_profile" "$preprod_account" "$preprod_profile" "$prod_account" "$prod_profile"

}

main(){

  SCRIPT=$(readlink -f "$0")
  SCRIPT_PATH=$(dirname "$SCRIPT")
  cd "$SCRIPT_PATH/../../" || exit

  CONDA_BASE=$(conda info --base)
  source "$CONDA_BASE"/etc/profile.d/conda.sh
  env_name=cdk-env
  conda init | grep -v -i -E "no change|action" || test $? = 1
  conda activate "$env_name" || exit

  export PYTHONIOENCODING=utf-8
  overwrite_config="n"
  config_file="$SCRIPT_PATH"/../config/cdk-app.yml

  if [[ -f "$config_file" ]]; then
    echo ""
    echo -n "There is already a config file, do you still want to overwrite it [y/n]:"
    read -r overwrite_config
    if [[ "$overwrite_config" = "n" ]]; then
      echo "Ok, please make sure that config file ['$config_file'] is up to date with required configuration!!!"
    fi
  else
    overwrite_config="y"
  fi

  if [[ "$overwrite_config" = "y" ]]; then
    has_required_cmds_to_create_account="y"
    if [[ -z "$(which mwinit | grep /mwinit)" ]] || [[ -z "$(which isengardcli | grep /isengardcli)" ]]; then
      has_required_cmds_to_create_account="n"
    fi

    create_prompt=""
    account_choice="[y/n]"
    if [[ "$has_required_cmds_to_create_account" = "y" ]]; then
      create_prompt="or Create New Aws accounts"
      account_choice="[provide/create]"
    fi

    account_prompt="Do you want to provide existing account details $create_prompt $account_choice:"

    echo ""
    echo -n "$account_prompt"
    read -r user_choice_account_provide_or_create

    if [[ "$has_required_cmds_to_create_account" = "n" ]] && [[ "$user_choice_account_provide_or_create" != "y" ]]; then
      echo "Ok, please make sure that you have properly configured configuration file in place."
      exit 0
    fi

    echo ""
    default_region="eu-west-1"
    echo -n "Enter Region [default: $default_region]:"
    read -r region
    if [[ -z "$region" ]]; then
      region="$default_region"
    fi

    if [[ "$has_required_cmds_to_create_account" = "n" ]] && [[ "$user_choice_account_provide_or_create" = "y" ]] || [[ "$user_choice_account_provide_or_create" = "p" ]] || [[ "$user_choice_account_provide_or_create" = "provide" ]]; then
      create_using_user_provided_details "$region"
    elif [[ "$has_required_cmds_to_create_account" = "y" ]] && [[ "$user_choice_account_provide_or_create" = "c" ]] || [[ "$user_choice_account_provide_or_create" = "create" ]]; then
      create_using_new_aws_isen_accounts "$region"
    fi


  fi

}

main "$@"