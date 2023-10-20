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
from typing import Optional

from mlops_commons.utilities.log_helper import LogHelper


class SeedCodeHelper(object):
    logging.basicConfig(level=logging.INFO)

    INSTANCE: 'SeedCodeHelper' = None

    def __init__(self):
        # if hasattr(self, 'INSTANCE_INITIALIZED'):
        #     return
        self.logger: Logger = LogHelper.get_logger(self)
        self.INSTANCE_INITIALIZED = True

    def __new__(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = super().__new__(cls)
        return cls.INSTANCE

    def has_initial_modal_approval(self, build_app_path: str) -> Optional[bool]:
        self.logger.info(f'retrieving model approval status from buildspec.yml of build_app from : {build_app_path}')
        build_spec_path: str = os.path.join(build_app_path, 'buildspec.yml')
        if os.path.exists(build_spec_path):
            with open(build_spec_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'ModelApprovalStatus' in line:
                        return line.split('ModelApprovalStatus')[-1].strip()\
                            .replace("\\", "")\
                            .replace(':', '')\
                            .replace(' ', '')\
                            .replace('"', '')\
                            .replace("'", '')\
                            .replace(',', '') \
                            .replace("{", '') \
                            .replace("}", '')\
                            .lower().strip() \
                            == 'approved'
        return False

    def has_docker_artifacts(self, build_app_path: str) -> bool:
        self.logger.info(f'retrieving dockerfile from build_app from : {build_app_path}')
        build_spec_path: str = os.path.join(build_app_path, 'buildspec.yml')
        dockerfile_path: str = os.path.join(build_app_path, 'source_scripts', 'Dockerfile')
        docker_build_sh_path: str = os.path.join(build_app_path, 'source_scripts', 'docker-build.sh')
        if os.path.exists(dockerfile_path) and os.path.exists(docker_build_sh_path) and os.path.exists(build_spec_path):
            with open(build_spec_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'ecr_repo_uri' in line.lower():
                        return True
        return False
