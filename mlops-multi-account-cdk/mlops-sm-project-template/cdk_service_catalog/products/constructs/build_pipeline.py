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
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_s3 as s3,
    aws_iam as iam,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
)
from typing import Optional
from constructs import Construct


class BuildPipelineConstruct(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            project_name: str,
            project_id: str,
            s3_artifact: s3.IBucket,
            pipeline_artifact_bucket: s3.IBucket,
            model_package_group_name: str,
            repository: codecommit.Repository,
            ecr_repository_name: Optional[str] = None,
            **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define resource names
        pipeline_name = f"{project_name}-{construct_id}"
        pipeline_description = f"{project_name} Model Build Pipeline"
        build_image = codebuild.LinuxBuildImage.STANDARD_7_0

        codebuild_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/service-role/",
        )

        sagemaker_execution_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            path="/service-role/",
        )

        # Create a policy statement for SM and ECR pull
        sagemaker_policy = iam.Policy(
            self,
            "SageMakerPolicy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=["sagemaker:*"],
                        not_resources=[
                            "arn:aws:sagemaker:*:*:domain/*",
                            "arn:aws:sagemaker:*:*:user-profile/*",
                            "arn:aws:sagemaker:*:*:app/*",
                            "arn:aws:sagemaker:*:*:flow-definition/*",
                        ],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:Describe*",
                            "ecr:GetAuthorizationToken",
                            "ecr:GetDownloadUrlForLayer",
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "cloudwatch:PutMetricData",
                        ],
                        resources=["*"],
                    ),
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
                    ),
                    iam.PolicyStatement(
                        actions=["iam:PassRole"],
                        resources=[sagemaker_execution_role.role_arn],
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
                        resources=[f"arn:aws:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:key/*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "ssm:PutParameter",
                            "ssm:GetParameters",
                            "ssm:GetParameter",
                            "ssm:GetParametersByPath",
                        ],
                        resources=[f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/*"],
                    ),
                ]
            ),
        )

        sagemaker_policy.attach_to_role(sagemaker_execution_role)
        sagemaker_policy.attach_to_role(codebuild_role)

        environment_variables = dict()

        environment_variables.update({
            "SAGEMAKER_PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                value=project_name
            )
        })
        environment_variables.update({
            "SAGEMAKER_PROJECT_ID": codebuild.BuildEnvironmentVariable(
                value=project_id
            )
        })
        environment_variables.update({
            "MODEL_PACKAGE_GROUP_NAME": codebuild.BuildEnvironmentVariable(
                value=model_package_group_name
            )
        })
        environment_variables.update({
            "AWS_REGION": codebuild.BuildEnvironmentVariable(value=Aws.REGION)
        })
        environment_variables.update({
            "SAGEMAKER_PIPELINE_NAME": codebuild.BuildEnvironmentVariable(
                value=pipeline_name,
            )
        })
        environment_variables.update({
            "SAGEMAKER_PIPELINE_DESCRIPTION": codebuild.BuildEnvironmentVariable(
                value=pipeline_description,
            )
        })
        environment_variables.update({
            "SAGEMAKER_PIPELINE_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                value=sagemaker_execution_role.role_arn,
            )
        })
        environment_variables.update({
            "ARTIFACT_BUCKET": codebuild.BuildEnvironmentVariable(value=s3_artifact.bucket_name)
        })
        environment_variables.update({
            "ARTIFACT_BUCKET_KMS_ID": codebuild.BuildEnvironmentVariable(
                value=s3_artifact.encryption_key.key_id
            )
        })

        if ecr_repository_name:
            environment_variables.update({
                "ECR_REPO_URI": codebuild.BuildEnvironmentVariable(
                    value=f"{Aws.ACCOUNT_ID}.dkr.ecr.{Aws.REGION}.amazonaws.com/{ecr_repository_name}"
                )
            })

        sm_pipeline_build = codebuild.PipelineProject(
            self,
            "SMPipelineBuild",
            project_name=f"{project_name}-{construct_id}",
            role=codebuild_role,  # figure out what actually this role would need
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            environment=codebuild.BuildEnvironment(build_image=build_image, environment_variables=environment_variables)
        )

        source_artifact = codepipeline.Artifact(artifact_name="GitSource")

        build_pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            pipeline_name=pipeline_name,
            artifact_bucket=pipeline_artifact_bucket,
        )

        # add a source stage
        source_stage = build_pipeline.add_stage(stage_name="Source")
        source_stage.add_action(
            codepipeline_actions.CodeCommitSourceAction(
                action_name="Source",
                output=source_artifact,
                repository=repository,
                branch="main",
            )
        )

        run_order = 1
        # add a build stage
        build_stage = build_pipeline.add_stage(stage_name="Build")

        if ecr_repository_name:
            # code build to include security scan over cloudformation template
            docker_build = codebuild.Project(
                self,
                "DockerBuild",
                build_spec=codebuild.BuildSpec.from_object(
                    {
                        "version": 0.2,
                        "phases": {
                            "build": {
                                "commands": [
                                    "cd source_scripts",
                                    "chmod +x docker-build.sh",
                                    f"./docker-build.sh {ecr_repository_name}",
                                ]
                            },
                        },
                    }
                ),
                environment=codebuild.BuildEnvironment(build_image=build_image, privileged=True)
            )

            docker_build.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["ecr:*"],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:ecr:{Aws.REGION}:{Aws.ACCOUNT_ID}:repository/{ecr_repository_name}"],
                )
            )

            docker_build.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["ecr:Get*"],
                    effect=iam.Effect.ALLOW,
                    resources=["*"],
                )
            )

            build_stage.add_action(
                codepipeline_actions.CodeBuildAction(
                    action_name="DockerBuild", input=source_artifact, project=docker_build, run_order=run_order
                )
            )

            run_order = run_order + 1

        build_stage.add_action(
            codepipeline_actions.CodeBuildAction(
                action_name="SMPipeline",
                input=source_artifact,
                project=sm_pipeline_build,
                run_order=run_order,
            )
        )
