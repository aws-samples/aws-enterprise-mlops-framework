# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from aws_cdk import (
    Aws,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_iot as iot,
    custom_resources as custres,
)
from aws_cdk import Tags  # , Aspects

import boto3
import constructs
import os
import logging

from config.constants import (
    PROJECT_NAME,

    MODEL_BUCKET_ARN,
    VPC_ID,
    VPC_SUBNETS,
    SG_ID,
    MODEL_BUCKET_KMS_ARN
)

s3_client = boto3.client("s3")


class DeployEC2AndIotRole(Stack):
    """
    Deploy EC2 and Iot Role stack which provisions Iot related ressources to create an EC2 digital twin and the necessary role to run GDK deploy in the deployment accounts.
    """

    def __init__(
        self,
        scope: constructs,
        id: str,
        **kwargs,
    ):
        # The code that defines your stack goes here
        super().__init__(scope, id, **kwargs)

        # Get the instance type from the environment. If none then defaults t3.small.
        if "INSTANCE_TYPE" in os.environ:
            instance_type = os.getenv("INSTANCE_TYPE")
        else:
            instance_type = "t3.small"

        ####
        # 1. Create a VPC to control the network our instance lives on.
        ####

        vpc_id = VPC_ID  # ssm.StringParameter.value_from_lookup(self, "/vpc/id")
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        user_subnets = []
        for idx, subnet in enumerate(VPC_SUBNETS):
            user_subnets.append(
                ec2.Subnet.from_subnet_attributes(
                    scope=self, id=f"subnet{idx}", subnet_id=subnet["id"], availability_zone=subnet["az"]
                )
            )

        if user_subnets:
            subnets = user_subnets
        else:
            private_subnets_with_nat = vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            )
            private_subnets_with_egress = vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS  # This selects private subnets with NAT or egress
            )
            subnets = private_subnets_with_nat.subnets + private_subnets_with_egress.subnets
            
        logging.info("Subnets:", subnets)

        sg_id = SG_ID  # ssm.StringParameter.value_from_lookup(self, "/vpc/sg/id")
        # Create or refer to a security group that only allows inbound traffic.
        security_group = ec2.SecurityGroup.from_lookup_by_id(self, "SG", security_group_id=sg_id)

        ####
        # 2. Create role for edge devices
        ####
        tes_role_name = f"{PROJECT_NAME}-SimulatedEdgeTokenExchangeRole"
        tes_role = iam.Role(
            self,
            tes_role_name,
            role_name=tes_role_name,
            assumed_by=iam.ServicePrincipal("credentials.iot.amazonaws.com"),
        )
        Tags.of(tes_role).add("Name", tes_role_name)

        ## Add permissions for simulated token exchange
        # https://docs.aws.amazon.com/greengrass/v2/developerguide/provision-minimal-iam-policy.html
        tes_policy_name = f"{tes_role_name}Access"
        tes_policy = iam.ManagedPolicy(
            self,
            tes_policy_name,
            managed_policy_name=tes_policy_name,  # Expects the policy to have the same name as the role + Access
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "iot:DescribeCertificate",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams",
                        "s3:GetBucketLocation",
                    ],
                    resources=["*"],
                    effect=iam.Effect.ALLOW,
                )
            ],
        )
        Tags.of(tes_policy).add("Name", "simulated-tes-policy")

        ## Add permissions for handling of kms encrypted material in dev account
        kms_policy = iam.Policy(
            self,
            "power-user-decrypt-kms-policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "kms:CreateAlias",
                        "kms:CreateKey",
                        "kms:Decrypt",
                        "kms:DeleteAlias",
                        "kms:Describe*",
                        "kms:GenerateRandom",
                        "kms:Get*",
                        "kms:List*",
                        "kms:TagResource",
                        "kms:UntagResource",
                        "iam:ListGroups",
                        "iam:ListRoles",
                        "iam:ListUsers",
                    ],
                    resources=[MODEL_BUCKET_KMS_ARN],
                    effect=iam.Effect.ALLOW,
                )
            ],
        )
        Tags.of(kms_policy).add("Name", "power-user-decrypt-kms-policy")

        kms_policy.attach_to_role(tes_role)
        tes_policy.attach_to_role(tes_role)

        ## Add permissions for interacting with IoT Core
        tes_role.add_to_policy(
            iam.PolicyStatement(
                actions=["greengrass:CreateComponentVersion", "greengrass:DescribeComponent"],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )

        ## Add permissions for interacting with S3, SageMaker
        tes_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonS3ReadOnlyAccess",
            )
        )

        tes_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonSageMakerEdgeDeviceFleetPolicy",
            )
        )
        # https://github.com/aws/aws-cdk/issues/10320

        ## Create role for digital twin EC2 to act as greengrass devices
        edge_role = iam.Role(
            self,
            "gg-provisioning",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ec2.amazonaws.com"), iam.ServicePrincipal("ssm.amazonaws.com")
            ),
        )
        Tags.of(edge_role).add("Name", "gg-provisioning")

        ## Provide access to SSM for secure communication with the instance.
        edge_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore",
            )
        )

        edge_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMPatchAssociation",
            )
        )

        ## Provide access to credentials and iot
        ec2_policy = iam.Policy(
            self,
            "gg-provision-policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "iam:AttachRolePolicy",
                        "iam:CreatePolicy",
                        "iam:CreateRole",
                        "iam:GetPolicy",
                        "iam:GetRole",
                        "iam:PassRole",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[
                        tes_policy.managed_policy_arn,
                        tes_role.role_arn,
                        f"arn:aws:iam::aws:policy/{tes_policy.managed_policy_name}",  # DO NOT DELETE, NEEDED FOR GREENGRASS
                    ],
                    sid="CreateTokenExchangeRole",
                ),
                iam.PolicyStatement(
                    actions=[
                        "iot:AddThingToThingGroup",
                        "iot:AttachPolicy",
                        "iot:AttachThingPrincipal",
                        "iot:CreateKeysAndCertificate",
                        "iot:CreatePolicy",
                        "iot:CreateRoleAlias",
                        "iot:CreateThing",
                        "iot:CreateThingGroup",
                        "iot:DescribeEndpoint",
                        "iot:DescribeRoleAlias",
                        "iot:DescribeThingGroup",
                        "iot:GetPolicy",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=["*"],
                    sid="CreateIoTResources",
                ),
                iam.PolicyStatement(
                    actions=[
                        "greengrass:CreateDeployment",
                        "iot:CancelJob",
                        "iot:CreateJob",
                        "iot:DeleteThingShadow",
                        "iot:DescribeJob",
                        "iot:DescribeThing",
                        "iot:DescribeThingGroup",
                        "iot:GetThingShadow",
                        "iot:UpdateJob",
                        "iot:UpdateThingShadow",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=["*"],
                    sid="DeployDevTools",
                ),
            ],
        )

        ## Provide access to artifacts bucket
        s3_policy = iam.Policy(
            self,
            "gg-artifacts-bucket-access-policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                        "s3:GetObjectVersion",
                        "s3:GetBucketAcl",
                        "s3:GetBucketLocation",
                    ],
                    resources=[MODEL_BUCKET_ARN, f"{MODEL_BUCKET_ARN}/*"],
                    effect=iam.Effect.ALLOW,
                )
            ],
        )
        Tags.of(ec2_policy).add("Name", "gg-provision-policy")

        ec2_policy.attach_to_role(edge_role)
        s3_policy.attach_to_role(edge_role)
        kms_policy.attach_to_role(edge_role)

        ####
        # 3. Provision custom resource to create IoT thing group and Token Exchange Role Alias
        ####

        thing_group_name = PROJECT_NAME
        iot_thing_group = iot.CfnThingGroup(self, "iotThingGroup", thing_group_name=thing_group_name)
        Tags.of(iot_thing_group).add("Name", thing_group_name)

        role_alias_name = f"{tes_role_name}Alias"
        iot_role_alias = iot.CfnRoleAlias(
            self,
            "iotRoleAlias",
            role_arn=tes_role.role_arn,
            # the properties below are optional
            role_alias=role_alias_name,
        )
        Tags.of(iot_role_alias).add("Name", role_alias_name)

        ########################################
        # Define Thing Policy

        thing_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iot:Connect", "iot:Publish", "iot:Subscribe", "iot:Receive", "greengrass:*"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iot:AssumeRoleWithCertificate"],
                    resources=[iot_role_alias.attr_role_alias_arn],
                ),
            ]
        )

        iot.CfnPolicy(
            self,
            "GreengrassThingPolicy",
            policy_name=f"{PROJECT_NAME}-GreengrassThingPolicy",
            policy_document=thing_policy_document,
        )

        ####
        # 4. Create role for publishing and deploying to greengrass
        ####
        deploy_role = iam.Role(
            self,
            "gg-deploy-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal(
                    "ec2.amazonaws.com"
                ),  # TODO if creating EC2 in preprod and prod: pass role from dev account as trusted entity instead of ec2
            ),
        )
        Tags.of(deploy_role).add("Name", "gg-deploy-role")

        gg_deploy_policy = iam.Policy(
            self,
            "gg-deploy-policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "greengrass:ListComponentVersions",
                        "greengrass:CreateComponentVersion",
                        "greengrass:CreateDeployment",
                        "iot:DescribeThingGroup",
                        "iot:DescribeJob",
                        "iot:CreateJob",
                        "iot:CancelJob",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=["*"],
                    sid="PublishAndDeploy",
                ),
                iam.PolicyStatement(
                    actions=[
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                        "s3:GetObjectVersion",
                        "s3:GetBucketAcl",
                        "s3:GetBucketLocation",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[MODEL_BUCKET_ARN, f"{MODEL_BUCKET_ARN}/*"],
                    sid="AccessGGArtifactsBucket",
                ),
            ],
        )
        Tags.of(gg_deploy_policy).add("Name", "gg-deploy-policy")

        gg_deploy_policy.attach_to_role(deploy_role)
        ## Provide access to kms
        kms_policy.attach_to_role(deploy_role)

        # Upload Ansible Script

        ########################################
        # Create IoT Thing for Greengrass Core

        thingName = f"{PROJECT_NAME}-digitaltwin"

        iot.CfnThing(self, "GreengrassCoreThing", thing_name=thingName)

        # Add GG installation script to EC2
        multipart_user_data = ec2.MultipartUserData()
        commands_user_data = ec2.UserData.for_linux()

        with open("iot_infra/greengrass/install_ggv2.sh", "r") as f:
            provision_ggv2 = f.read()

        provision_ggv2 = provision_ggv2.replace("$1", Aws.REGION)
        provision_ggv2 = provision_ggv2.replace("$2", thingName)
        provision_ggv2 = provision_ggv2.replace("$3", thing_group_name)
        provision_ggv2 = provision_ggv2.replace("$4", tes_role.role_name)
        provision_ggv2 = provision_ggv2.replace("$5", role_alias_name)
        print(f"provision_ggv2: {provision_ggv2}")

        commands_user_data.add_commands(provision_ggv2)

        multipart_user_data.add_user_data_part(commands_user_data, ec2.MultipartBody.SHELL_SCRIPT, True)
        # multipart_user_data.add_user_data_part(commands_user_data, ec2.MultipartBody.CLOUD_BOOTHOOK, True)

        # Increase the disk space on the device.
        root_volume = ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(25))

        # Create a generic machine image for use with CPU.
        # Still hardcoded
        # TODO: PLEASE CHANGE AMI IF SWITCHING REGIONS. This is a specific ubuntu image required for the Edge application
        image = ec2.MachineImage.generic_linux(ami_map={"eu-west-1": "ami-00aa9d3df94c6c354"})

        # Create ec2 instance to be used instead of edge device
        instance_name = f"{PROJECT_NAME}-digitaltwin"
        instance = ec2.Instance(
            self,
            instance_name,
            role=edge_role,
            instance_type=ec2.InstanceType(instance_type),
            machine_image=image,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=subnets),
            security_group=security_group,
            user_data=multipart_user_data,
            block_devices=[root_volume],
            propagate_tags_to_volume_on_creation=True,
            require_imdsv2=True,
        )
        Tags.of(instance).add("Name", instance_name)

        print(f"Instance created with name: {instance_name}")

    def get_iot_endpoint(self, iot_type):
        endpoint = custres.AwsCustomResource(
            self,
            iot_type,
            on_create={
                "service": "IoT",
                "action": "describeEndpoint",
                "physical_resource_id": custres.PhysicalResourceId.from_response("endpointAddress"),
                "parameters": {"endpointType": iot_type},
            },
            policy=custres.AwsCustomResourcePolicy.from_sdk_calls(
                resources=custres.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
        )
        return endpoint.get_response_field("endpointAddress")
