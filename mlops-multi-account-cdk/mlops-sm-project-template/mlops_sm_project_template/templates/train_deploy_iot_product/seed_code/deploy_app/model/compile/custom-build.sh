#!/bin/bash
COMPONENT_NAME=$1

if [ $# -ne 1 ]; then
  echo 1>&2 "Usage: $0 COMPONENT-NAME"
  exit 3
fi

echo "Installing libraries for build"
conda create -y -q \
    -n $COMPONENT_NAME \
    python=3.10

conda run -n $COMPONENT_NAME \
    pip install --no-cache-dir \
        xgboost \
        onnx \
        onnxmltools \
        onnxconverter_common \
        protobuf \
        skl2onnx

VERSION=$(jq -r '.component."'"$COMPONENT_NAME"'".version' gdk-config.json)
echo "Building version $VERSION of $COMPONENT_NAME"

rm -rf ./greengrass-build
mkdir -p ./greengrass-build/recipes
mkdir -p ./greengrass-build/artifacts

# copy recipe to greengrass-build
cp recipe.json ./greengrass-build/recipes

# create custom build directory
rm -rf ./custom-build
mkdir -p ./custom-build/$COMPONENT_NAME

conda run --name $COMPONENT_NAME \
    python ./compile/onnx_converter.py \
        --input . \
        --output ./custom-build/$COMPONENT_NAME

# copy archive to greengrass-build
mkdir -p ./greengrass-build/artifacts/$COMPONENT_NAME/$VERSION/
cp ./custom-build/$COMPONENT_NAME/* ./greengrass-build/artifacts/$COMPONENT_NAME/$VERSION/
