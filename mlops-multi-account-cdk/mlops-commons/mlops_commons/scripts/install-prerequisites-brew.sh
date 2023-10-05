#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

#SCRIPT=$(readlink -f "$0")
#SCRIPT_PATH=$(dirname "$SCRIPT")


# install miniconda to manage python packages
[[ -z "$(brew list | grep miniconda)" ]] && brew install --cask miniconda

# conda doesn't initialize from shell, below step to fix that
CONDA_BASE=$(conda info --base)
source "$CONDA_BASE"/etc/profile.d/conda.sh
conda init

# install nodejs (required for aws cdk)
[[ -z "$(which docker | grep /docker )" ]] && brew install node

# install docker (mainly to handle bundling CDK assets)
[[ -z "$(brew list | grep miniconda)" ]] && brew install --cask docker

# install aws cdk
[[ -z "$(npm list -g | grep aws-cdk)" ]] && npm install -g aws-cdk

# setup python environment
env_name=cdk-env
[[ -z "$(conda env list | grep $env_name)" ]] && conda create -n "$env_name" python=3.11 -y
conda activate "$env_name"


# install project dependencies from requirements.txt
pip install -r "$1/requirements.txt"
# now you should have all the necessary packages setup on your machines and should proceed with creating the aws profiles to start setting up the accounts and deploying the solution
