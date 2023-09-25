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

import json
import os
from dataclasses import dataclass, field
from typing import List

from dataclasses_json import DataClassJsonMixin, config
from yamldataclassconfig.config import YamlDataClassConfig


@dataclass
class DeploymentStage(DataClassJsonMixin):
    stage_name: str
    account: int
    enabled: bool = field(default=True)
    region: str = field(default='')


@dataclass
class DeploymentConfig(DataClassJsonMixin):
    set_name: str
    enabled: bool = field(default=True)
    default_region: str = field(default=os.getenv('CDK_DEFAULT_REGION'))
    stages: List[DeploymentStage] = field(default=None)

    def get_deployment_stages(self) -> List[DeploymentStage]:
        st: List[DeploymentStage] = list()
        for ds in self.stages:
            st.append(DeploymentStage(
                stage_name=ds.stage_name,
                account=ds.account,
                enabled=ds.enabled,
                region=self.default_region if ds.region is None or ds.region.strip() == '' else ds.region.strip()
            ))
        return st

    def get_deployment_stage_by_name(self, name: str) -> DeploymentStage:
        return list(filter(lambda st: st.stage_name.lower() == name.lower(), self.get_deployment_stages())).pop()


@dataclass
class CodeCommitConfig(DataClassJsonMixin):
    repo_name: str
    branch_name: str


@dataclass
class PipelineConfig(DataClassJsonMixin):
    account: int = field(default=os.getenv('CDK_DEFAULT_ACCOUNT'))
    region: str = field(default=os.getenv('CDK_DEFAULT_REGION'))
    code_commit: CodeCommitConfig = field(default=None)


@dataclass
class CdkAppConfig(DataClassJsonMixin):
    app_prefix: str = field(default='mlops-cdk')
    pipeline: PipelineConfig = field(default=None)
    deployments: List[DeploymentConfig] = field(default=None)


@dataclass
class AppConfig(YamlDataClassConfig):
    cdk_app_config: CdkAppConfig = field(default=None)


@dataclass
class DeploymentConfigOld(DataClassJsonMixin):
    dev_account: int = field(metadata=config(field_name="DEV_ACCOUNT"))
    set_name: str = field(default=f'', metadata=config(field_name="SET_NAME"))
    preprod_account: int = field(default=-1, metadata=config(field_name="PREPROD_ACCOUNT"))
    prod_account: int = field(default=-1, metadata=config(field_name="PROD_ACCOUNT"))
    deployment_region: str = field(
        default=os.getenv('CDK_DEFAULT_REGION'),
        metadata=config(field_name="DEPLOYMENT_REGION")
    )


class AppConfigOld:

    def __init__(self):
        self.cdk_app_config_old: List[DeploymentConfigOld] = list()

    def load(self, file_path: str):
        with open(file_path, 'r', encoding="utf-8") as file:
            json_obj = json.load(file)
            for rec in json_obj:
                self.cdk_app_config_old.append(DeploymentConfigOld.from_dict(rec))

    def get_new_app_config(self) -> AppConfig:

        from cdk_service_catalog.config.constants import (
            APP_PREFIX,
            PIPELINE_BRANCH,
            PIPELINE_ACCOUNT,
            DEFAULT_DEPLOYMENT_REGION,
            CODE_COMMIT_REPO_NAME
        )

        code_commit: CodeCommitConfig = CodeCommitConfig(repo_name=CODE_COMMIT_REPO_NAME, branch_name=PIPELINE_BRANCH)
        pipeline: PipelineConfig = PipelineConfig(
            account=PIPELINE_ACCOUNT,
            region=DEFAULT_DEPLOYMENT_REGION,
            code_commit=code_commit
        )
        deployments: List[DeploymentConfig] = list()
        cdk_app_config: CdkAppConfig = CdkAppConfig(app_prefix=APP_PREFIX, pipeline=pipeline, deployments=deployments)
        conf: AppConfig = AppConfig(cdk_app_config=cdk_app_config)

        for old_dc in self.cdk_app_config_old:
            stages: List[DeploymentStage] = list()
            dc: DeploymentConfig = DeploymentConfig(
                set_name=f'devconf-{old_dc.dev_account}'
                if old_dc.set_name is None or old_dc.set_name.strip() == '' else old_dc.set_name,
                enabled=True, default_region=old_dc.deployment_region,
                stages=stages
            )
            stages.append(DeploymentStage(stage_name='Dev',
                                          account=old_dc.dev_account,
                                          enabled=True,
                                          region=old_dc.deployment_region)
                          )
            stages.append(DeploymentStage(stage_name='Preprod',
                                          account=old_dc.preprod_account,
                                          enabled=True,
                                          region=old_dc.deployment_region)
                          )
            stages.append(DeploymentStage(stage_name='Prod',
                                          account=old_dc.prod_account,
                                          enabled=True,
                                          region=old_dc.deployment_region)
                          )
            deployments.append(dc)
        return conf
