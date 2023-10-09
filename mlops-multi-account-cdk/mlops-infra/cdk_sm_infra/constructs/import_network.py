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

from logging import Logger

import aws_cdk
from aws_cdk import (
    aws_ec2 as ec2,
)
from constructs import Construct

from cdk_utilities.cdk_infra_app_config import ImportNetworkConfig
from mlops_commons.utilities.log_helper import LogHelper

"""
This is an optional construct to setup the Networking resources (VPC and Subnets) from existing 
resources in the account to be used in the CDK APP.
"""


class ImportNetwork(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            conf: ImportNetworkConfig
    ) -> None:
        super().__init__(scope, construct_id)
        self.logger: Logger = LogHelper.get_logger(self)

        # vpc resource to be used for the endpoint and lambda vpc configs
        self.vpc: ec2.Vpc = ec2.Vpc.from_lookup(
            self, f"VPC-{conf.vpc_id}", vpc_id=conf.vpc_id)

        # subnets resources should use
        # self.subnets = [
        #     ec2.Subnet.from_subnet_id(self, f"SUBNET-{subnet_id}", subnet_id)
        #     for subnet_id in conf.subnets
        # ]
        self.subnets = [
            ec2.Subnet.from_subnet_attributes(self, f"SUBNET-{subnet_id}", subnet_id=subnet_id)
            for subnet_id in conf.subnets
        ]
        for subnet in self.subnets:
            aws_cdk.Annotations.of(subnet).acknowledge_warning('@aws-cdk/aws-ec2:noSubnetRouteTableId')

        # default security group
        self.default_security_group = ec2.SecurityGroup.from_lookup_by_id(
            self, f'SG-{conf.base_security_group}', security_group_id=conf.base_security_group).security_group_id

        if self.default_security_group is None:
            self.logger.warning(f'No security group found by : {conf.base_security_group}, '
                                f'now using the default security group of vpc')
            self.default_security_group = self.vpc.vpc_default_security_group
