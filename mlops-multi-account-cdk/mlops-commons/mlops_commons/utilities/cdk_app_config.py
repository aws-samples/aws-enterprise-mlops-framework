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
from dataclasses import dataclass, field
from typing import List, Optional

from dataclasses_json import DataClassJsonMixin
from yamldataclassconfig.config import YamlDataClassConfig


@dataclass
class BootstrapConfig(DataClassJsonMixin):
    enabled: bool = field(default=True)
    execution_policy_filepath: str = field(default='')
    execution_policy_arn: str = field(default='arn:aws:iam::aws:policy/AdministratorAccess')
    aws_profile: str = field(default='')


@dataclass
class DeploymentStage(DataClassJsonMixin):
    stage_name: str
    account: int
    enabled: bool = field(default=True)
    region: str = field(default='')
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)

    def get_bootstrap(self) -> BootstrapConfig:
        return BootstrapConfig(
            enabled=self.bootstrap.enabled,
            execution_policy_arn=self.bootstrap.execution_policy_arn,
            execution_policy_filepath=self.bootstrap.execution_policy_filepath
            if self.bootstrap.execution_policy_filepath else
            f'.{os.path.sep}config{os.path.sep}execution_policy_'
            f'{self.account}_{self.region}.json',
            aws_profile=self.bootstrap.aws_profile if self.bootstrap.aws_profile else
            f'cdk_{self.account}_{self.region}'
        )


@dataclass
class DeploymentConfig(DataClassJsonMixin):
    set_name: str
    enabled: bool = field(default=True)
    default_region: Optional[str] = field(default=os.getenv('CDK_DEFAULT_REGION'))
    stages: List[DeploymentStage] = field(default=None)

    def get_deployment_stages(self) -> List[DeploymentStage]:
        st: List[DeploymentStage] = list()
        for ds in self.stages:
            st.append(DeploymentStage(
                stage_name=ds.stage_name,
                account=ds.account,
                enabled=ds.enabled,
                region=self.default_region if ds.region is None or ds.region.strip() == '' else ds.region.strip(),
                bootstrap=ds.bootstrap
            ))
        return st

    def get_deployment_stage_by_name(self, name: str) -> DeploymentStage:
        return list(filter(lambda st: st.stage_name.lower() == name.lower(), self.get_deployment_stages())).pop()


@dataclass
class CodeCommitConfig(DataClassJsonMixin):
    repo_name: str
    branch_name: str


@dataclass
class CodeCommitRepo(DataClassJsonMixin):
    infra: CodeCommitConfig = field(default_factory=lambda: CodeCommitConfig('mlops-infra', 'main'))
    project_template: CodeCommitConfig = field(
        default_factory=lambda: CodeCommitConfig('mlops-sm-project-template', 'main')
    )


@dataclass
class PipelineConfig(DataClassJsonMixin):
    account: int = field(default=os.getenv('CDK_DEFAULT_ACCOUNT'))
    region: str = field(default=os.getenv('CDK_DEFAULT_REGION'))
    code_commit: CodeCommitRepo = field(default_factory=CodeCommitRepo)
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)

    def get_bootstrap(self) -> BootstrapConfig:
        return BootstrapConfig(
            enabled=self.bootstrap.enabled,
            execution_policy_arn=self.bootstrap.execution_policy_arn,
            execution_policy_filepath=self.bootstrap.execution_policy_filepath
            if self.bootstrap.execution_policy_filepath else
            f'.{os.path.sep}config{os.path.sep}execution_policy_'
            f'{self.account}_{self.region}.json',
            aws_profile=self.bootstrap.aws_profile if self.bootstrap.aws_profile else
            f'cdk_{self.account}_{self.region}'
        )


@dataclass
class CdkAppConfig(DataClassJsonMixin):
    app_prefix: str = field(default='mlops-cdk')
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    deployments: List[DeploymentConfig] = field(default=None)


@dataclass
class AppConfig(YamlDataClassConfig):
    cdk_app_config: CdkAppConfig = field(default=None)
