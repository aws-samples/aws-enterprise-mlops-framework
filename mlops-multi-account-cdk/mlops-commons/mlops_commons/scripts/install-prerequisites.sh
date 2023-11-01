#!/bin/bash
# this script uses Homebrew to do the installations for all prerequisites to deploy the solution described in this repository

aws_cdk_mlops_home_path=~/aws_cdk_mlops
node_version="v18.18.2"
aws_cdk_mlops_profile="$aws_cdk_mlops_home_path/.aws_cdk_mlops_profile"
miniconda_home_path="$aws_cdk_mlops_home_path/miniconda3"
nodejs_home_path="$aws_cdk_mlops_home_path/nodejs"
export PATH=$miniconda_home_path/bin:$PATH
export PATH=$nodejs_home_path/node-$node_version/bin:$PATH

if [[ -f $aws_cdk_mlops_profile ]]; then
  source $aws_cdk_mlops_profile
fi

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

get_os_name(){
  os_name=$(grep -i -E "^name" /etc/os-release)
    case "$os_name" in
      *Ubuntu*) echo "Ubuntu" ;;
      *Red*Hat*) echo "RedHat" ;;
      *Fedora*) echo "Fedora" ;;
      *CentOS*) echo "CentOS" ;;
      *Amazon*) echo "AmazonLinux" ;;
      *)  echo "" ;;
    esac
}

get_arch_type(){
  uname -m
}

update_executable_path(){

  path_to_add=$1
  echo "shell -> $SHELL"

    case "$SHELL" in

      */zsh)

        if [[ -f ~/.zprofile ]]; then
          if [[ -z $(grep "export PATH=$path_to_add/bin:" ~/.zprofile) ]]; then
            echo export PATH=$path_to_add/bin:$PATH >> ~/.zprofile
            echo "adding nodejs path to  ~/.zprofile"
          fi
          source ~/.zprofile
        fi

        if [[ -f ~/.zshrc ]]; then
          if [[ -z $(grep "export PATH=$path_to_add/bin:" ~/.zshrc) ]]; then
            echo export PATH=$path_to_add/bin:$PATH >> ~/.zshrc
            echo "adding nodejs path to  ~/.zshrc"
          fi
          # TODO: it is creating error, so not loading, error due to conda setup in it for terminal
          #source ~/.zshrc
        fi
        ;;

      */bash)

        if [[ -f ~/.bash_profile ]]; then
          if [[ -z $(grep "export PATH=$path_to_add/bin:" ~/.bash_profile) ]]; then
            echo export PATH=$path_to_add/bin:$PATH >> ~/.bash_profile
            echo "adding nodejs path to  ~/.bash_profile"
          fi
          source ~/.bash_profile
        fi
        ;;

      *) echo "not supported shell"
        ;;
    esac


    if [[ ! -f $aws_cdk_mlops_profile ]] || [[ -z $(grep "export PATH=$path_to_add/bin:" $aws_cdk_mlops_profile) ]]; then
      echo "export PATH=$path_to_add/bin:$PATH" >> $aws_cdk_mlops_profile
      echo "adding nodejs path to  $aws_cdk_mlops_profile"
    fi
    source $aws_cdk_mlops_profile

}

install_miniconda(){
  mkdir -p $miniconda_home_path
  arc_type=$(get_arch_type)
  os_type=$(get_os_type)
  url=https://repo.anaconda.com/miniconda/Miniconda3-latest-"$os_type"-"$arc_type".sh
  echo "Downloading miniconda for arc_type $arc_type and os_type $os_type from $url and saving it to $miniconda_home_path"
  curl -L "$url" -o "$miniconda_home_path/miniconda.sh"
  bash $miniconda_home_path/miniconda.sh -b -u -p $miniconda_home_path
  rm -rf $miniconda_home_path/miniconda.sh
  export PATH=$miniconda_home_path/bin:$PATH
  if [[ ! -f $aws_cdk_mlops_profile ]] || [[ -z $(grep "export PATH=$miniconda_home_path/bin:" $aws_cdk_mlops_profile) ]]; then
    echo "export PATH=$miniconda_home_path/bin:$PATH" >> $aws_cdk_mlops_profile
    echo "adding miniconda path to  $aws_cdk_mlops_profile"
  fi
  echo "miniconda installed at $miniconda_home_path"
}

