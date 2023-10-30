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
import logging
import sys
from logging import Logger
from pathlib import Path
from typing import Optional

from mlops_commons.utilities.cdk_app_config import (
    AppConfig,
    CdkAppConfig
)
from mlops_commons.utilities.log_helper import LogHelper


class ConfigHelper(object):
    logging.basicConfig(level=logging.INFO)

    INSTANCE: 'ConfigHelper' = None

    def __init__(self):

        if hasattr(self, 'INSTANCE_INITIALIZED'):
            return

        self.logger: Logger = LogHelper.get_logger(self)
        self.base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')

        self.app_config: Optional[AppConfig] = AppConfig()

        self.logger.info(f'cdk app base directory : {self.base_dir}')

        yaml_config_path: str = os.path.join(
            self.base_dir,
            'config',
            'cdk-app.yml'
        )

        self.logger.info(f'Trying to loading cdk app configuration file : {yaml_config_path}')
        if os.path.exists(yaml_config_path):
            self.app_config.load(Path(yaml_config_path))
        self.INSTANCE_INITIALIZED = True
        self.logger.debug(f'cdk app config : {str(self.app_config)}')

    def __new__(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE

    @staticmethod
    def get_config() -> CdkAppConfig:
        return ConfigHelper().app_config.cdk_app_config


# used for shell script to get attribute value
if __name__ == '__main__':
    if 'get_governance_profile' in sys.argv:
        print(ConfigHelper.get_config().pipeline.bootstrap.aws_profile)
