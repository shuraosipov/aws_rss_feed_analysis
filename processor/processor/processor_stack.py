from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_events as events,
    aws_glue as glue,
    aws_glue_alpha as glue_alpha,
    aws_events_targets as targets,
    aws_iam as iam,
)
from constructs import Construct

class ProcessorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)



        # glue workflow
        workflow = glue.CfnWorkflow(self, "workflow", name="RssFeedProcessorWorkflow", 
                max_concurrent_runs=1,
                description="ETL workflow to cleanup and processing AWS RSS Feed data",
        )


        iam_role_glue = iam.Role(self, "glue-shell-job-role", 
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            role_name="RssFeedProcessorGlueShellJobRole",
            description="Glue shell job role to run ETL workflow",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
            ]
        )

        iam_role_glue.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
            ],
            resources=[
                "arn:aws:s3:::shuraosipov-rss-feed-analysis/landing/*",
                "arn:aws:s3:::shuraosipov-rss-feed-analysis/processed/*",
                "arn:aws:s3:::shuraosipov-rss-feed-analysis/athena_output/*",
            ]
        ))

        iam_role_glue.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
            ],
            resources=[
                "*",
            ] 
        ))

        # glue shell job
        job = glue_alpha.Job(self, "PythonShellJob",
            executable=glue_alpha.JobExecutable.python_shell(
                glue_version=glue_alpha.GlueVersion.V1_0,
                python_version=glue_alpha.PythonVersion.THREE,
                script=glue_alpha.Code.from_asset("scripts/script.py"),
            ),
            description="Cleanup and Processing for AWS RSS Feed data",
            role=iam_role_glue,
        )

        # glue workflow
        trigger = glue.CfnTrigger(self, "trigger",
            name="RssFeedProcessorTrigger",
            type="ON_DEMAND",
            workflow_name=workflow.name,
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=job.job_name,
                    arguments={
                        "--bucket": "shuraosipov-rss-feed-analysis",
                        "--table": "aws_feed_landing",
                        "--output": "processed/feed_2.csv",
                    }
                )
            ]
        )

        # iam role for event bridge rule to trigger aws glue shell job
        iam_role_event_bridge = iam.Role(self, "event-bridge-role",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
            role_name="RssFeedProcessorEventBridgeRole",
            description="Event bridge role to trigger glue shell job",
        )

        # attach policy to event bridge role
        iam_role_event_bridge.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "glue:notifyEvent",

                ],
                resources=[
                    f"arn:aws:glue:us-east-1:419091122511:workflow/{workflow.name}",
                ]
            )
        )
        
        # add target to event bridge rule
        glue_workflow_target = events.CfnRule.TargetProperty(
            id="target-workflow-id",
            arn="arn:aws:glue:us-east-1:419091122511:workflow/RssFeedProcessorWorkflow",
            role_arn=iam_role_event_bridge.role_arn,
        )

        # event bridge rule to trigger aws glue shell job
        rule = events.Rule(self, "rule",
            description="Event bridge rule to trigger glue workflow",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {
                        "name": ["shuraosipov-rss-feed-analysis"]
                        },
                    "object": {
                        "key": [{ "prefix": "landing/" }]
                    }
                }
            ),
        )

        


        
        