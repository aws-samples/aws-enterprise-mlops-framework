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

from constructs import Construct
from cdk_sm_infra.constructs.sm_studio_network import SMStudioNetwork
from cdk_sm_infra.constructs.sm_studio import SMStudio


class SMStudioInfra(Construct):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            app_prefix: str,
            use_network_from_stage_config: bool = False
    ) -> None:
        super().__init__(scope, construct_id)

        network = SMStudioNetwork(self, "sm_studio_network", use_network_from_stage_config)
        subnets = network.primary_vpc.private_subnets

        sagemaker_studio = SMStudio(
            self,
            "sagemaker-studio",
            app_prefix=app_prefix,
            vpc=network.primary_vpc,
            subnets=subnets
        )
