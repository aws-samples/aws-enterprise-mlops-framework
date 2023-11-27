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
import yaml
import argparse
from logging import Logger
from pathlib import Path
from typing import Optional, Any
import random
from mlops_commons.utilities.cdk_app_config import (
    AppConfig,
    CdkAppConfig
)
from mlops_commons.utilities.log_helper import LogHelper


class ConfigHelper(object):
    logging.basicConfig(level=logging.INFO)

    INSTANCE: 'ConfigHelper' = None
    CONFIG_YAML_FILE_NAME: str = 'cdk-app.yml'

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
            self.CONFIG_YAML_FILE_NAME
        )

        self.logger.info(f'Trying to loading cdk app configuration file : {yaml_config_path}')
        if os.path.exists(yaml_config_path):
            self.app_config.load(Path(yaml_config_path))
        else:
            self.logger.error(f'Cdk app configuration file not found : {yaml_config_path}')
            sys.exit(1)

        self.INSTANCE_INITIALIZED = True
        self.logger.debug(f'cdk app config : {str(self.app_config)}')

    def __new__(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE

    @staticmethod
    def get_config() -> CdkAppConfig:
        return ConfigHelper().app_config.cdk_app_config

    @classmethod
    def create_config_file(cls) -> None:

        args = cls.parse_cli_args()
        print(f'config values : {args}')

        conf_dict = {
            'cdk_app_config': {
                'app_prefix': 'mlops',
                'pipeline': {
                    'account': args.gov_account,
                    'region': args.gov_region,
                    'bootstrap': {
                        'aws_profile': args.gov_profile
                    },
                    'code_commit': {
                        'infra': {
                            'repo_name': 'mlops-infra',
                            'branch_name': 'main'
                        },
                        'project_template': {
                            'repo_name': 'mlops-sm-project-template',
                            'branch_name': 'main'
                        }
                    }
                },
                'deployments': []

            }
        }
        for bu, stages in [('first-example', [
            ('dev', args.dev_account, args.dev_profile),
            ('preprod', args.preprod_account, args.preprod_profile),
            ('prod', args.prod_account, args.prod_profile)
        ])]:
            st = {
                'set_name': bu,
                'stages': []
            }
            conf_dict['cdk_app_config']['deployments'].append(st)
            for stage, account, profile in stages:
                st['stages'].append(
                    {
                        'stage_name': stage,
                        'account': account,
                        'bootstrap': {
                            'aws_profile': profile
                        }
                    }
                )

        base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..')

        yaml_config_path: str = os.path.join(
            base_dir,
            'config',
            cls.CONFIG_YAML_FILE_NAME
        )

        if os.path.exists(yaml_config_path):
            os.rename(yaml_config_path, f'{yaml_config_path}_{random.randint(1, 999)}_.bak')
        with open(yaml_config_path, 'w', encoding='utf-8') as yml_stream:
            yaml.dump(conf_dict, yml_stream, default_flow_style=False, sort_keys=False)
        print(f'Config file created successfully at : {yaml_config_path}')

    @staticmethod
    def parse_cli_args() -> Any:

        parser = argparse.ArgumentParser("MLOps Cdk app configuration.")

        for ctype in ['gov', 'dev', 'preprod', 'prod']:
            ctx: str = 'Governance/Pipeline' if ctype == 'gov' else ctype
            for cname in ['account', 'region', 'profile']:
                cli_mame: str = f"{ctype}_{cname}"
                parser.add_argument(
                    f"-{cli_mame}",
                    f"--{cli_mame}",
                    dest=cli_mame,
                    type=str,
                    help=f"{ctx.capitalize()} AWS {cname.capitalize()}",
                )

        args = parser.parse_args(args=sys.argv[2:])

        if args.gov_account is None or args.gov_region is None or args.gov_profile is None or \
                args.dev_account is None or args.dev_profile is None or \
                args.preprod_account is None or args.preprod_profile is None or \
                args.prod_account is None or args.prod_profile is None:
            parser.print_help()
            sys.exit(2)
        return args


# used for shell script to get attribute value
if __name__ == '__main__':
    if 'get_governance_profile' in sys.argv:
        print(ConfigHelper.get_config().pipeline.bootstrap.aws_profile)
    elif 'create_config_file' in sys.argv:
        ConfigHelper.create_config_file()
