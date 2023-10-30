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
from logging import Logger
from pathlib import Path
import datetime
import aws_cdk
import aws_cdk as cdk
from aws_cdk import Stack, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import CfnParameter
from aws_cdk import aws_servicecatalog as servicecatalog
from constructs import Construct

from mlops_commons.macros.string_macro import StringMacro
from mlops_commons.utilities.log_helper import LogHelper
from mlops_commons.utilities.s3_utils import S3Utils


class SageMakerServiceCatalog(Stack):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            app_prefix: str,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.logger: Logger = LogHelper.get_logger(self)

        # Note - macro name must be unique on account level. String macro is being used in
        # use-case product stack to lower case the project name which is being used as a
        # part for creating s3 bucket name
        string_macro: StringMacro = StringMacro(self, construct_id=f"{app_prefix}-string-macro", app_prefix=app_prefix)
        string_macro.create(macro_name=f"{app_prefix.capitalize()}StringFn")

        execution_role_arn = CfnParameter(
            self,
            "ExecutionRoleArn",
            type="AWS::SSM::Parameter::Value<String>",
            description="The SageMaker Studio execution role",
            min_length=1,
            default="/mlops/role/lead",
        ).value_as_string

        bucket_name: str = S3Utils.create_bucket_name(
            prefix=app_prefix,
            name_part1='sc-product',
            name_part2='assets',
            suffix_part1=kwargs.get('env')['account'],
            suffix_part2=kwargs.get('env')['region'],
            convert_region_to_short_code=True
        )
        self.logger.info(f'Creating sc-product-assets artifact bucket : {bucket_name}')

        sc_product_artifact_bucket = s3.Bucket(
            self,
            'MLOpsProductAssetsBucket',
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )

        # Service Catalog Portfolio
        portfolio = servicecatalog.Portfolio(
            self,
            "SM_Projects_Portfolio",
            display_name="SM Projects Portfolio",
            provider_name="ML Admin Team",
            description="Products for SM Projects",
        )

        execute_role = iam.Role.from_role_arn(self,
                                              'PortfolioExecutionRoleArn',
                                              execution_role_arn,
                                              mutable=False
                                              )
        portfolio.give_access_to_role(execute_role)
        launch_role: iam.Role = self.create_launch_role()

        # Adding sagemaker projects products
        self.add_all_products(
            app_prefix=app_prefix,
            portfolio=portfolio,
            launch_role=launch_role,
            sc_product_artifact_bucket=sc_product_artifact_bucket,
        )

    def add_all_products(
            self,
            app_prefix: str,
            portfolio: servicecatalog.Portfolio,
            launch_role: iam.Role,
            sc_product_artifact_bucket: s3.Bucket,
            templates_directory: str = "cdk_service_catalog/products"
    ):
        templates_path = Path(templates_directory)
        for file in filter(lambda x: 'seed_code' not in x.parts
                                     and 'constructs' not in x.parts
                                     and '__init__' != x.stem
                                     and 'class MLOpsStack' in open(x).read(),
                           templates_path.glob("*/*.py")):
            SageMakerServiceCatalogProduct(
                self,
                construct_id=f'{file.parts[-2]}_{file.stem}',
                app_prefix=app_prefix,
                portfolio=portfolio,
                template_py_file=file,
                launch_role=launch_role,
                sc_product_artifact_bucket=sc_product_artifact_bucket

            )

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
                    "cloudformation:CreateChangeSet",
                    "cloudformation:DescribeChangeSet",
                    "cloudformation:ExecuteChangeSet",
                    "cloudformation:ListChangeSets"

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
            app_prefix: str,
            portfolio: servicecatalog.Portfolio,
            template_py_file: Path,
            launch_role: iam.Role,
            sc_product_artifact_bucket: s3.Bucket,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        module_name: str = template_py_file.stem
        short_name = f'{template_py_file.parts[-2]}-{module_name.replace("_product_stack", "")}'

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

        try:
            product_version = template_module.MLOpsStack.get_product_version()
        except AttributeError:
            product_version = 'v1'

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
                            app_prefix=app_prefix,
                            asset_bucket=sc_product_artifact_bucket,
                            **kwargs,
                        )
                    ),
                    product_version_name=product_version,
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

        # adding timestamp to record creation time of the product to resolve caching issue
        Tags.of(sm_projects_product).add(
            key="created_at", value=f"{datetime.datetime.utcnow().isoformat()}"
        )
