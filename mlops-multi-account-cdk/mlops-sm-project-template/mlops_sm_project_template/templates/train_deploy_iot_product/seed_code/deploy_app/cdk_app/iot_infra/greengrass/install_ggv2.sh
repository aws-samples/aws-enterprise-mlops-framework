#!/bin/sh

# This sample is non-production-ready template
# © 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
# http://aws.amazon.com/agreement or other written agreement between Customer and either
# Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

# Note: make sure that the entity running this script has the GreengrassProvisionPolicy policy attached
# in order to successfully provision the IoT device (see infrastructure/sm-edge/template.myl)

# if [ $# -ne 5 ]; then
#   echo 1>&2 "Usage: $0 AWS-REGION IOT-THING-NAME IOT_THING_GROUP TES_ROLE_NAME TES_ROLE_ALIAS"
#   exit 3
# fi

sleep 1m # Waits 1 minutes to ensure Digital Twin is attached to the network

AWS_REGION=$1
IOT_THING_NAME=$2
IOT_THING_GROUP=$3
TES_ROLE_NAME=$4
TES_ROLE_ALIAS=$5

echo "\n===[ Installing prerequisites ]===\n"
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo NEEDRESTART_MODE=a apt-get install -y openjdk-8-jdk curl unzip python3-pip

echo "\n===[ Downloading Greengrass v2 ]===\n"
cd /tmp
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassCore
rm greengrass-nucleus-latest.zip

echo "\n===[ Installing and provisioning Greengrass v2 ]===\n"
sudo -E java -Droot='/greengrass/v2' -Dlog.store=FILE -jar ./GreengrassCore/lib/Greengrass.jar \
    --aws-region ${AWS_REGION} \
    --thing-name ${IOT_THING_NAME} \
    --thing-group-name ${IOT_THING_GROUP} \
    --tes-role-name ${TES_ROLE_NAME} \
    --tes-role-alias-name ${TES_ROLE_ALIAS} \
    --component-default-user ggc_user:ggc_group \
    --provision true \
    --setup-system-service true \
    --deploy-dev-tools true

echo "\n===[ Greengrass v2 started ]===\n"

echo "\n===[ Complete ]===\n"
