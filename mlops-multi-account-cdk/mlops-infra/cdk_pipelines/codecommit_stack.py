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
from typing import List

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_codecommit as codecommit,
)
from constructs import Construct

import cdk_utilities
from mlops_commons.utilities.cdk_app_config import (
    PipelineConfig,
    CodeCommitConfig
)
from mlops_commons.utilities.zip_utils import ZipUtility
from mlops_commons.utilities.config_helper import ConfigHelper


class CdkPipelineCodeCommitStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, set_name: str, conf: CodeCommitConfig, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        source_code_dirs: List[str] = list()
        base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')
        source_code_dirs.append(base_dir)
        if os.path.exists(cdk_utilities.mlops_commons_base_dir):
            source_code_dirs.append(cdk_utilities.mlops_commons_base_dir)

        config_helper: ConfigHelper = ConfigHelper()

        self.repo = codecommit.Repository(
            self,
            "MLOpsInfraPipelineCodeRepo",
            repository_name=f'{conf.repo_name}_{set_name}',
            description="CDK Code with MLOps Infra project",
            code=codecommit.Code.from_zip_file(file_path=ZipUtility.create_zip_using_payload(
                source_code_dirs,
                out_file_suffix=set_name,
                file_key=f'/config/{config_helper.CONFIG_YAML_FILE_NAME}',
                file_key_payload=config_helper.create_set_name_specific_config_as_str(
                    set_name=set_name
                )),
                branch=conf.branch_name
            )
        )

    @classmethod
    def get_repo(cls, scope, set_name: str, pipeline_conf: PipelineConfig) -> codecommit.Repository:
        return cls.get_instance(scope, set_name, pipeline_conf).repo

    @classmethod
    def get_instance(cls, scope, set_name: str, pipeline_conf: PipelineConfig) -> 'CdkPipelineCodeCommitStack':
        return CdkPipelineCodeCommitStack(
            scope,
            f'ml-infra-cc-repo-{set_name}',
            set_name=set_name,
            conf=pipeline_conf.code_commit.infra,
            description='CDK stack for creating MLOps Infra pipeline codecommit repository',
            env=cdk.Environment(account=str(pipeline_conf.account), region=pipeline_conf.region)
        )
