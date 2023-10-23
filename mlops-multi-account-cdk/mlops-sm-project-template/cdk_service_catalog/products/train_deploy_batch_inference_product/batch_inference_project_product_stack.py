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
from typing import Optional, Any

import aws_cdk
from aws_cdk import (
    Aws,
    Tags,
    aws_s3 as s3,
    aws_iam as iam,
    aws_kms as kms,
    aws_ecr as ecr,
    aws_sagemaker as sagemaker,
    aws_servicecatalog as sc,
    aws_codecommit as codecommit,
)

from constructs import Construct

from cdk_service_catalog.products.constructs.build_pipeline import BuildPipelineConstruct
from cdk_service_catalog.products.constructs.deploy_pipeline import DeployPipelineConstruct
from cdk_service_catalog.products.constructs.ssm import SSMConstruct
from cdk_utilities.seed_code_helper import SeedCodeHelper

from mlops_commons.utilities.zip_utils import ZipUtility

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


class MLOpsStack(sc.ProductStack):
    DESCRIPTION: str = ("This template includes a build and a deploy code repository (CodeCommit) associated "
                        "to their respective CICD pipeline (CodePipeline). The build repository and CICD pipeline "
                        "are used to run SageMaker pipeline(s) in dev and promote the pipeline definition to an "
                        "artefact bucket. The deploy repository and CICD pipeline loads the artefact SageMaker "
                        "pipeline definition to create a Sagemaker pipeline in preprod and production as "
                        "infrastructure as code (eg for batch inference). The target PREPROD/PROD accounts are "
                        "provided as cloudformation parameters and must be provided during project creation. "
                        "The PREPROD/PROD accounts need to be cdk bootstraped in advance to have the right "
                        "CloudFormation execution cross account roles.")

    TEMPLATE_NAME: str = "MLOps Batch Inference template to build and deploy SageMaker pipeline"

    TEMPLATE_VERSION: str = 'v1.0'

    SUPPORT_EMAIL: str = 'batch_inference_project@example.com'

    SUPPORT_URL: str = 'https://example.com/support/batch_inference_project'

    SUPPORT_DESCRIPTION: str = ('Example of support details for batch inference project'
                                )

    @classmethod
    def get_description(cls) -> str:
        return cls.DESCRIPTION

    @classmethod
    def get_support_email(cls) -> str:
        return cls.SUPPORT_EMAIL

    @classmethod
    def get_product_name(cls) -> str:
        return cls.TEMPLATE_NAME

    @classmethod
    def get_product_version(cls) -> str:
        return cls.TEMPLATE_VERSION

    @classmethod
    def get_support_url(cls) -> str:
        return cls.SUPPORT_URL

    @classmethod
    def get_support_description(cls) -> str:
        return cls.SUPPORT_DESCRIPTION

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            asset_bucket: s3.Bucket = None,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, asset_bucket=asset_bucket, **kwargs)

        # Define required parameters
        project_name = aws_cdk.CfnParameter(
            self,
            "SageMakerProjectName",
            type="String",
            description="The name of the SageMaker project.",
            min_length=1,
            max_length=32,
        ).value_as_string

        project_id = aws_cdk.CfnParameter(
            self,
            "SageMakerProjectId",
            type="String",
            min_length=1,
            max_length=16,
            description="Service generated Id of the project.",
        ).value_as_string

        preprod_account = aws_cdk.CfnParameter(
            self,
            "PreProdAccount",
            type="String",
            min_length=11,
            max_length=13,
            description="Id of preprod account.",
        ).value_as_string

        prod_account = aws_cdk.CfnParameter(
            self,
            "ProdAccount",
            type="String",
            min_length=11,
            max_length=13,
            description="Id of prod account.",
        ).value_as_string

        deployment_region = aws_cdk.CfnParameter(
            self,
            "DeploymentRegion",
            type="String",
            min_length=8,
            max_length=10,
            description="Deployment region for preprod and prod account.",
        ).value_as_string

        Tags.of(self).add("sagemaker:project-id", project_id)
        Tags.of(self).add("sagemaker:project-name", project_name)

        SSMConstruct(
            self,
            "MLOpsSSM",
            project_name=project_name,
            preprod_account=preprod_account,
            prod_account=prod_account,
            deployment_region=deployment_region,  # Modify when x-region is enabled
        )

        build_app_path: str = f"{BASE_DIR}/seed_code/build_app"
        build_app_repository = codecommit.Repository(
            self,
            "BuildRepo",
            repository_name=f"{project_name}-{construct_id}-build",
            code=codecommit.Code.from_zip_file(
                ZipUtility.create_zip(build_app_path),
                branch="main",
            ),
        )

        deploy_app_repository = codecommit.Repository(
            self,
            "DeployRepo",
            repository_name=f"{project_name}-{construct_id}-deploy",
            code=codecommit.Code.from_zip_file(
                ZipUtility.create_zip(f"{BASE_DIR}/seed_code/deploy_app"),
                branch="main",
            ),
        )

        seed_code_helper: SeedCodeHelper = SeedCodeHelper()
        has_docker_artifacts: bool = seed_code_helper.has_docker_artifacts(build_app_path)
        create_model_event_rule: bool = seed_code_helper.has_initial_modal_approval(build_app_path) is False

        Tags.of(deploy_app_repository).add(key="sagemaker:project-id", value=project_id)
        Tags.of(deploy_app_repository).add(
            key="sagemaker:project-name", value=project_name
        )

        # create kms key to be used by the assets bucket
        kms_key = kms.Key(
            self,
            "ArtifactsBucketKMSKey",
            description="key used for encryption of data in Amazon S3",
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

        # allow cross account access to the kms key
        kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                actions=[
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey",
                ],
                resources=[
                    "*",
                ],
                principals=[
                    iam.ArnPrincipal(f"arn:aws:iam::{preprod_account}:root"),
                    iam.ArnPrincipal(f"arn:aws:iam::{prod_account}:root"),
                ],
            )
        )

        s3_artifact = s3.Bucket(
            self,
            "S3Artifact",
            bucket_name=f"mlops-{project_name}-{Aws.ACCOUNT_ID}",  # Bucket name has a limit of 63 characters
            encryption_key=kms_key,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )

        # Block insecure requests to the bucket
        s3_artifact.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowSSLRequestsOnly",
                actions=["s3:*"],
                effect=iam.Effect.DENY,
                resources=[
                    s3_artifact.bucket_arn,
                    s3_artifact.arn_for_objects(key_pattern="*"),
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
                principals=[iam.AnyPrincipal()],
            )
        )

        # DEV account access to objects in the bucket
        s3_artifact.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AddDevPermissions",
                actions=["s3:*"],
                resources=[
                    s3_artifact.arn_for_objects(key_pattern="*"),
                    s3_artifact.bucket_arn,
                ],
                principals=[
                    iam.ArnPrincipal(f"arn:aws:iam::{Aws.ACCOUNT_ID}:root"),
                ],
            )
        )

        # PROD account access to objects in the bucket
        s3_artifact.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AddCrossAccountPermissions",
                actions=["s3:List*", "s3:Get*", "s3:Put*"],
                resources=[
                    s3_artifact.arn_for_objects(key_pattern="*"),
                    s3_artifact.bucket_arn,
                ],
                principals=[
                    iam.ArnPrincipal(f"arn:aws:iam::{preprod_account}:root"),
                    iam.ArnPrincipal(f"arn:aws:iam::{prod_account}:root"),
                ],
            )
        )

        model_package_group_name = f"{project_name}-{project_id}"

        # cross account model registry resource policy
        model_package_group_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    sid="ModelPackageGroup",
                    actions=[
                        "sagemaker:DescribeModelPackageGroup",
                    ],
                    resources=[
                        f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package-group/{model_package_group_name}"
                    ],
                    principals=[
                        iam.ArnPrincipal(f"arn:aws:iam::{preprod_account}:root"),
                        iam.ArnPrincipal(f"arn:aws:iam::{prod_account}:root"),
                    ],
                ),
                iam.PolicyStatement(
                    sid="ModelPackage",
                    actions=[
                        "sagemaker:DescribeModelPackage",
                        "sagemaker:ListModelPackages",
                        "sagemaker:UpdateModelPackage",
                        "sagemaker:CreateModel",
                    ],
                    resources=[
                        f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/{model_package_group_name}/*"
                    ],
                    principals=[
                        iam.ArnPrincipal(f"arn:aws:iam::{preprod_account}:root"),
                        iam.ArnPrincipal(f"arn:aws:iam::{prod_account}:root"),
                    ],
                ),
            ]
        ).to_json()

        model_package_group = sagemaker.CfnModelPackageGroup(
            self,
            "ModelPackageGroup",
            model_package_group_name=model_package_group_name,
            model_package_group_description=f"Model Package Group for {project_name}",
            model_package_group_policy=model_package_group_policy,
            tags=[
                aws_cdk.CfnTag(key="sagemaker:project-id", value=project_id),
                aws_cdk.CfnTag(key="sagemaker:project-name", value=project_name),
            ],
        )

        ml_models_ecr_repo_name: Optional[str] = None
        ml_models_ecr_repo_arn: Optional[Any] = None
        if has_docker_artifacts:
            # create ECR repository
            ml_models_ecr_repo = ecr.Repository(
                self,
                "MLModelsECRRepository",
                image_scan_on_push=True,
                image_tag_mutability=ecr.TagMutability.MUTABLE,
                repository_name=f"{project_name}",
            )

            # add cross account resource policies
            ml_models_ecr_repo.add_to_resource_policy(
                iam.PolicyStatement(
                    actions=[
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:BatchGetImage",
                        "ecr:CompleteLayerUpload",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:InitiateLayerUpload",
                        "ecr:PutImage",
                        "ecr:UploadLayerPart",
                    ],
                    principals=[
                        iam.ArnPrincipal(f"arn:aws:iam::{Aws.ACCOUNT_ID}:root"),
                    ],
                )
            )

            ml_models_ecr_repo.add_to_resource_policy(
                iam.PolicyStatement(
                    actions=[
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer",
                    ],
                    principals=[
                        iam.ArnPrincipal(f"arn:aws:iam::{preprod_account}:root"),
                        iam.ArnPrincipal(f"arn:aws:iam::{prod_account}:root"),
                    ],
                )
            )
            ml_models_ecr_repo_name = ml_models_ecr_repo.repository_name
            ml_models_ecr_repo_arn = ml_models_ecr_repo.repository_arn

        kms_key = kms.Key(
            self,
            "PipelineBucketKMSKey",
            description="key used for encryption of data in Amazon S3",
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

        pipeline_artifact_bucket = s3.Bucket(
            self,
            "PipelineBucket",
            bucket_name=f"pipeline-{project_name}-{Aws.ACCOUNT_ID}",  # Bucket name has a limit of 63 characters
            encryption_key=kms_key,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )

        BuildPipelineConstruct(
            self,
            "build",
            project_name=project_name,
            project_id=project_id,
            pipeline_artifact_bucket=pipeline_artifact_bucket,
            model_package_group_name=model_package_group_name,
            repository=build_app_repository,
            s3_artifact=s3_artifact,
            ecr_repository_name=ml_models_ecr_repo_name,
        )

        DeployPipelineConstruct(
            self,
            "deploy",
            project_name=project_name,
            project_id=project_id,
            pipeline_artifact_bucket=pipeline_artifact_bucket,
            model_package_group_name=model_package_group_name,
            repository=deploy_app_repository,
            s3_artifact=s3_artifact,
            preprod_account=preprod_account,
            prod_account=prod_account,
            ecr_repo_arn=ml_models_ecr_repo_arn,
            deployment_region=deployment_region,
            create_model_event_rule=create_model_event_rule,
        )
