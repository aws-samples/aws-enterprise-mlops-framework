#!/usr/bin/env python3
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

import cdk_utilities
from logging import Logger
import aws_cdk as cdk

from cdk_pipelines.cdk_pipeline_codecommit_repo import CdkPipelineCodeCommitStack
from cdk_pipelines.cdk_pipelines import CdkPipelineStack
from mlops_commons.utilities.cdk_app_config import CdkAppConfig, DeploymentStage
from mlops_commons.utilities.config_helper import ConfigHelper
from mlops_commons.utilities.log_helper import LogHelper


class MLOpsCdkApp:

    def __init__(self):
        self.logger: Logger = LogHelper.get_logger(self)
        self.logger.info(f'mlops_commons path : {cdk_utilities.mlops_commons_base_dir}')

    def main(self):

        self.logger.info('Starting cdk app...')

        app = cdk.App()
        cac: CdkAppConfig = ConfigHelper.get_config()

        CdkPipelineCodeCommitStack.get_repo(app, cac.pipeline)

        for dc in cac.deployments:

            dev_conf: DeploymentStage = dc.get_deployment_stage_by_name('Dev')

            self.logger.info(f'Start deploying config '
                             f'set name : {dc.set_name}, '
                             f'dev_account: {dev_conf.account}, '
                             f'deployment_region : {dev_conf.region}')

            if not dc.enabled or not dev_conf.enabled:
                self.logger.info(f'Skipping deployment of config ->'
                                 f'set name : {dc.set_name}, '
                                 f'dev_account: {dev_conf.account}, '
                                 f'deployment_region : {dev_conf.region} '
                                 f'enabled : {str(dev_conf.enabled)}'
                                 f' as it is disabled in configuration file. To enable it, set the attribute '
                                 f'enabled=True at deployments level in yaml configuration file ')
                continue

            CdkPipelineStack(
                app,
                f"ml-sc-deploy-pipeline-{dc.set_name}",
                app_prefix=cac.app_prefix,
                set_name=dc.set_name,
                deploy_conf=dev_conf,
                pipeline_conf=cac.pipeline,
                description="CI/CD CDK Pipelines for Sagemaker Projects Service Catalog",
                env=cdk.Environment(account=str(cac.pipeline.account), region=cac.pipeline.region)
            ).add_dependency(CdkPipelineCodeCommitStack.INSTANCE)

        app.synth()


if __name__ == "__main__":
    MLOpsCdkApp().main()
