from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    # aws_sqs as sqs,
)
from constructs import Construct

import uuid

class CollectorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Read context parameters defined in cdk.json
        bucket_name = self.node.try_get_context("bucket_name")
        days_range = self.node.try_get_context("days_range")
        feed_url = self.node.try_get_context("feed_url")
        layer_version_arns = self.node.try_get_context("layer_version_arns")

        # a function that return list of layers based on layer version arn
        def get_layers(layer_version_arns):
            layers = []

            for layer_version in layer_version_arns:
                layer = lambda_.LayerVersion.from_layer_version_arn(
                    scope=self, 
                    id=f"layer_{uuid.uuid4().hex}", 
                    layer_version_arn=layer_version

                )
                layers.append(layer)
            return layers
        
        function = lambda_.Function(self, "CollectorFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda"),
            handler="lambda_function.lambda_handler",
            timeout=Duration.seconds(15),
            layers=get_layers(layer_version_arns), 
            environment={
                "BUCKET_NAME": bucket_name,
                "DAYS_RANGE": days_range,
                "FEED_URL": feed_url,
            }
        )
