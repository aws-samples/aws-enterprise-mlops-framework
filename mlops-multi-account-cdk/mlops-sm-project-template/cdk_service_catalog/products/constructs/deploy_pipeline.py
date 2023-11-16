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
import typing
from logging import Logger

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

from cdk_utilities.yaml_helper import YamlHelper

from mlops_commons.utilities.log_helper import LogHelper


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
            caller_base_dir: Optional[str],
            ecr_repo_arn: Optional[str] = None,

    ) -> None:
        super().__init__(scope, construct_id)
        self.logger: Logger = LogHelper.get_logger(self)
        base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}')

        # Define resource names
        pipeline_name = f"{project_name}-{construct_id}"
        build_image = codebuild.LinuxBuildImage.STANDARD_7_0

        model_bucket_arn = s3_artifact.bucket_arn

        cdk_synth_build_role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/service-role/",
        )

        cdk_synth_build_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sagemaker:ListModelPackages", "sagemaker:DescribeModelPackage"],
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

        environment_variables.update({
            "MODEL_BUCKET_ARN": codebuild.BuildEnvironmentVariable(value=model_bucket_arn)
        })

        environment_variables.update({
            "ARTIFACT_BUCKET": codebuild.BuildEnvironmentVariable(value=s3_artifact.bucket_name)
        })
        environment_variables.update({
            "ARTIFACT_BUCKET_KMS_ID": codebuild.BuildEnvironmentVariable(
                value=s3_artifact.encryption_key.key_id
            )
        })

        if ecr_repo_arn:
            environment_variables.update({
                "ECR_REPO_ARN": codebuild.BuildEnvironmentVariable(value=ecr_repo_arn)
            })

        default_deploy_build_spec_env_name: str = 'default_deploy_build_spec'

        build_spec_python_fn = self.create_python_fn_deploy_build_spec_update(
            default_build_spec_env_name=default_deploy_build_spec_env_name,
            product_specific_build_spec_filepath='./buildspec.yml',  # this file will be in Cfn Prepare Synth action
            command='if [ -f ./config/cfn_nag_ignore.yml ]; then cp ./config/cfn_nag_ignore.yml ./cdk.out/ ; fi'
        )

        self.logger.info(f'build_spec_python_fn -> {build_spec_python_fn}')

        default_deploy_build_spec_yml_b64: str = YamlHelper.encode_file_as_base64_string(
            f'{base_dir}{os.path.sep}conf{os.path.sep}default_deploy_buildspec.yml'
        )

        cdk_prepare_synth_build = codebuild.PipelineProject(
            self,
            "CDKPrepareSynthBuild",
            role=cdk_synth_build_role,
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": 0.2,
                    "env": {
                        "shell": "bash",
                        "variables": {
                            f"{default_deploy_build_spec_env_name}": f'{default_deploy_build_spec_yml_b64}'
                        },
                    },
                    "phases": {
                        "install": {
                            "runtime-versions": {"python": 3.11},
                        },
                        "build": {
                            "commands": [
                                f"python -c '{build_spec_python_fn}'",
                            ]
                        },
                    },
                    "artifacts": {
                        "base-directory": ".",
                        "files": "**/*"
                    },
                }
            ),
            environment=codebuild.BuildEnvironment(
                build_image=build_image,
                environment_variables=environment_variables,
            ),
        )

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

        mandatory_cfn_nag_ignore_env_name: str = 'mandatory_cfn_nag_ignore'
        merged_cfn_nag_file_name: str = 'merged_cfn_nag_ignore.yml'

        cfn_nag_ignore_python_fn = self.create_python_fn_cfn_nag_yaml_merge(
            mandatory_nag_env_name=mandatory_cfn_nag_ignore_env_name,
            product_specific_cfn_nag_filepath='./cfn_nag_ignore.yml',  # this file will be in Cfn nag codepipeline stage
            out_file_name=merged_cfn_nag_file_name
        )

        self.logger.info(f'cfn_nag_ignore_python_fn -> {cfn_nag_ignore_python_fn}')

        cfn_nag_mandatory_yml_b64: str = YamlHelper.encode_file_as_base64_string(
            f'{base_dir}{os.path.sep}conf{os.path.sep}cfn_nag_ignore.yml'
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
                            f"{mandatory_cfn_nag_ignore_env_name}": f'{cfn_nag_mandatory_yml_b64}'
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
                                f"python -c '{cfn_nag_ignore_python_fn}'",
                                'mkdir report || echo "dir report exists"',
                                'ls -lrt',
                                f"SCAN_RESULT=$(cfn_nag_scan --fail-on-warnings "
                                f"--deny-list-path {merged_cfn_nag_file_name} "
                                "--input-path  ${TemplateFolder} -o json > ./report/cfn_nag.out.json && echo OK || "
                                "echo FAILED)",
                                "cat ./report/cfn_nag.out.json",
                                "echo Completed cfn scanning `date`",
                                "echo $SCAN_RESULT",
                                "echo $FAIL_BUILD",
                                """if [[ "$FAIL_BUILD" = "true" && "$SCAN_RESULT" = "FAILED" ]]; 
                                then printf "\n\nFailiing pipeline as possible insecure configurations 
                                were detected\n\n" && exit 1; fi""",
                            ]
                        },
                    },
                    "artifacts": {"files": "./report/cfn_nag.out.json"},
                }
            ),
            environment=codebuild.BuildEnvironment(build_image=build_image)
        )

        source_artifact = codepipeline.Artifact(artifact_name="GitSource")
        cdk_prepare_synth_artifact = codepipeline.Artifact(artifact_name="CDKPrepareSynth")
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
                run_order=1,
                action_name="Prepare_Synth",
                input=source_artifact,
                outputs=[cdk_prepare_synth_artifact],
                project=cdk_prepare_synth_build,
            )
        )

        build_stage.add_action(
            codepipeline_actions.CodeBuildAction(
                run_order=2,
                action_name="Synth",
                input=cdk_prepare_synth_artifact,
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

    def create_python_fn_cfn_nag_yaml_merge(self, mandatory_nag_env_name: str,
                                            product_specific_cfn_nag_filepath: str, out_file_name: str) -> str:

        self.logger.info(f'mandatory_nag_env_name: {mandatory_nag_env_name}, '
                         f'product_specific_cfn_nag_filepath: {product_specific_cfn_nag_filepath}, '
                         f'out_file_name: {out_file_name} ')

        cfn_nag_ignore_python_fn: str = f'yaml_file_path="{product_specific_cfn_nag_filepath}";' \
                                        f'import os;' \
                                        f'import yaml;' \
                                        f'from base64 import b64decode;' \
                                        f'm_yml_str=b64decode(os.getenv("{mandatory_nag_env_name}")).decode("utf-8");' \
                                        f'm_yml = yaml.safe_load(m_yml_str); ' \
                                        f'os.path.exists(yaml_file_path) and ' \
                                        f'[m_yml["RulesToSuppress"].append(e) ' \
                                        f'for e in yaml.safe_load(open(yaml_file_path, "r"))["RulesToSuppress"]];  ' \
                                        f'yaml.dump(m_yml, open("{out_file_name}", "w"), ' \
                                        f'default_flow_style=False)'
        return cfn_nag_ignore_python_fn

    def create_python_fn_deploy_build_spec_update(self, default_build_spec_env_name: str,
                                                  product_specific_build_spec_filepath: str, command: str) -> str:

        self.logger.info(f'default_buildspec_env_name: {default_build_spec_env_name}, '
                         f'product_specific_buildspec_filepath: {product_specific_build_spec_filepath}, '
                         f'command : {command}')

        build_spec_python_fn: str = f'command="{command}";' \
                                    f'bs_yml="{product_specific_build_spec_filepath}";' \
                                    f'import os;' \
                                    f'import yaml;' \
                                    f'from base64 import b64decode;' \
                                    f'm_yml_str=b64decode(os.getenv("{default_build_spec_env_name}")).decode("utf-8");' \
                                    f'm_yml = yaml.safe_load(m_yml_str); ' \
                                    f'os.path.exists(bs_yml) is False and ' \
                                    f'yaml.dump(m_yml, open(bs_yml, "w"), default_flow_style=False, sort_keys=False); ' \
                                    f'bs=yaml.safe_load(open(bs_yml, 'r')); ' \
                                    r'print(bs); ' \
                                    r'phases = bs.get("phases", None); ' \
                                    r'phases is None and bs.update({"phases": {}}); ' \
                                    r'phases = bs.get("phases", None); ' \
                                    r'post_build=phases.get("post_build", None); ' \
                                    r'post_build is None and phases.update({"post_build": {}}); ' \
                                    r'post_build=phases.get("post_build", None);  ' \
                                    r'commands=post_build.get("commands", None); ' \
                                    r'commands is None and post_build.update({"commands":[]});  ' \
                                    r'commands=post_build.get("commands", None); ' \
                                    r'commands.append(command); ' \
                                    r'yaml.dump(bs, open(bs_yml, "w"), default_flow_style=False, sort_keys=False);'
        return build_spec_python_fn
