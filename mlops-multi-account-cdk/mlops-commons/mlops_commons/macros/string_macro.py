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
from logging import Logger
from typing import Optional

import aws_cdk as core
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_cloudformation as cfn,
)
from constructs import Construct

from mlops_commons.utilities.log_helper import LogHelper


class StringMacro(Construct):
    def __init__(self, scope: Construct, construct_id: str, app_prefix: str = 'mlops') -> None:
        super().__init__(scope, construct_id)
        self.logger: Logger = LogHelper.get_logger(self)
        self.base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}')
        self.app_prefix: str = app_prefix

    def create(self, macro_name: Optional[str] = None):

        self.logger.info(f'macro base dir : {self.base_dir}')

        event_handler = PythonFunction(
            self,
            f"{self.app_prefix}-string-macro-function",
            runtime=lambda_.Runtime.PYTHON_3_11,
            entry=f"{self.base_dir}{os.path.sep}lambda{os.path.sep}string",
            index='string_handler.py',
            handler='handler',
            timeout=core.Duration.seconds(120)
        )

        event_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=["*"],
            )
        )
        event_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["logs:*"],
                resources=["arn:aws:logs:*:*:*"],
            )
        )

        macro = cfn.CfnMacro(
            self,
            f"{self.app_prefix}-string-macro",
            name=f"{self.app_prefix.capitalize()}StringFn" if not macro_name else macro_name,
            function_name=event_handler.function_arn,
            description="String macro"
        )

        self.logger.info(f'Cloudformation Macro will be created by name {macro.name} '
                         f'and function {macro.function_name}')
