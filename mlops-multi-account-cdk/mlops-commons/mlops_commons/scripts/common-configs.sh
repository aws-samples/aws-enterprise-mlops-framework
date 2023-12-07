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