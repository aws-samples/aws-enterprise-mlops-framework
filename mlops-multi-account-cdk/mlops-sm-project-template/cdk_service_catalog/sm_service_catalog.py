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


import os
from importlib import import_module
from pathlib import Path

import aws_cdk
import aws_cdk as cdk
from aws_cdk import Stack, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import CfnParameter
from aws_cdk import aws_servicecatalog as servicecatalog
from constructs import Construct


class SageMakerServiceCatalog(Stack):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        execution_role_arn = CfnParameter(
            self,
            "ExecutionRoleArn",
            type="AWS::SSM::Parameter::Value<String>",
            description="The SageMaker Studio execution role",
            min_length=1,
            default="/mlops/role/lead",
        ).value_as_string

        default_file_assets_bucket_name: str = (f'cdk-{aws_cdk.DefaultStackSynthesizer.DEFAULT_QUALIFIER}'
                                                f'-assets-{aws_cdk.Aws.ACCOUNT_ID}-{aws_cdk.Aws.REGION}')

        sc_product_artifact_bucket = s3.Bucket.from_bucket_name(
            scope=self,
            id='DEFAULT_FILE_ASSETS_BUCKET',
            bucket_name=default_file_assets_bucket_name,
        )

        # Service Catalog Portfolio
        portfolio = servicecatalog.Portfolio(
            self,
            "SM_Projects_Portfolio",
            display_name="SM Projects Portfolio",
            provider_name="ML Admin Team",
            description="Products for SM Projects",
        )

        # launch_role = iam.Role.from_role_name(
        #     self, "LaunchRole", "AmazonSageMakerServiceCatalogProductsLaunchRole"
        # )
        execute_role = iam.Role.from_role_arn(self,
                                              'PortfolioExecutionRoleArn',
                                              execution_role_arn,
                                              mutable=False
                                              )
        portfolio.give_access_to_role(execute_role)
        launch_role: iam.Role = self.create_launch_role()

        # Adding sagemaker projects products
        self.add_all_products(
            portfolio=portfolio,
            launch_role=launch_role,
            sc_product_artifact_bucket=sc_product_artifact_bucket,
        )

    def add_all_products(
            self,
            portfolio: servicecatalog.Portfolio,
            launch_role: iam.Role,
            templates_directory: str = "cdk_service_catalog/products",
            **kwargs,
    ):
        templates_path = Path(templates_directory)
        [
            SageMakerServiceCatalogProduct(
                self,
                file.stem.replace("_product_stack", ""),
                portfolio=portfolio,
                template_py_file=file,
                launch_role=launch_role,
                **kwargs,
            )
            for file in templates_path.glob("**/*_product_stack.py")
        ]

    def create_launch_role(self) -> iam.Role:
        # Create the launch role
        products_launch_role = iam.Role(
            self,
            "ProductLaunchRole",
            assumed_by=iam.ServicePrincipal("servicecatalog.amazonaws.com"),
            path="/service-role/",
        )

        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSageMakerAdmin-ServiceCatalogProductsServiceRolePolicy"
            )
        )

        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEventBridgeFullAccess")
        )

        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSKeyManagementServicePowerUser")
        )

        products_launch_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("IAMFullAccess"))

        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitFullAccess")
        )

        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodePipeline_FullAccess")
        )

        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeBuildAdminAccess")
        )

        products_launch_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_FullAccess"))
        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMReadOnlyAccess")
        )
        products_launch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryFullAccess")
        )

        products_launch_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*"
                    # TODO lock this policy to only certain roles from the other account that are used for deploying the solution as defined in templates/pipeline_constructs/deploy_pipeline_stack.py
                ],
            ),
        )

        products_launch_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:*",
                    "s3-object-lambda:*",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
        )

        products_launch_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "kms:Create*",
                    "kms:Describe*",
                    "kms:Enable*",
                    "kms:List*",
                    "kms:Put*",
                    "kms:Update*",
                    "kms:Revoke*",
                    "kms:Disable*",
                    "kms:Get*",
                    "kms:Delete*",
                    "kms:ScheduleKeyDeletion",
                    "kms:CancelKeyDeletion",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
        )

        products_launch_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:ssm:*:{cdk.Aws.ACCOUNT_ID}:parameter/mlops/*",
                ],
            ),
        )

        products_launch_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:sagemaker:*:{cdk.Aws.ACCOUNT_ID}:model-package-group/*"],
            ),
        )

        return products_launch_role


class SageMakerServiceCatalogProduct(cdk.NestedStack):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            portfolio: servicecatalog.Portfolio,
            template_py_file: Path,
            launch_role: iam.Role,
            sc_product_artifact_bucket: s3.Bucket,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        module_name: str = template_py_file.stem
        short_name = module_name.replace("_product_stack", "")
        module_path: str = (
            (template_py_file.parent / module_name).as_posix().replace(os.path.sep, ".")
        )
        template_module = import_module(module_path)
        try:
            description = template_module.MLOpsStack.get_description()
        except AttributeError:
            description = "Products for SageMaker Projects"
        try:
            support_email = template_module.MLOpsStack.get_support_email()
        except AttributeError:
            support_email = "ml_admins@example.com"

        try:
            product_name = template_module.MLOpsStack.get_product_name()
        except AttributeError:
            product_name = short_name

        try:
            support_url = template_module.MLOpsStack.get_support_url()
        except AttributeError:
            support_url = 'https://yoursite.com/products/support/'

        try:
            support_description = template_module.MLOpsStack.get_support_description()
        except AttributeError:
            support_description = 'Mention about your support details'

        sm_projects_product = servicecatalog.CloudFormationProduct(
            self,
            short_name,
            product_name=product_name,
            owner="Global ML Team",
            product_versions=[
                servicecatalog.CloudFormationProductVersion(
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                        template_module.MLOpsStack(
                            self,
                            "project",
                            asset_bucket=sc_product_artifact_bucket,
                            **kwargs,
                        )
                    ),
                    product_version_name="v1",
                    validate_template=True,
                )
            ],
            description=description,
            support_email=support_email,
            support_description=support_description,
            support_url=support_url,
        )
        portfolio.add_product(sm_projects_product)
        portfolio.set_launch_role(sm_projects_product, launch_role)
        Tags.of(sm_projects_product).add(
            key="sagemaker:studio-visibility", value="true"
        )
