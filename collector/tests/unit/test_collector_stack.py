import aws_cdk as core
import aws_cdk.assertions as assertions

from collector.collector_stack import CollectorStack

# example tests. To run these tests, uncomment this file along with the example
# resource in collector/collector_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CollectorStack(app, "collector")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
