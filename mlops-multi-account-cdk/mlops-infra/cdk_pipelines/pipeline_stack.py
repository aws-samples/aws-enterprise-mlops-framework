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
from logging import Logger
from typing import List

import aws_cdk
import aws_cdk as cdk
from aws_cdk import (

    Stack,
    Stage,
    Tags,
    aws_codecommit as codecommit,
    pipelines as pipelines,
    aws_s3 as s3,
    aws_iam as iam,
    aws_kms as kms,
)
from constructs import Construct

from cdk_utilities.cdk_infra_app_config import InfraAppConfig
from mlops_commons.utilities.cdk_app_config import (
    DeploymentStage,
    PipelineConfig, CodeCommitConfig
)
from mlops_commons.utilities.log_helper import LogHelper
from cdk_sm_infra.sm_infra_stack import SagemakerInfraStack


class SagemakerInfraStage(Stage):
    """
    MLOpsInfra Stage
    """

    def __init__(self, scope: Construct, construct_id: str, set_name: str, stage_name: str,
                 app_prefix: str, deploy_sm_domain=False, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.logger: Logger = LogHelper.get_logger(self)

        base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')
        conf: InfraAppConfig = InfraAppConfig()

        config_filepath: str = os.path.join(base_dir, 'config', 'cdk-infra-app.yml')
        if os.path.exists(config_filepath):
            conf.load(config_filepath)
        else:
            self.logger.info(f'cdk infra app specific configuration not found at : {config_filepath}, '
                             f'using default configuration')
        self.logger.debug(f'cdk-infra-app config : {str(conf.cdk_infra_app_config)}')

        SagemakerInfraStack(
            self,
            f'mlops-infra',
            app_prefix=app_prefix,
            set_name=set_name,
            network_conf=conf.cdk_infra_app_config.network.get_network_stage_config_by(
                set_name=set_name,
                stage_name=stage_name
            ),
            sagemaker_conf=conf.cdk_infra_app_config.sagemaker,
            deploy_sm_domain=deploy_sm_domain,
            **kwargs
        )


class CdkPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, set_name: str,
                 app_prefix: str, deploy_stages_conf: List[DeploymentStage],
                 pipeline_conf: PipelineConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.logger: Logger = LogHelper.get_logger(self)

        code_commit_conf: CodeCommitConfig = pipeline_conf.code_commit.infra
        repo: codecommit.IRepository = codecommit.Repository.from_repository_name(
            self, "ProjectTemplateRepo", repository_name=code_commit_conf.repo_name
        )

        artifact_bucket = self.create_pipeline_artifact_bucket(app_prefix=app_prefix, set_name=set_name)

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            pipeline_name=f"{app_prefix}-infra-{code_commit_conf.branch_name}-{set_name}",
            docker_enabled_for_synth=True,
            docker_enabled_for_self_mutation=True,
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.code_commit(repo, code_commit_conf.branch_name),
                install_commands=[
                    "npm install -g aws-cdk@2.100.0",
                    "pip install -r requirements.txt",
                ],
                commands=[
                    f"cdk synth --no-lookup",
                ],
            ),
            cross_account_keys=True,
            self_mutation=True,
            artifact_bucket=artifact_bucket,

        )
        for stage in sorted(deploy_stages_conf,
                            key=lambda x: {'dev': 0, 'preprod': 1, 'prod': 2}.get(x.stage_name, 3)):

            if not stage.enabled:
                self.logger.info(f'Skipping deployment of config ->'
                                 f'set name : {set_name}, '
                                 f'stage name : {stage.stage_name}, '
                                 f'account : {stage.account}, '
                                 f'region : {stage.region}, '
                                 f' as it is disabled in configuration file. To enable it, set the attribute '
                                 f'enabled=True at deployments level in yaml configuration file ')
                continue

            pipeline.add_stage(
                SagemakerInfraStage(
                    self,
                    stage.stage_name,
                    set_name=set_name,
                    stage_name=stage.stage_name,
                    app_prefix=app_prefix,
                    env=aws_cdk.Environment(account=str(stage.account), region=stage.region),
                    deploy_sm_domain=str(stage.stage_name).lower().strip().startswith('dev')
                )
            )

        # General tags applied to all resources created on this scope (self)
        Tags.of(self).add("cdk-app", f"{app_prefix}-infra")

    def create_pipeline_artifact_bucket(self, app_prefix: str, set_name: str) -> s3.Bucket:
        # create kms key to be used by the assets bucket
        kms_key = kms.Key(
            self,
            "MLOpsPipelineArtifactsBucketKMSKey",
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
                    iam.ArnPrincipal(f"arn:aws:iam::{cdk.Aws.ACCOUNT_ID}:root"),
                ],
            )
        )

        s3_artifact = s3.Bucket(
            self,
            "MLOpsSmTemplatePipelineArtifactBucket",
            bucket_name=f"{app_prefix}-infra-pipeline-bucket-{set_name}",
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

        # Tooling account access to objects in the bucket
        s3_artifact.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AddToolingPermissions",
                actions=["s3:*"],
                resources=[
                    s3_artifact.arn_for_objects(key_pattern="*"),
                    s3_artifact.bucket_arn,
                ],
                principals=[
                    iam.ArnPrincipal(f"arn:aws:iam::{cdk.Aws.ACCOUNT_ID}:root"),
                ],
            )
        )

        return s3_artifact