install_nodejs(){

  mkdir -p $nodejs_home_path
  arc_type=$(get_arch_type)
  os_type=$(get_os_type)

  file_extension="gz"
  if [[ "$os_type" == "MacOSX" ]]; then

    os_type="darwin"
    update_executable_path "$nodejs_home_path/node-$node_version/bin"

     if [[ "$arc_type" == *"_64" ]]; then
       arc_type="x64"
     else
       arc_type="arm64"
     fi

  else

    os_type="linux"
    file_extension="xz"
    path_to_add="$nodejs_home_path/node-$node_version/bin"

    if [[ -f ~/.bashrc ]]; then
      if [[ -z $(grep "export PATH=$path_to_add:" ~/.bashrc) ]]; then
        echo export PATH=$path_to_add:$PATH >> ~/.bashrc
      fi
      # source ~/.bashrc
      echo "setting ~/.bashrc"
    fi

    if [[ ! -f $aws_cdk_mlops_profile ]] || [[ -z $(grep "export PATH=$path_to_add:" $aws_cdk_mlops_profile) ]]; then
      echo "export PATH=$path_to_add:$PATH" >> $aws_cdk_mlops_profile
      echo "adding nodejs path to  $aws_cdk_mlops_profile"
    fi
    source $aws_cdk_mlops_profile

    if [[ "$arc_type" == *"_64" ]]; then
       arc_type="x64"
    else
       arc_type="arm64"
    fi
  fi

  # https://nodejs.org/dist/v18.18.2/node-v18.18.2-darwin-x64.tar.gz
  # https://nodejs.org/dist/v18.18.2/node-v18.18.2-darwin-arm64.tar.gz
  # https://nodejs.org/dist/v18.18.2/node-v18.18.2-linux-x64.tar.xz
  #

  node_file_name=node-"$node_version-$os_type-$arc_type.tar.$file_extension"
  simple_node_file_name="node-$node_version.tar"
  url=https://nodejs.org/dist/"$node_version"/$node_file_name

  echo "Downloading nodejs for arc_type $arc_type and os_type $os_type from $url and saving it to $nodejs_home_path"
  curl -L "$url" -o "$nodejs_home_path/$simple_node_file_name"

  # extracting the downloaded nodejs tar file
  tar -xJvf "$nodejs_home_path/$simple_node_file_name" -C $nodejs_home_path

  # removing if there is any existing installation
  rm -rf "$nodejs_home_path/node-$node_version"

  # renaming the downloaded nodejs installation to node-$node_version folder
  mv "$nodejs_home_path/node-$node_version-$os_type-$arc_type" "$nodejs_home_path/node-$node_version"

  # removing the downloaded nodejs tar file
  rm -rf "${nodejs_home_path:?}/$simple_node_file_name"

  export PATH=$nodejs_home_path/node-$node_version/bin:$PATH

  echo "nodejs installed at $nodejs_home_path"
}

install_docker(){

  os_type=$(get_os_type)

  if [[ "$os_type" == "MacOSX" ]]; then
    brew install --cask docker
  else
    echo "install docker for linux"
    os_name=$(get_os_name)
    if [[ "$os_name" == "AmazonLinux" ]]; then
      yum_cmd="yum"
      if [[ "$USER" != "root" ]]; then
        echo "current user : $USER , doesn't have root permission, kindly approve it to install packages"
        yum_cmd="sudo yum"
      fi
      $yum_cmd install docker
    else
      curl -fsSL https://get.docker.com -o get-docker.sh
      bash ./get-docker.sh
    fi
  fi
}

