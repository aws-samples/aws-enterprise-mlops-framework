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
class ProductionVariantConfig(DataClassJsonMixin):
    initial_instance_count: Optional[int] = field(default=None)
    initial_variant_weight: Optional[int] = field(default=None)
    instance_type: Optional[str] = field(default=None)
    variant_name: Optional[str] = field(default=None)


@dataclass
class DefaultProductionVariantConfig(DataClassJsonMixin):
    initial_instance_count: Optional[int] = field(default=1)
    initial_variant_weight: Optional[int] = field(default=1)
    instance_type: Optional[str] = field(default='ml.g4dn.2xlarge')
    variant_name: Optional[str] = field(default='AllTraffic')


@dataclass
class DeploymentStageConfig(DataClassJsonMixin):
    stage_name: str
    production_variant: Optional[ProductionVariantConfig] = field(default_factory=ProductionVariantConfig)


@dataclass
class DeploymentConfig(DataClassJsonMixin):
    set_name: str
    stages: Optional[List[DeploymentStageConfig]] = field(default=None)

    def get_product_variant_by(self, stage_name: str) -> Optional[ProductionVariantConfig]:
        conf = list(
            filter(lambda x: str(x.stage_name).strip().lower() == stage_name.strip().lower(), self.stages)
        )
        return conf[0].production_variant if len(conf) > 0 else ProductionVariantConfig()


@dataclass
class CdkDeployAppConfig(DataClassJsonMixin):

    @staticmethod
    def get_default_deployments():
        return [DeploymentConfig(
            set_name=DEFAULT_VALUE,
            stages=[DeploymentStageConfig(stage_name=DEFAULT_VALUE)]
        )]

    default_production_variant: DefaultProductionVariantConfig = field(default_factory=DefaultProductionVariantConfig)
    deployments: Optional[List[DeploymentConfig]] = field(
        default_factory=lambda: CdkDeployAppConfig.get_default_deployments()
    )

    def get_product_variant_by(self, set_name: str, stage_name: str) -> Optional[ProductionVariantConfig]:

        conf = list(
            filter(lambda x: str(x.set_name).strip().lower() == set_name.strip().lower(), self.deployments)
        )

        # if cdk infra app configuration is not available for given
        # set name and stage name then use default configuration
        if conf is None or len(conf) == 0:
            conf = self.get_default_deployments()
            stage_name = DEFAULT_VALUE

        response = conf[0].get_product_variant_by(stage_name=stage_name)

        # updating production_variant value with updated default_production_variant value in case where
        # production_variant doesn't have any or some of the attributes from config
        if response:
            pv: ProductionVariantConfig = response

            if pv.initial_instance_count is None:
                pv.initial_instance_count = self.default_production_variant.initial_instance_count

            if pv.initial_variant_weight is None:
                pv.initial_variant_weight = self.default_production_variant.initial_variant_weight

            if pv.instance_type is None:
                pv.instance_type = self.default_production_variant.instance_type

            if pv.variant_name is None:
                pv.variant_name = self.default_production_variant.variant_name
        return response


@dataclass
class DeployAppConfig(YamlDataClassConfig):
    cdk_deploy_app_config: CdkDeployAppConfig = field(default_factory=CdkDeployAppConfig)
