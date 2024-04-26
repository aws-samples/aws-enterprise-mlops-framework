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
import logging
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

from mlops_sm_project_template.cdk_helper_scripts import seed_code_helper
from constructs import Construct

from mlops_sm_project_template.templates.constructs.build_pipeline import BuildPipelineConstruct
from mlops_sm_project_template.templates.constructs.deploy_pipeline import DeployPipelineConstruct
from mlops_sm_project_template.templates.constructs.ssm import SSMConstruct

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


class MLOpsStack(sc.ProductStack):
    DESCRIPTION: str = ("This template includes a model building pipeline that includes a workflow to pre-process, "
                        "train, evaluate and register a model. The deploy pipeline creates a dev,preprod and "
                        "production endpoint. The target DEV/PREPROD/PROD accounts are parameterized in this template."
                        )
    TEMPLATE_NAME: str = ("Build & Deploy MLOps parameterized "
                          "template for Generative AI CV"
                          )

    TEMPLATE_VERSION: str = 'v1.0'

    SUPPORT_EMAIL: str = 'genai_cv_project@example.com'

    SUPPORT_URL: str = 'https://example.com/support/genai_cv_project'

    SUPPORT_DESCRIPTION: str = ('Example of support details for genai cv project'
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
            app_prefix: str,
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
            min_length=12,
            max_length=12,
            description="Id of preprod account.",
        ).value_as_string

        prod_account = aws_cdk.CfnParameter(
            self,
            "ProdAccount",
            type="String",
            min_length=12,
            max_length=12,
            description="Id of prod account.",
        ).value_as_string

        deployment_region = aws_cdk.CfnParameter(
            self,
            "DeploymentRegion",
            type="String",
            min_length=9,
            max_length=14,
            description="Deployment region for preprod and prod account.",
        ).value_as_string

        Tags.of(self).add("sagemaker:project-id", project_id)
        Tags.of(self).add("sagemaker:project-name", project_name)
        Tags.of(self).add("sagemaker:app-prefix", app_prefix)

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
            code=codecommit.Code.from_directory(
                directory_path=build_app_path,
                branch="main",
            ),
        )

        deploy_app_path: str = f"{BASE_DIR}/seed_code/deploy_app"
        deploy_app_repository = codecommit.Repository(
            self,
            "DeployRepo",
            repository_name=f"{project_name}-{construct_id}-deploy",
            code=codecommit.Code.from_directory(
                directory_path=deploy_app_path,
                branch="main",
            ),
        )

        has_docker_artifacts = seed_code_helper.has_docker_artifacts(build_app_path)
        create_model_event_rule = seed_code_helper.has_initial_model_approval(build_app_path) is False

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

        artifact_bucket_name = f"mlops-{project_name}-{Aws.ACCOUNT_ID}"

        logging.info(f'Creating {artifact_bucket_name} artifact bucket')

        s3_artifact = s3.Bucket(
            self,
            "S3Artifact",
            bucket_name=artifact_bucket_name,  # Bucket name has a limit of 63 characters
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

        pipeline_bucket_name = f"pipeline-{project_name}-{Aws.ACCOUNT_ID}"

        logging.info(f'Creating {pipeline_bucket_name} pipeline bucket')
        pipeline_artifact_bucket = s3.Bucket(
            self,
            "PipelineBucket",
            bucket_name=pipeline_bucket_name,  # Bucket name has a limit of 63 characters
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
            caller_base_dir=BASE_DIR
        )
