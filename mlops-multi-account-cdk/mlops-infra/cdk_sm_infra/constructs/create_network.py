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

from cdk_utilities.cdk_infra_app_config import CreateNetworkConfig
from mlops_commons.utilities.log_helper import LogHelper

"""
This will create new vpc, subnets as per given configuration in the account to be used in the CDK APP.
"""


class CreateNetwork(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            conf: CreateNetworkConfig
    ) -> None:
        super().__init__(scope, construct_id, )
        self.logger: Logger = LogHelper.get_logger(self)

        self.vpc = ec2.Vpc(
            self,
            "PrimaryVPC",
            ip_addresses=ec2.IpAddresses.cidr(conf.vpc_cidr),
            max_azs=conf.vpc_max_azs,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=conf.vpc_private_subnet_cidr_mask,
                ),
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC,
                                        cidr_mask=conf.vpc_public_subnet_cidr_mask),
            ],
            enable_dns_hostnames=conf.vpc_enable_dns_hostnames,
            enable_dns_support=conf.vpc_enable_dns_support,
            nat_gateways=conf.vpc_nat_gateways,
        )

        # # setup VPC endpoints - they are required for instances were the domain does not have internet access

        # S3 VPC Endpoint
        if conf.vpc_add_s3_endpoint:
            self.vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)

        # KMS VPC Endpoint
        if conf.vpc_add_kms_endpoint:
            self.vpc.add_interface_endpoint("KMSEndpoint", service=ec2.InterfaceVpcEndpointAwsService.KMS)

        # ECR VPC Endpoint
        if conf.vpc_add_ecr_endpoint:
            self.vpc.add_interface_endpoint("ECREndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR)

        # ECR DOCKER VPC Endpoint
        if conf.vpc_add_ecr_docker_endpoint:
            self.vpc.add_interface_endpoint(
                "ECRDockerEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
            )
        self.subnets = self.vpc.private_subnets
        self.default_security_group = self.vpc.vpc_default_security_group
