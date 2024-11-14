#!/bin/bash
DEPLOYMENT_FILE=$1
GDK_ARTEFACTS_DIR=$2
TARGET_ARN=$3

echo "switching folder to $GDK_ARTEFACTS_DIR/ .."
cd $GDK_ARTEFACTS_DIR
echo "Specifying target Things Group ARN in $DEPLOYMENT_FILE:"
jq '.targetArn = "'"$TARGET_ARN"'"' $DEPLOYMENT_FILE > tmp && mv tmp $DEPLOYMENT_FILE

# DEPLOY
echo "Creating deployment with the following specifications:"
echo $(cat deployment.json)
aws greengrassv2 create-deployment --cli-input-json file://$DEPLOYMENT_FILE