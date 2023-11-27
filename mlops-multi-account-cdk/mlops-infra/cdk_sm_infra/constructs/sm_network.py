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
from typing import Optional, Any, Tuple, List

from aws_cdk import (
    aws_ssm as ssm, )
from constructs import Construct

from cdk_sm_infra.constructs.create_network import CreateNetwork
from cdk_sm_infra.constructs.import_network import ImportNetwork
from cdk_utilities.cdk_infra_app_config import CreateNetworkConfig, \
    NetworkDeploymentStageConfig, ImportNetworkConfig
from mlops_commons.utilities.log_helper import LogHelper


class SMNetwork(Construct):
    def __init__(self, scope: Construct, construct_id: str, network_conf: NetworkDeploymentStageConfig) -> None:
        super().__init__(scope, construct_id)

        self.logger: Logger = LogHelper.get_logger(self)

        self.primary_vpc: Optional[Any] = None
        self.private_subnets: Optional[List[Any]] = None
        self.default_security_group: Optional[str] = None

        import_network_conf: ImportNetworkConfig = network_conf.import_network
        if import_network_conf:
            method_args = import_network_conf
            method_ref = self.import_network
        else:
            method_args = network_conf.create_network
            method_ref = self.create_network

        self.primary_vpc, self.private_subnets, self.default_security_group = method_ref(conf=method_args)

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
            string_list_value=[subnet.subnet_id for subnet in self.private_subnets],
        )

        # Default Security Group ID parameters
        default_sg_id_param = ssm.StringParameter(
            self,
            "DefaultSecurityGroupIDParameter",
            parameter_name="/vpc/sg/id",
            string_value=self.default_security_group,
        )

    def import_network(self, conf: ImportNetworkConfig) -> Tuple[Any, List[Any], Any]:
        self.logger.info(f'using user provided network setup : {str(conf)}')
        network: ImportNetwork = ImportNetwork(self, 'import_network', conf)
        return network.vpc, network.subnets, network.default_security_group

    def create_network(self, conf: CreateNetworkConfig) -> Tuple[Any, List[Any], Any]:
        self.logger.info(f'creating new vpc with  private and public subnet : {str(conf)}')
        network: CreateNetwork = CreateNetwork(self, 'create_network', conf)
        return network.vpc, network.subnets, network.default_security_group
