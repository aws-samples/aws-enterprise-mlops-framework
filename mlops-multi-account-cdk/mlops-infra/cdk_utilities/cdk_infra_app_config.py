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
from dataclasses import dataclass, field
from typing import List, Optional

from dataclasses_json import DataClassJsonMixin
from yamldataclassconfig.config import YamlDataClassConfig

DEFAULT_VALUE: str = 'default'


@dataclass
class CreateNetworkConfig(DataClassJsonMixin):
    vpc_cidr: str = field(default="10.0.0.0/16")
    vpc_max_azs: int = field(default=3)
    vpc_private_subnet_cidr_mask: int = field(default=24)
    vpc_public_subnet_cidr_mask: int = field(default=26)
    vpc_enable_dns_hostnames: bool = field(default=True)
    vpc_enable_dns_support: bool = field(default=True)
    vpc_nat_gateways: int = field(default=1)
    vpc_add_s3_endpoint: bool = field(default=True)
    vpc_add_kms_endpoint: bool = field(default=True)
    vpc_add_ecr_endpoint: bool = field(default=True)
    vpc_add_ecr_docker_endpoint: bool = field(default=True)


@dataclass
class ImportNetworkConfig(DataClassJsonMixin):
    vpc_id: str
    subnets: List[str]
    base_security_group: str


@dataclass
class NetworkDeploymentStageConfig(DataClassJsonMixin):
    stage_name: str
    create_network: CreateNetworkConfig = field(default_factory=CreateNetworkConfig)
    import_network: Optional[ImportNetworkConfig] = field(default=None)


@dataclass
class NetworkDeploymentConfig(DataClassJsonMixin):
    set_name: str
    stages: Optional[List[NetworkDeploymentStageConfig]] = field(default=None)

    def get_network_stage_config_by(self, stage_name: str) -> Optional[NetworkDeploymentStageConfig]:
        conf = list(
            filter(lambda x: str(x.stage_name).strip().lower() == stage_name.strip().lower(), self.stages)
        )
        return conf[0] if len(conf) > 0 else NetworkDeploymentStageConfig(stage_name=stage_name)


@dataclass
class NetworkConfig(DataClassJsonMixin):
    @staticmethod
    def get_default_deployments():
        return [NetworkDeploymentConfig(
            set_name=DEFAULT_VALUE,
            stages=[NetworkDeploymentStageConfig(stage_name=DEFAULT_VALUE)]
        )]

    default_create_network: CreateNetworkConfig = field(default_factory=CreateNetworkConfig)
    deployments: List[NetworkDeploymentConfig] = field(default_factory=lambda: NetworkConfig.get_default_deployments())

    def get_network_stage_config_by(self, set_name: str, stage_name: str) -> Optional[NetworkDeploymentStageConfig]:

        conf = list(
            filter(lambda x: str(x.set_name).strip().lower() == set_name.strip().lower(), self.deployments)
        )

        # if cdk infra app configuration is not available for given
        # set name and stage name then use default configuration
        if conf is None or len(conf) == 0:
            conf = self.get_default_deployments()
            stage_name = DEFAULT_VALUE

        response = conf[0].get_network_stage_config_by(stage_name=stage_name)

        return response


@dataclass
class SagemakerUserProfileName(DataClassJsonMixin):
    user_profile_name: str


@dataclass
class SagemakerUserProfileConfig(DataClassJsonMixin):
    prefix: str
    users: List[SagemakerUserProfileName]


@dataclass
class SagemakerProfileConfig(DataClassJsonMixin):
    data_scientists: SagemakerUserProfileConfig = field(
        default_factory=lambda: SagemakerUserProfileConfig('ds', [SagemakerUserProfileName("data-scientist")])
    )
    lead_data_scientists: SagemakerUserProfileConfig = field(
        default_factory=lambda: SagemakerUserProfileConfig('lead-ds', [SagemakerUserProfileName("lead-data-scientist")])
    )


@dataclass
class SagemakerConfig(DataClassJsonMixin):
    profiles: SagemakerProfileConfig = field(default_factory=SagemakerProfileConfig)


@dataclass
class CdkInfraAppConfig(DataClassJsonMixin):
    network: NetworkConfig = field(default_factory=NetworkConfig)
    sagemaker: SagemakerConfig = field(default_factory=SagemakerConfig)


@dataclass
class InfraAppConfig(YamlDataClassConfig):
    cdk_infra_app_config: CdkInfraAppConfig = field(default_factory=CdkInfraAppConfig)
