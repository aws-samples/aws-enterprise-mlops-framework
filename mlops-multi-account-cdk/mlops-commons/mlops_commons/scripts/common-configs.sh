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
      *Debian*) echo "Debian" ;;
      *)  echo "" ;;
    esac
}

get_arch_type(){
  uname -m
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