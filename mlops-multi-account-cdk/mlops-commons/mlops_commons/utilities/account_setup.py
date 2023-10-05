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

# !/usr/bin/env python3

import os
import subprocess
import sys
from logging import Logger

from .cdk_app_config import (
    CdkAppConfig,
    PipelineConfig,
    BootstrapConfig,
    DeploymentStage
)
from .config_helper import ConfigHelper
from .log_helper import LogHelper
from .cdk_execution_policy import CdkExecutionPolicy


class AccountSetup:

    def __init__(self):
        self.logger: Logger = LogHelper.get_logger(self)
        self.config_helper: ConfigHelper = ConfigHelper()
        self.execution_policy: CdkExecutionPolicy = CdkExecutionPolicy(base_dir=self.config_helper.base_dir)

    def main(self):

        self.logger.info(f'Starting to setup account...')

        cdk_app_config: CdkAppConfig = self.config_helper.get_config()
        pipeline_conf: PipelineConfig = cdk_app_config.pipeline
        pipeline_bootstrap_conf: BootstrapConfig = pipeline_conf.get_bootstrap()

        if pipeline_bootstrap_conf.enabled:
            self.bootstrap_governance_account(cdk_app_config=cdk_app_config)
        else:
            self.logger.info(f'Bootstrapping is disabled for governance '
                             f'account : {pipeline_conf.account}, '
                             f'region : {pipeline_conf.region}')

        dev_account: str = ''
        for ds in filter(lambda x: x.enabled, cdk_app_config.deployments):

            self.logger.info(f'################## Starting to process set_name : {ds.set_name} ################## ')

            for stage in filter(lambda y: y.enabled, ds.get_deployment_stages()):

                if str(stage.stage_name).strip().lower() == 'dev':
                    dev_account: str = str(stage.account)

                self.bootstrap_stage_account(
                    app_prefix=cdk_app_config.app_prefix,
                    governance_account=str(pipeline_conf.account),
                    governance_region=pipeline_conf.region,
                    dev_account=dev_account,
                    set_name=ds.set_name,
                    stage=stage
                )

            self.logger.info(f'################## Finished processing of set_name : {ds.set_name} ################## ')

    def bootstrap_stage_account(self,
                                app_prefix: str,
                                governance_account: str,
                                governance_region: str,
                                dev_account: str,
                                set_name: str,
                                stage: DeploymentStage):

        stage_bootstrap_conf: BootstrapConfig = stage.get_bootstrap()

        if stage_bootstrap_conf.enabled:
            execution_policy_arn: str = self.execution_policy.get_policy_arn(
                app_prefix=app_prefix,
                account=str(stage.account),
                conf=stage_bootstrap_conf
            )
            # 'arn:aws:iam::aws:policy/AdministratorAccess'
            self.logger.info(f'Starting to bootstrap '
                             f'{stage.stage_name}, account : {stage.account}, region : {stage.region}, '
                             f'pipeline region : {governance_region}'
                             f' with execution policy : "{execution_policy_arn}"')

            profile: str = stage_bootstrap_conf.aws_profile
            region: str = stage.region
            accounts_to_trust: str = f'{governance_account}'

            if len(str(stage.region).strip()) == 0:
                region = governance_region
                self.logger.info(f' stage_name : {stage.stage_name} account : {stage.account}, '
                                 f'does not have valid region, so defaulting to pipeline region : {governance_region}')

            if str(stage.stage_name).strip().lower() != 'dev':
                accounts_to_trust = f'{governance_account},{dev_account}'

            cmd: str = f'cdk bootstrap aws://{stage.account}/{region} ' \
                       f'--trust {accounts_to_trust} ' \
                       f'--cloudformation-execution-policies {execution_policy_arn} ' \
                       f'--profile {profile}'

            if not self.run(cmd, stage.account, stage.region):
                sys.exit(-1)
        else:
            self.logger.info(f'Bootstrapping is disabled for '
                             f'set_name : {set_name}, '
                             f'stage_name : {stage.stage_name}, '
                             f'account : {stage.account}, '
                             f'region : {stage.region}')

    def bootstrap_governance_account(self, cdk_app_config: CdkAppConfig):

        pipeline_conf: PipelineConfig = cdk_app_config.pipeline
        pipeline_bootstrap_conf: BootstrapConfig = pipeline_conf.get_bootstrap()

        governance_execution_policy_arn: str = self.execution_policy.get_policy_arn(
            app_prefix=cdk_app_config.app_prefix,
            account=str(pipeline_conf.account),
            conf=pipeline_conf.get_bootstrap()
        )
        # 'arn:aws:iam::aws:policy/AdministratorAccess'
        self.logger.info(f'Starting to bootstrap '
                         f'governance account : {pipeline_conf.account}, region : {pipeline_conf.region},'
                         f' with execution policy : "{governance_execution_policy_arn}"')
        profile: str = pipeline_bootstrap_conf.aws_profile
        cmd: str = f'cdk bootstrap aws://{pipeline_conf.account}/{pipeline_conf.region} ' \
                   f'--cloudformation-execution-policies {governance_execution_policy_arn} ' \
                   f'--profile {profile}'
        if not self.run(cmd, pipeline_conf.account, pipeline_conf.region):
            sys.exit(-1)
        self.logger.info('Finished bootstrapping of governance account')

    def run(self, cmd: str, account: int, region: str) -> bool:
        print(os.linesep)
        self.logger.info(f'command : {cmd}')
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
        error: bool = False
        num_lines: int = 0
        while True:
            line = process.stdout.readline().rstrip()
            if not line and num_lines > 7:
                break
            if not error and f'Environment aws://{account}/{region} failed bootstrapping: Error:' in line:
                error = True
            print(line)
            num_lines = num_lines + 1

        process.kill()
        self.logger.info(f'Bootstrapping for account : {account}, region : {region}, status : {not error}')
        print(os.linesep)
        return not error

    def load_file(self, filepath) -> str:
        self.logger.info(f'Loading file : {filepath}')
        with open(file=filepath, mode='r', encoding='utf-8') as f:
            content = f.read()
        return content


if __name__ == "__main__":
    AccountSetup().main()
