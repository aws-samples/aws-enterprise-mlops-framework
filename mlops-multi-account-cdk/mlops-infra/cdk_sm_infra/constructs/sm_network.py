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
    aws_ec2 as ec2,
    aws_ssm as ssm,
)
from constructs import Construct


class SMNetwork(Construct):
    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        self.primary_vpc = ec2.Vpc(
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

        # Subnet IDs parameters
        default_sg_id_param = ssm.StringParameter(
            self,
            "DefaultSecurityGroupIDParameter",
            parameter_name="/vpc/sg/id",
            string_value=self.primary_vpc.vpc_default_security_group,
        )

        # # setup VPC endpoints - they are required for instances were the domain does not have internet access

        # S3 VPC Endpoint
        self.primary_vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)

        # KMS VPC Endpoint
        self.primary_vpc.add_interface_endpoint("KMSEndpoint", service=ec2.InterfaceVpcEndpointAwsService.KMS)

        # ECR VPC Endpoint
        self.primary_vpc.add_interface_endpoint("ECREndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR)

        # ECR DOCKER VPC Endpoint
        self.primary_vpc.add_interface_endpoint(
            "ECRDockerEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
        )
