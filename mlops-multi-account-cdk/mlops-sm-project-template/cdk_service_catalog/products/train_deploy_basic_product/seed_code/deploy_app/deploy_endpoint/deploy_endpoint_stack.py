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

import logging
from logging import Logger

from datetime import datetime, timezone

import constructs
from aws_cdk import (
    Aws,
    CfnParameter,
    Stack,
    Tags,
    aws_iam as iam,
    aws_kms as kms,
    aws_sagemaker as sagemaker,
)

from .get_approved_package import get_approved_package
from cdk_utilities.cdk_deploy_app_config import ProductionVariantConfig
from cdk_utilities.constants import (
    PROJECT_NAME,
    PROJECT_ID,
    MODEL_PACKAGE_GROUP_NAME,
    DEV_ACCOUNT,
    ECR_REPO_ARN,
    MODEL_BUCKET_ARN,
)


class DeployEndpointStack(Stack):
    """
    Deploy Endpoint Stack
    Deploy Endpoint stack which provisions SageMaker Model Endpoint resources.
    """
    logging.basicConfig(level=logging.INFO)

    def __init__(
            self,
            scope: constructs,
            id: str,
            product_variant_conf: ProductionVariantConfig,
            **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        self.logger: Logger = logging.getLogger(self.__class__.__name__)

        self.logger.info(f'PROJECT_ID : {PROJECT_ID}, PROJECT_NAME : {PROJECT_NAME}, '
                         f'MODEL_PACKAGE_GROUP_NAME :{MODEL_PACKAGE_GROUP_NAME}, '
                         f'DEV_ACCOUNT : {DEV_ACCOUNT}, ECR_REPO_ARN : {ECR_REPO_ARN}, '
                         f'MODEL_BUCKET_ARN : {MODEL_BUCKET_ARN}, '
                         f'product_variant_conf : {product_variant_conf}')

        self.logger.info('Deploying Endpoint Stack')

        Tags.of(self).add("sagemaker:project-id", PROJECT_ID)
        Tags.of(self).add("sagemaker:project-name", PROJECT_NAME)
        Tags.of(self).add("sagemaker:deployment-stage", Stack.of(self).stack_name)

        app_subnet_ids = CfnParameter(
            self,
            "subnet-ids",
            type="AWS::SSM::Parameter::Value<List<String>>",
            description="Account APP Subnets IDs",
            min_length=1,
            default="/vpc/subnets/private/ids",
        ).value_as_list

        sg_id = CfnParameter(
            self,
            "sg-id",
            type="AWS::SSM::Parameter::Value<String>",
            description="Account Default Security Group id",
            min_length=1,
            default="/vpc/sg/id",
        ).value_as_string

        self.logger.info(f'app_subnet_ids : {app_subnet_ids}, sg_id : {sg_id}')

        # iam role that would be used by the model endpoint to run the inference
        model_execution_policy = iam.ManagedPolicy(
            self,
            "ModelExecutionPolicy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "s3:Put*",
                            "s3:Get*",
                            "s3:List*",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[
                            MODEL_BUCKET_ARN,
                            f"{MODEL_BUCKET_ARN}/*",
                        ],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "kms:Encrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[f"arn:aws:kms:{Aws.REGION}:{DEV_ACCOUNT}:key/*"],
                    ),
                ]
            ),
        )

        if ECR_REPO_ARN:
            model_execution_policy.add_statements(
                iam.PolicyStatement(
                    actions=["ecr:Get*"],
                    effect=iam.Effect.ALLOW,
                    resources=[ECR_REPO_ARN],
                )
            )

        model_execution_role = iam.Role(
            self,
            "ModelExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                model_execution_policy,
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
            ],
        )

        # setup timestamp to be used to trigger the custom resource update event to retrieve latest approved model
        # and to be used with model and endpoint config resources' names
        now = datetime.now().replace(tzinfo=timezone.utc)

        timestamp = now.strftime("%Y%m%d%H%M%S")

        # get latest approved model package from the model registry (only from a specific model package group)
        latest_approved_model_package = get_approved_package()

        self.logger.info(f'latest_approved_model_package : {latest_approved_model_package}')

        # Sagemaker Model
        model_name = f"{MODEL_PACKAGE_GROUP_NAME}-{timestamp}"

        model = sagemaker.CfnModel(
            self,
            "Model",
            execution_role_arn=model_execution_role.role_arn,
            model_name=model_name,
            containers=[
                sagemaker.CfnModel.ContainerDefinitionProperty(
                    model_package_name=latest_approved_model_package
                )
            ],
            vpc_config=sagemaker.CfnModel.VpcConfigProperty(
                security_group_ids=[sg_id],
                subnets=app_subnet_ids,
            ),
        )

        # Sagemaker Endpoint Config, name must be max 63 characters length
        endpoint_config_name = f"{MODEL_PACKAGE_GROUP_NAME}-ec-{timestamp}"[:63]

        production_variant = sagemaker.CfnEndpointConfig.ProductionVariantProperty(
            initial_instance_count=product_variant_conf.initial_instance_count,
            initial_variant_weight=product_variant_conf.initial_variant_weight,
            instance_type=product_variant_conf.instance_type,
            variant_name=product_variant_conf.variant_name,
            model_name=model_name,
        )

        kms_key_id = None
        # if the instance type is not having nvme ssd, then create a kms key to encrypt the assets bucket
        if 'd' not in product_variant_conf.instance_type:
            # create kms key to be used by the assets bucket
            kms_key = kms.Key(
                self,
                "endpoint-kms-key",
                description="key used for encryption of data in Amazpn SageMaker Endpoint",
                enable_key_rotation=True,
                policy=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["kms:*"],
                            effect=iam.Effect.ALLOW,
                            resources=["*"],
                            principals=[iam.AccountRootPrincipal()],
                        )
                    ]
                ),
            )
            kms_key_id = kms_key.key_id

        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "EndpointConfig",
            endpoint_config_name=endpoint_config_name,
            kms_key_id=kms_key_id,
            production_variants=[production_variant],
        )

        endpoint_config.add_depends_on(model)

        # Sagemaker Endpoint
        endpoint_name = f"{MODEL_PACKAGE_GROUP_NAME}-e"

        endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
            endpoint_config_name=endpoint_config.endpoint_config_name,
            endpoint_name=endpoint_name,
        )

        endpoint.add_depends_on(endpoint_config)

        self.endpoint = endpoint