install_linux_packages(){
  os_type=$(get_os_type)
  if  [[ "$os_type" == "Linux" ]]; then
    os_name=$(get_os_name)
    # echo "installing linux packages for $os_name"
    if [[ "$os_name" == "Ubuntu" ]]; then

      apt_cmd="apt-get"
      dpkg_cmd="dpkg"
      if [[ "$USER" != "root" ]]; then
        echo "current user : $USER , doesn't have root permission, kindly approve it to install packages"
        apt_cmd="sudo apt-get"
        dpkg_cmd="sudo dpkg"
      fi

      [[ -z "$(which curl 2>&1 |  grep -i -E curl)" ]] && $apt_cmd update -y && $apt_cmd upgrade -y && $apt_cmd install -y curl
      [[ -z "$($dpkg_cmd -s gcc 2>&1 |  grep -i -E ^Package)" ]] && $apt_cmd install -y gcc
      [[ -z "$($dpkg_cmd -s python3-dev 2>&1 |  grep -i -E ^Package)" ]] && $apt_cmd install -y python3-dev

    elif [[ "$os_name" == "RedHat" ]] || [[ "$os_name" == "Fedora" ]] || [[ "$os_name" == "CentOS" ]] || [[ "$os_name" == "AmazonLinux" ]]; then

      yum_cmd="yum"
      if [[ "$USER" != "root" ]]; then
        echo "current user : $USER , doesn't have root permission, kindly approve it to install packages"
        yum_cmd="sudo yum"
      fi

      [[ -z "$($yum_cmd list installed which 2>&1 |  grep -i -E which)" ]] && $yum_cmd update -y && $yum_cmd upgrade -y && $yum_cmd install -y which --allowerasing
      [[ -z "$($yum_cmd list installed curl 2>&1 |  grep -i -E curl)" ]] && $yum_cmd update -y && $yum_cmd upgrade -y && $yum_cmd install -y curl --allowerasing
      [[ -z "$($yum_cmd list installed gcc 2>&1 |  grep -i -E ^gcc)" ]] && $yum_cmd install -y gcc --allowerasing
      [[ -z "$($yum_cmd list installed python3-devel 2>&1 |  grep -i -E ^python3-devel)" ]] && $yum_cmd install -y python3-devel --allowerasing

    else
      echo "not supported os : $os_name"
    fi
  fi
}

install_prerequisites(){

  if [[ ! -d "$aws_cdk_mlops_home_path" ]]; then
    echo "$aws_cdk_mlops_home_path doesn't exist, creating it now."
    mkdir -p $aws_cdk_mlops_home_path
  fi

  # install dev packages for if os is linux
  install_linux_packages

  # install miniconda to manage python packages
  [[ -z "$(which conda | grep /conda)" ]] && install_miniconda

  echo "using miniconda from $(which conda)"

  # conda doesn't initialize from shell, below step to fix that
  CONDA_BASE=$(conda info --base)
  source "$CONDA_BASE"/etc/profile.d/conda.sh
  conda init | grep -v -i -E "no change|action" || test $? = 1

  # install nodejs (required for aws cdk)
  [[ -z "$(which node | grep /node )" ]] && install_nodejs

  echo "using nodejs from $(which node)"

  # install docker (mainly to handle bundling CDK assets)
  [[ -z "$(which docker | grep /docker )" ]] && install_docker

  # install aws cdk
  # setting cdk cli version to 2.100.0 and aws-cdk-lib@2.100.0  as version onward has
  # issue related to s3, as of now latest version is 2.101.0
  # as version onward has issue related to s3, as of now latest version is 2.101.0
  # which is also having this s3 policy issue "Policy has invalid action (Service: S3, Status Code: 400"
  # https://github.com/aws/aws-cdk/issues/27542
  CDK_VERSION=2.100.0
  [[ -z "$(npm list -g | grep aws-cdk@$CDK_VERSION)" ]] && npm install -g aws-cdk@$CDK_VERSION

  # setup python environment
  env_name=cdk-env
  [[ -z "$(conda env list | grep $env_name)" ]] && conda create -n "$env_name" python=3.11 -y
  conda activate "$env_name"
  echo "using python from $(which python)"

  # install project dependencies from requirements.txt , don't display already installed dependencies
  for project_path in "${@:1}"
  do
    pip install  -r "$project_path/requirements.txt" | grep -v "Requirement already satisfied:" || test $? = 1
    # now you should have all the necessary packages setup on your machines and should proceed with creating the aws profiles to start setting up the accounts and deploying the solution
  done
}
