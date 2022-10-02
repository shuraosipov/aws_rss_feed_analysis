import uuid

from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_events_targets as targets
)
from aws_cdk.aws_events import Rule, Schedule
from constructs import Construct


class CollectorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Read context parameters defined in cdk.json
        bucket_name = self.node.try_get_context("bucket_name")
        days_range = self.node.try_get_context("days_range")
        feed_url = self.node.try_get_context("feed_url")
        layer_version_arns = self.node.try_get_context("layer_version_arns")
        sns_topic_arn = self.node.try_get_context("sns_topic_arn")

        # create IAM role for lambda function
        lambda_role = iam.Role(self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ]
        )

        # provide lambda function with write access to S3 bucket
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject"],
            resources=[f"arn:aws:s3:::{bucket_name}/*"]
        ))

        # provide lambda function with access to SNS topic
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sns:Publish"],
            resources=[sns_topic_arn]
        ))


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
            role=lambda_role,
            code=lambda_.Code.from_asset("lambda"),
            handler="lambda_function.lambda_handler",
            timeout=Duration.seconds(15),
            layers=get_layers(layer_version_arns), 
            environment={
                "BUCKET_NAME": bucket_name,
                "DAYS_RANGE": days_range,
                "FEED_URL": feed_url,
                "SNS_TOPIC_ARN": sns_topic_arn
            }
        )

        # event bridge rule to trigger lambda function every midnight
        Rule(self, "CollectorRule", 
            schedule=Schedule.cron(minute="02", hour="00"),
            targets=[targets.LambdaFunction(function)]
        )
