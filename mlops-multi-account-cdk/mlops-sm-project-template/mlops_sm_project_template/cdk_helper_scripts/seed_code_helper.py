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
import logging
from typing import Optional

def has_initial_model_approval(build_app_path: str) -> Optional[bool]:
    logging.info(f'retrieving model approval status from buildspec.yml of build_app from : {build_app_path}')
    build_spec_path: str = os.path.join(build_app_path, 'buildspec.yml')
    if os.path.exists(build_spec_path):
        with open(build_spec_path, 'r', encoding='utf-8') as f:
            for line in f:
                if 'ModelApprovalStatus' in line:
                    value: str = line.split("ModelApprovalStatus")[-1].split(",")[0]
                    value = re.sub('[{}:"\\\\]', '', value).lower().strip()
                    return value == 'approved'
    return False

def has_docker_artifacts(build_app_path: str) -> bool:
    logging.info(f'retrieving dockerfile from build_app from : {build_app_path}')
    build_spec_path: str = os.path.join(build_app_path, 'buildspec.yml')
    dockerfile_path: str = os.path.join(build_app_path, 'source_scripts', 'Dockerfile')
    docker_build_sh_path: str = os.path.join(build_app_path, 'source_scripts', 'docker-build.sh')
    if os.path.exists(dockerfile_path) and os.path.exists(docker_build_sh_path) and os.path.exists(build_spec_path):
        with open(build_spec_path, 'r', encoding='utf-8') as f:
            for line in f:
                if 'ecr_repo_uri' in line.lower():
                    return line.split('ecr_repo_uri')[-1].replace('\\', '').replace('"', '').strip().startswith(':')
    return False
