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

import logging
from logging import Logger
from deploy_endpoint.deploy_endpoint_stack import DeployEndpointStack
from cdk_utilities.constants import (
    DEFAULT_DEPLOYMENT_REGION,
    DEV_ACCOUNT,
    PREPROD_ACCOUNT,
    PREPROD_REGION,
    PROD_ACCOUNT,
    PROD_REGION,
    PROJECT_NAME,
    PROJECT_ID
)
from cdk_utilities.cdk_deploy_app_config import ProductionVariantConfig
from cdk_utilities.config_helper import ConfigHelper

import aws_cdk as cdk


class CdkDeployApp:
    logging.basicConfig(level=logging.INFO)

    def __init__(self):
        self.logger: Logger = logging.getLogger(self.__class__.__name__)
        self.logger.info('CdkDeployApp init')

    def main(self):
        self.logger.info(f'Starting to deploy app by Project Name: {PROJECT_NAME}, Project Id: {PROJECT_ID}')

        conf: ConfigHelper = ConfigHelper()
        app = cdk.App()

        for stage, account, region in [
            ('dev', DEV_ACCOUNT, DEFAULT_DEPLOYMENT_REGION),
            ('preprod', PREPROD_ACCOUNT, PREPROD_REGION),
            ('prod', PROD_ACCOUNT, PROD_REGION)
        ]:
            pv: ProductionVariantConfig = conf.get_config_by(stage_name=stage)
            self.logger.info(f'Deploying stage : {stage}, account : {account}, '
                             f'region : {region}, ProductionVariantConfig : {str(pv)}')
            DeployEndpointStack(app, stage, product_variant_conf=pv,
                                env=cdk.Environment(account=account, region=region))
        app.synth()


if __name__ == '__main__':
    CdkDeployApp().main()
