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
from typing import Optional, Any, Tuple

from aws_cdk import (
    aws_ec2 as ec2,
    aws_ssm as ssm, Stage,
)
from constructs import Construct
from cdk_sm_infra.constructs.networking import Networking
from logging import Logger
from mlops_commons.utilities.log_helper import LogHelper


class SMNetwork(Construct):
    def __init__(self, scope: Construct, construct_id: str, use_network_from_stage_config: bool = False) -> None:
        super().__init__(scope, construct_id)

        self.logger: Logger = LogHelper.get_logger(self)

        self.primary_vpc: Optional[Any] = None
        self.private_subnets: Optional[Any] = None
        self.default_security_group: Optional[Any] = None

        if use_network_from_stage_config:
            self.primary_vpc, self.private_subnets, self.default_security_group = self.network_from_stage_config()
        else:
            self.primary_vpc, self.private_subnets, self.default_security_group = self.create_network()

        # VPC ID parameters
        vpc_id_param = ssm.StringParameter(
            self,
            "VPCIDParameter",
            parameter_name="/vpc/id",
            string_value=self.primary_vpc.vpc_id,
        )

        # Private Subnet IDs parameters
        private_subnet_ids_param = ssm.StringListParameter(
            self,
            "PrivateSubnetIDsParameter",
            parameter_name="/vpc/subnets/private/ids",
            string_list_value=[subnet.subnet_id for subnet in self.primary_vpc.private_subnets],
        )

        # Default Security Group ID parameters
        default_sg_id_param = ssm.StringParameter(
            self,
            "DefaultSecurityGroupIDParameter",
            parameter_name="/vpc/sg/id",
            string_value=self.default_security_group,
        )

    def network_from_stage_config(self) -> Tuple[Any, Any, Any]:
        stage_name = Stage.of(self).stage_name.lower()
        self.logger.info(f'using user provided network setup from stage name : {stage_name}')
        network: Networking = Networking(self, 'custom_network', stage_name)
        return network.vpc, network.subnets, network.default_security_group

    def create_network(self) -> Tuple[Any, Any, Any]:
        self.logger.info(f'creating new vpc with  private and public subnet')
        primary_vpc = ec2.Vpc(
            self,
            "PrimaryVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=3,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=26),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=1,
        )

        # # setup VPC endpoints - they are required for instances were the domain does not have internet access

        # S3 VPC Endpoint
        primary_vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)

        # KMS VPC Endpoint
        primary_vpc.add_interface_endpoint("KMSEndpoint", service=ec2.InterfaceVpcEndpointAwsService.KMS)

        # ECR VPC Endpoint
        primary_vpc.add_interface_endpoint("ECREndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR)

        # ECR DOCKER VPC Endpoint
        primary_vpc.add_interface_endpoint(
            "ECRDockerEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
        )

        return primary_vpc, primary_vpc.private_subnets, primary_vpc.vpc_default_security_group
