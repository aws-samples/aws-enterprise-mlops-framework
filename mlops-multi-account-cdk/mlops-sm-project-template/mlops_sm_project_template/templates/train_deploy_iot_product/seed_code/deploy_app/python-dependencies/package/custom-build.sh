#!/bin/bash
APP_DIR=$1
COMPONENT_NAME=$2

if [ $# -ne 2 ]; then
  echo 1>&2 "Usage: $0 APP_DIR COMPONENT_NAME"
  exit 3
fi

export PYTHON_VERSION="3.10"
echo "Packaging Python dependencies for edge runtime"
echo "Using Python version ${PYTHON_VERSION}"
conda create -y -q \
    -n $COMPONENT_NAME \
    python=$PYTHON_VERSION

# get component version
VERSION=$(jq -r '.component."'"$COMPONENT_NAME"'".version' gdk-config.json)
echo "Building version $VERSION of $COMPONENT_NAME"

# create recipes and artifacts folders
mkdir -p ./greengrass-build/recipes
mkdir -p ./greengrass-build/artifacts

# copy recipe to greengrass-build
cp recipe.json ./greengrass-build/recipes

# create custom build directory
mkdir -p ./custom-build/python-dependencies
conda run -n $COMPONENT_NAME pip download -r ../$APP_DIR/requirements.txt -d ./custom-build/python-dependencies

cd custom-build/python-dependencies
zip -rm -X ../python-dependencies.zip *
cd ../..

# copy archive to greengrass-build
mkdir -p ./greengrass-build/artifacts/$COMPONENT_NAME/$VERSION/
cp ./custom-build/python-dependencies.zip ./greengrass-build/artifacts/$COMPONENT_NAME/$VERSION/
