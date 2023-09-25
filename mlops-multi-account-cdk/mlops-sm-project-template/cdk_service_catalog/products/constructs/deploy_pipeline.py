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

import typing

import aws_cdk as cdk
from aws_cdk import Aws, CfnCapabilities
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct
from typing import Optional


class DeployPipelineConstruct(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            project_name: str,
            project_id: str,
            pipeline_artifact_bucket: s3.Bucket,
            model_package_group_name: str,
            repository: codecommit.Repository,
            s3_artifact: s3.IBucket,
            preprod_account: str,
            prod_account: str,
            deployment_region: str,
            create_model_event_rule: bool,
            ecr_repo_arn: Optional[str] = None,
            model_bucket_arn: Optional[str] = None,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define resource names
        pipeline_name = f"{project_name}-{construct_id}"
        build_image = codebuild.LinuxBuildImage.STANDARD_7_0

        cdk_synth_build_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/service-role/",
        )

        cdk_synth_build_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sagemaker:ListModelPackages"],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package-group/*",
                    # TODO: Add conditions
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-package/*",
                    # TODO: Add conditions
                ],
            )
        )

        cdk_synth_build_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:{Aws.PARTITION}:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/*",
                ],
            )
        )

        cdk_synth_build_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:Decrypt",
                    "kms:DescribeKey",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:key/*"],
            ),
        )

        cdk_synth_build_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/mlops/*",  # TODO: Add conditions
                ],
            ),
        )

        cdk_synth_build_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:AbortMultipartUpload",
                    "s3:DeleteObject",
                    "s3:GetBucket*",
                    "s3:GetObject*",
                    "s3:List*",
                    "s3:PutObject*",
                    "s3:Create*",
                ],
                resources=[
                    s3_artifact.bucket_arn,
                    f"{s3_artifact.bucket_arn}/*",
                    "arn:aws:s3:::sagemaker-*",
                ],
            )
        )

        environment_variables = dict()

        environment_variables.update({
            "MODEL_PACKAGE_GROUP_NAME": codebuild.BuildEnvironmentVariable(
                value=model_package_group_name
            )
        })
        environment_variables.update({
            "PROJECT_ID": codebuild.BuildEnvironmentVariable(value=project_id)
        })
        environment_variables.update({
            "PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                value=project_name
            )
        })

        if ecr_repo_arn and model_bucket_arn:
            environment_variables.update({
                "ECR_REPO_ARN": codebuild.BuildEnvironmentVariable(value=ecr_repo_arn)
            })
            environment_variables.update({
                "MODEL_BUCKET_ARN": codebuild.BuildEnvironmentVariable(value=model_bucket_arn)
            })

        cdk_synth_build = codebuild.PipelineProject(
            self,
            "CDKSynthBuild",
            role=cdk_synth_build_role,
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=build_image,
                environment_variables=environment_variables,
            ),
        )

        # code build to include security scan over cloudformation template
        security_scan = codebuild.Project(
            self,
            "SecurityScanTooling",
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": 0.2,
                    "env": {
                        "shell": "bash",
                        "variables": {
                            "TemplateFolder": "./*.template.json",
                            "FAIL_BUILD": "true",
                        },
                    },
                    "phases": {
                        "install": {
                            "runtime-versions": {"ruby": 3.2},
                            "commands": [
                                "export date=`date +%Y-%m-%dT%H:%M:%S.%NZ`",
                                "echo Installing cfn_nag - `pwd`",
                                "gem install cfn-nag",
                                "echo cfn_nag installation complete `date`",
                            ],
                        },
                        "build": {
                            "commands": [
                                "echo Starting cfn scanning `date` in `pwd`",
                                "echo 'RulesToSuppress:\n- id: W58\n  reason: W58 is an warning raised due to Lambda functions require permission to write CloudWatch Logs, although the lambda role contains the policy that support these permissions cgn_nag continues to through this problem (https://github.com/stelligent/cfn_nag/issues/422)' > cfn_nag_ignore.yml",
                                # this is temporary solution to an issue with W58 rule with cfn_nag
                                'mkdir report || echo "dir report exists"',
                                "SCAN_RESULT=$(cfn_nag_scan --fail-on-warnings --deny-list-path cfn_nag_ignore.yml --input-path  ${TemplateFolder} -o json > ./report/cfn_nag.out.json && echo OK || echo FAILED)",
                                "echo Completed cfn scanning `date`",
                                "echo $SCAN_RESULT",
                                "echo $FAIL_BUILD",
                                """if [[ "$FAIL_BUILD" = "true" && "$SCAN_RESULT" = "FAILED" ]]; then printf "\n\nFailiing pipeline as possible insecure configurations were detected\n\n" && exit 1; fi""",
                            ]
                        },
                    },
                    "artifacts": {"files": "./report/cfn_nag.out.json"},
                }
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image)
        )

        source_artifact = codepipeline.Artifact(artifact_name="GitSource")
        cdk_synth_artifact = codepipeline.Artifact(artifact_name="CDKSynth")
        cfn_nag_artifact = codepipeline.Artifact(artifact_name="CfnNagScanReport")

        deploy_code_pipeline = codepipeline.Pipeline(
            self,
            "DeployPipeline",
            cross_account_keys=True,
            pipeline_name=pipeline_name,
            artifact_bucket=pipeline_artifact_bucket,
        )

        # add a source stage
        source_stage = deploy_code_pipeline.add_stage(stage_name="Source")
        source_stage.add_action(
            codepipeline_actions.CodeCommitSourceAction(
                action_name="Source",
                output=source_artifact,
                repository=repository,
                branch="main",
            )
        )

        # add a build stage
        build_stage = deploy_code_pipeline.add_stage(stage_name="Build")

        build_stage.add_action(
            codepipeline_actions.CodeBuildAction(
                action_name="Synth",
                input=source_artifact,
                outputs=[cdk_synth_artifact],
                project=cdk_synth_build,
            )
        )

        # add a security evaluation stage for cloudformation templates
        security_stage = deploy_code_pipeline.add_stage(stage_name="SecurityEvaluation")

        security_stage.add_action(
            codepipeline_actions.CodeBuildAction(
                action_name="CFNNag",
                input=cdk_synth_artifact,
                outputs=[cfn_nag_artifact],
                project=security_scan,
            )
        )

        # add stages to deploy to the different environments
        for stage, account, region in [
            ('Dev', Aws.ACCOUNT_ID, cdk.Aws.REGION),
            ('PreProd', preprod_account, deployment_region),
            ('Prod', prod_account, deployment_region)
        ]:

            actions: typing.Optional[typing.List[codepipeline.IAction]] = list()

            actions.append(
                codepipeline_actions.CloudFormationCreateUpdateStackAction(
                    action_name=f"Deploy_CFN_{stage}",
                    run_order=1,
                    template_path=cdk_synth_artifact.at_path(f"{stage.lower()}.template.json"),
                    stack_name=f"{project_name}-{construct_id}-{stage.lower()}",
                    admin_permissions=False,
                    replace_on_failure=True,
                    role=iam.Role.from_role_arn(
                        self,
                        f"{stage}ActionRole",
                        f"arn:{Aws.PARTITION}:iam::{account}:"
                        f"role/cdk-{cdk.DefaultStackSynthesizer.DEFAULT_QUALIFIER}-"
                        f"deploy-role-{account}-{region}",
                        mutable=False,
                    ),
                    deployment_role=iam.Role.from_role_arn(
                        self,
                        f"{stage}DeploymentRole",
                        f"arn:{Aws.PARTITION}:iam::{account}:"
                        f"role/cdk-{cdk.DefaultStackSynthesizer.DEFAULT_QUALIFIER}-"
                        f"cfn-exec-role-{account}-{region}",
                        mutable=False,
                    ),
                    cfn_capabilities=[
                        CfnCapabilities.AUTO_EXPAND,
                        CfnCapabilities.NAMED_IAM,
                    ],
                )
            )

            if stage in ['Dev', 'PreProd']:
                approved_stage: str = 'PreProd' if stage == 'Dev' else 'Prod'
                actions.append(
                    codepipeline_actions.ManualApprovalAction(
                        action_name=f"Approve_{approved_stage}",
                        run_order=2,
                        additional_information=f"Approving deployment for {approved_stage}",
                    )
                )

            # add stage to deploy
            deploy_code_pipeline.add_stage(
                stage_name=f"Deploy{stage}",
                actions=actions,
            )

        if create_model_event_rule:
            # CloudWatch rule to trigger model pipeline when a status change event
            # happens to the model package group
            model_event_rule = events.Rule(
                self,
                "ModelEventRule",
                event_pattern=events.EventPattern(
                    source=["aws.sagemaker"],
                    detail_type=["SageMaker Model Package State Change"],
                    detail={
                        "ModelPackageGroupName": [model_package_group_name],
                        "ModelApprovalStatus": ["Approved", "Rejected"],
                    },
                ),
                targets=[targets.CodePipeline(deploy_code_pipeline)],
            )
        else:
            # CloudWatch rule to trigger the deploy CodePipeline when the build
            # CodePipeline has succeeded
            codepipeline_event_rule = events.Rule(
                self,
                "BuildCodePipelineEventRule",
                event_pattern=events.EventPattern(
                    source=["aws.codepipeline"],
                    detail_type=["CodePipeline Pipeline Execution State Change"],
                    detail={
                        "pipeline": [f"{project_name}-build"],
                        "state": ["SUCCEEDED"],
                    },
                ),
                targets=[targets.CodePipeline(deploy_code_pipeline)],
            )
