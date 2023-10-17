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

from aws_cdk import (
    Aws,
    aws_ssm as ssm,
)

from constructs import Construct


class SSMConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, project_name: str, preprod_account: str, prod_account: str,
                 deployment_region: str) -> None:
        super().__init__(scope, construct_id)

        # SSM parameters for the project

        # TODO: if sets of accounts have overlapping accounts (eg same dev or preprod), the parameter names need to
        #  be "parametrized" as well

        # DEV parameters
        dev_account_id_param = ssm.StringParameter(
            self,
            "DevAccountIDParameter",
            # parameter_name="/mlops/dev/account_id",
            parameter_name=f"/mlops/{project_name}/dev/account_id",
            string_value=Aws.ACCOUNT_ID,
            simple_name=False,
        )

        dev_region_param = ssm.StringParameter(
            self,
            "DevRegionParameter",
            # parameter_name="/mlops/dev/account_id",
            parameter_name=f"/mlops/{project_name}/dev/region",
            string_value=Aws.REGION,
            simple_name=False,
        )

        # PREPROD parameters
        PREPROD_ACCOUNT_id_param = ssm.StringParameter(
            self,
            "PreProdAccountIDParameter",
            # parameter_name="/mlops/preprod/account_id",
            parameter_name=f"/mlops/{project_name}/preprod/account_id",
            string_value=preprod_account,
            simple_name=False,
        )

        PREPROD_REGION_param = ssm.StringParameter(
            self,
            "PreProdRegionParameter",
            # parameter_name="/mlops/preprod/region",
            parameter_name=f"/mlops/{project_name}/preprod/region",
            string_value=deployment_region,
            simple_name=False,
        )

        # PROD parameters
        prod_account_id_param = ssm.StringParameter(
            self,
            "ProdAccountIDParameter",
            # parameter_name="/mlops/prod/account_id",
            parameter_name=f"/mlops/{project_name}/prod/account_id",
            string_value=prod_account,
            simple_name=False,
        )

        prod_region_param = ssm.StringParameter(
            self,
            "ProdRegionParameter",
            # parameter_name="/mlops/prod/region",
            parameter_name=f"/mlops/{project_name}/prod/region",
            string_value=deployment_region,
            simple_name=False,
        )
