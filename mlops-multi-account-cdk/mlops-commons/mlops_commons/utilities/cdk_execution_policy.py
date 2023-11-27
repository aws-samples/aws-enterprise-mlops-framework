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
from logging import Logger
from typing import Dict, List, Any

import boto3

from .cdk_app_config import BootstrapConfig
from .log_helper import LogHelper


class CdkExecutionPolicy:

    def __init__(self, base_dir: str):
        self.logger: Logger = LogHelper.get_logger(self)
        self.base_dir: str = base_dir

    def get_policy_arn(self, app_prefix: str, account: str, conf: BootstrapConfig) -> str:

        self.logger.debug(f'Fetching policy app_prefix : {app_prefix} , account : {account}, config : {str(conf)} ')

        execution_policy_arn: str = conf.execution_policy_arn

        if account in execution_policy_arn:
            self.logger.info(f'Found user provided execution policy from config : {execution_policy_arn}')
            return execution_policy_arn

        execution_policy_real_filepath: str = os.path.join(
            self.base_dir,
            conf.execution_policy_filepath
        )

        self.logger.info(f'Checking if execution policy file is provided : {execution_policy_real_filepath}')

        if os.path.exists(execution_policy_real_filepath):

            self.logger.info(f'Given Execution Policy File Found')

            policy_name: str = f'{app_prefix}_cdk_cloudforamtion_execution_policy'
            policy_arn: str = f'arn:aws:iam::{account}:policy/{policy_name}'

            session = boto3.session.Session(profile_name=conf.aws_profile)

            try:
                self.logger.info(f'Checking if this policy already available by arn -> {policy_arn}')

                iam = session.resource('iam')
                policy = iam.Policy(policy_arn)
                default_version = policy.default_version

                self.logger.info(f'Execution Policy Found in IAM !!!!, name : {policy_name}, '
                                 f'default version : {default_version.version_id}')

                self.logger.info(f'Now checking if this policy is changed in '
                                 f'configuration file : {execution_policy_real_filepath}')
                policy_document_from_conf: str = self.load_file(execution_policy_real_filepath)
                policy_json_from_conf = json.loads(policy_document_from_conf)

                if policy_json_from_conf != default_version.document:
                    self.logger.info(f'Change detected in execution policy!!! , '
                                     f'start creating a new policy version and setting that to default version')
                    execution_policy_arn = self.create_policy_version(
                        policy_arn=policy_arn,
                        policy_document=policy_document_from_conf,
                        session=session
                    )
                else:
                    self.logger.info(f'Execution Policy : {policy_name} is up to date as per configuration file.')

            except Exception as e:
                err_msg: str = str(e)
                self.logger.error(f'Exception occurred while fetching policy : {err_msg}')
                if 'NoSuchEntity' in err_msg:
                    execution_policy_arn = self.create_policy(
                        policy_name=policy_name,
                        policy_file=execution_policy_real_filepath,
                        session=session
                    )

        else:
            self.logger.info(f'Using default execution policy arn -> {execution_policy_arn}')

        return execution_policy_arn

    def create_policy(self, session: boto3.Session, policy_name, policy_file: str) -> str:
        self.logger.info(f'Now creating execution policy by name : {policy_name}')

        res = session.client('iam').create_policy(
            PolicyName=policy_name,
            PolicyDocument=self.load_file(policy_file),
            Description='CDK Execution policy'
        )
        execution_policy_arn = res['Policy']['Arn']
        self.logger.info(f'Successfully Created Execution Policy arn -> {execution_policy_arn}')
        return execution_policy_arn

    def create_policy_version(self, session: boto3.Session, policy_arn, policy_document: str) -> str:

        self.logger.info(f'Now creating execution policy version by arn ->  {policy_arn}')

        client = session.client('iam')

        self.delete_policy_version(client, policy_arn)

        res = client.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=policy_document,
            SetAsDefault=True
        )
        version_id = res['PolicyVersion']['VersionId']
        self.logger.info(f'Successfully Created Execution Policy version id -> {version_id}')
        return policy_arn

    def delete_policy_version(self, client, policy_arn):
        max_items: int = 5
        version_res = client.list_policy_versions(
            PolicyArn=policy_arn,
            MaxItems=max_items
        )
        versions_without_default: [Dict[List, Any]] = list(
            filter(lambda v: not v['IsDefaultVersion'], version_res['Versions'])
        )
        if len(versions_without_default) + 1 == max_items:
            sorted_version: [Dict[List, Any]] = sorted(versions_without_default,
                                                       key=lambda v: v['CreateDate'], reverse=False)
            oldest_policy_version: Dict[str, Any] = sorted_version[0]
            self.logger.info(
                f'There are already {max_items} version(s) available, '
                f'deleting oldest policy version which is not default version  : {oldest_policy_version}')
            del_res = client.delete_policy_version(
                PolicyArn=policy_arn,
                VersionId=oldest_policy_version['VersionId']
            )
            self.logger.info(f'Successfully deleted policy '
                             f'version : {oldest_policy_version["VersionId"]} of '
                             f'policy : {policy_arn} , '
                             f'response http status code :{del_res["ResponseMetadata"]["HTTPStatusCode"]}')

    def load_file(self, filepath) -> str:
        self.logger.info(f'Loading file : {filepath}')
        with open(file=filepath, mode='r', encoding='utf-8') as f:
            content = f.read()
        return content
