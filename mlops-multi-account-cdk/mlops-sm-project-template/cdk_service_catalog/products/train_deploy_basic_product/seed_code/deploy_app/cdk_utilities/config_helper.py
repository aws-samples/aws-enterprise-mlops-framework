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
import os
from logging import Logger
from pathlib import Path
from typing import Optional

from .cdk_deploy_app_config import (
    DeployAppConfig,
    CdkDeployAppConfig, ProductionVariantConfig
)
from .constants import INFRA_SET_NAME


class ConfigHelper(object):
    logging.basicConfig(level=logging.INFO)

    INSTANCE: 'ConfigHelper' = None

    def __init__(self):

        if hasattr(self, 'INSTANCE_INITIALIZED'):
            return

        self.logger: Logger = logging.getLogger(self.__class__.__name__)
        self.base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')
        self.app_config: Optional[DeployAppConfig] = DeployAppConfig()
        self.logger.info(f'cdk deploy app base directory : {self.base_dir}')

        yaml_config_path: str = os.path.join(
            self.base_dir,
            'config',
            'cdk-deploy-app.yml'
        )

        self.logger.info(f'Trying to loading cdk deploy app configuration file : {yaml_config_path}')
        if os.path.exists(yaml_config_path):
            self.app_config.load(Path(yaml_config_path))
        self.INSTANCE_INITIALIZED = True
        self.logger.debug(f'cdk deploy app config : {str(self.app_config)}')

    def __new__(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE

    @staticmethod
    def get_config() -> CdkDeployAppConfig:
        return ConfigHelper().app_config.cdk_deploy_app_config

    def get_config_by(self, stage_name: str) -> ProductionVariantConfig:
        return self.app_config.cdk_deploy_app_config.get_product_variant_by(
            set_name=INFRA_SET_NAME,
            stage_name=stage_name
        )
