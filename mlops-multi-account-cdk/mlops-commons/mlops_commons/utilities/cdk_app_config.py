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
import re
from dataclasses import dataclass, field
from typing import List, Optional

from dataclasses_json import DataClassJsonMixin
from yamldataclassconfig.config import YamlDataClassConfig


class DataValidations:
    @staticmethod
    def account_id_validation(context: str, account: int | str) -> int | str:
        if isinstance(account, str):
            account = account.strip() if account else None

        _account = str(account)
        if account is None or len(_account) != 12 or _account.isnumeric() is False:
            raise ValueError(f'{context} '
                             f'Invalid account number \'{account}\' , AWS Account Id must be of 12 digit')
        return account

    @staticmethod
    def region_validation(context: str, region: str) -> str:
        regions: List[str] = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'af-south-1', 'ap-east-1',
                              'ap-south-2', 'ap-southeast-3', 'ap-southeast-4', 'ap-south-1',
                              'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
                              'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-south-1',
                              'eu-west-3', 'eu-south-2', 'eu-north-1', 'eu-central-2', 'il-central-1', 'me-south-1',
                              'me-central-1', 'sa-east-1', 'us-gov-east-1', 'us-gov-west-1']
        if region is None or region.strip().lower() not in regions:
            raise ValueError(f'{context} '
                             f'Invalid region \'{region}\' , AWS Region must be specified, '
                             f'Valid regions for \'{region.split("-")[0]}\' are : '
                             f'{list(filter(lambda r: r.startswith(region.split("-")[0]), regions))}')
        region = region.strip().lower()
        return region


@dataclass
class BootstrapConfig(DataClassJsonMixin):
    enabled: bool = field(default=True)
    execution_policy_filepath: str = field(default='')
    execution_policy_arn: str = field(default='arn:aws:iam::aws:policy/AdministratorAccess')
    aws_profile: str = field(default='')

    def __post_init__(self):
        self.execution_policy_filepath = self.execution_policy_filepath.strip()
        self.execution_policy_arn = self.execution_policy_arn.strip()
        self.aws_profile = self.aws_profile.strip()


@dataclass
class DeploymentStage(DataClassJsonMixin):
    stage_name: str
    account: int | str
    enabled: bool = field(default=True)
    region: str = field(default='')
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)

    def __post_init__(self):

        if self.stage_name:
            self.stage_name = self.stage_name.strip()

        if self.region:
            self.region = self.region.strip()

        if len(self.bootstrap.execution_policy_filepath.strip()) == 0:
            base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')
            self.bootstrap.execution_policy_filepath = f'{base_dir}{os.path.sep}config{os.path.sep}execution_policy_' \
                                                       f'{self.account}_{self.region}.json'

        if len(self.bootstrap.aws_profile.strip()) == 0:
            self.bootstrap.aws_profile = f'cdk_{self.account}_{self.region}'


@dataclass
class DeploymentConfig(DataClassJsonMixin):
    set_name: str
    enabled: bool = field(default=True)
    default_region: Optional[str] = field(default=None)
    stages: List[DeploymentStage] = field(default=None)

    def __post_init__(self):

        if self.set_name:
            self.set_name = self.set_name.strip()
        if self.default_region:
            self.default_region = self.default_region.strip()

        for ds in self.stages:
            ds.region = self.default_region if ds.region is None or ds.region.strip() == '' else ds.region.strip()

    def get_deployment_stage_by_name(self, name: str) -> DeploymentStage:
        return list(filter(lambda st: st.stage_name.lower() == name.lower(), self.stages)).pop()


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
    account: int | str = field(default=None)
    region: str = field(default=None)
    code_commit: CodeCommitRepo = field(default_factory=CodeCommitRepo)
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)

    def __post_init__(self):

        if len(self.bootstrap.execution_policy_filepath.strip()) == 0:
            base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')
            self.bootstrap.execution_policy_filepath = f'{base_dir}{os.path.sep}config{os.path.sep}execution_policy_' \
                                                       f'{self.account}_{self.region}.json'

        if len(self.bootstrap.aws_profile.strip()) == 0:
            self.bootstrap.aws_profile = f'cdk_{self.account}_{self.region}'

        self.account = DataValidations.account_id_validation('Pipeline ,', self.account)
        self.region = DataValidations.region_validation('Pipeline ,', self.region)


@dataclass
class CdkAppConfig(DataClassJsonMixin):
    app_prefix: str = field(default='mlops-cdk')
    pipeline: PipelineConfig = field(default=None)
    deployments: List[DeploymentConfig] = field(default=None)

    def __post_init__(self):
        if self.deployments:
            for dc in self.deployments:
                if dc.default_region is None or dc.default_region.strip() == '':
                    dc.default_region = self.pipeline.region
                dc.default_region = DataValidations.region_validation(f'default region for deployment set '
                                                                      f'{dc.set_name} ,', dc.default_region)
                for ds in dc.stages:
                    ds.region = dc.default_region if ds.region is None or ds.region.strip() == '' else ds.region.strip()
                    ds.region = DataValidations.region_validation(f'Deployment set '
                                                                  f'\'{dc.set_name}\' , '
                                                                  f'Deployment stage \'{ds.stage_name}\'',
                                                                  ds.region)

                    ds.account = DataValidations.account_id_validation(f'Deployment set '
                                                                       f'\'{dc.set_name}\' , '
                                                                       f'Deployment stage \'{ds.stage_name}\'',
                                                                       ds.account)


@dataclass
class AppConfig(YamlDataClassConfig):
    cdk_app_config: CdkAppConfig = field(default=None)
