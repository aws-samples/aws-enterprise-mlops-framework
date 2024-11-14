import aws_cdk as core
import aws_cdk.assertions as assertions

from iot_infra.iot_infra_stack import DeployEC2AndIotRole

# example tests. To run these tests, uncomment this file along with the example
# resource in iot_infra.iot_infra_stack/iot_infra_stack.py
def test_template():
    app = core.App()
    stack = DeployEC2AndIotRole(app, "edge-infra")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
