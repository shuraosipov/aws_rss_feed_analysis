from aws_cdk import (
    Duration,
    Stack,
    aws_events as events,
    aws_glue as glue,
    aws_glue_alpha as glue_alpha,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
)
from constructs import Construct

class ProcessorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # get context parameters
        bucket_name = self.node.try_get_context("bucket_name")
        account_id = self.node.try_get_context("aws_account_id")
        region = self.node.try_get_context("aws_region")
        sns_topic_arn = self.node.try_get_context("sns_topic_arn")
        table_name = self.node.try_get_context("table_name")
        database_name = self.node.try_get_context("database_name")

        # create glue database
        glue_db = glue_alpha.Database(self, "RssFeedProcessorGlueDatabase",
            database_name=database_name,
        )

        # create glue table
        glue_table = glue.CfnTable(self, "RssFeedProcessorGlueTable",
            catalog_id=account_id,
            database_name=glue_db.database_name,
            table_input=glue.CfnTable.TableInputProperty(
                name=table_name,
                description="RSS Feed Table",
                table_type="EXTERNAL_TABLE",
                parameters= {
                    "EXTERNAL": "TRUE",
                    "has_encrypted_data": "false",
                    "skip.header.line.count": "1",
                    "transient_lastDdlTime": "1665690435"
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(
                            name="id",
                            type="string"
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="services",
                            type="string"
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="title",
                            type="string"
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="link",
                            type="string"
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="date",
                            type="string"
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="description",
                            type="string"
                        )],
                    location=f"s3://{bucket_name}/landing",
                    input_format="org.apache.hadoop.mapred.TextInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
                        parameters={
                            "field.delim": ";",
                            "serialization.format": ";"
                        }
                    ),
                )
            )
        )


        # glue workflow
        workflow = glue.CfnWorkflow(self, "RssFeedProcessorGlueWorkflow", 
            name="RssFeedProcessorGlueWorkflow",
            max_concurrent_runs=1,
            description="ETL workflow to cleanup and processing AWS RSS Feed data",
        )

        # glue shell job
        iam_role_glue = iam.Role(self, "RssFeedProcessorGlueShellJobRole", 
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
                f"arn:aws:s3:::{bucket_name}/landing/*",
                f"arn:aws:s3:::{bucket_name}/processed/*",
                f"arn:aws:s3:::{bucket_name}/athena_output/*",
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

        iam_role_glue.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sns:Publish"],
            resources=[sns_topic_arn]
        ))

        
        job = glue_alpha.Job(self, "RssFeedProcessorGlueJob",
            executable=glue_alpha.JobExecutable.python_shell(
                glue_version=glue_alpha.GlueVersion.V1_0,
                python_version=glue_alpha.PythonVersion.THREE_NINE,
                script=glue_alpha.Code.from_asset("assets/script.py"),
            ),
            description="Cleanup and Processing for AWS RSS Feed data",
            role=iam_role_glue
        )

        # glue trigger
        trigger = glue.CfnTrigger(self, "trigger",
            name="RssFeedProcessorGlueTrigger",
            type="EVENT",
            workflow_name=workflow.name,
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=job.job_name,
                    arguments={
                        "--bucket": f"{bucket_name}",
                        "--topic_arn": f"{sns_topic_arn}",
                        "--table": f"{table_name}",
                        "--database": f"{database_name}",
                    }
                )
            ]
        )

        # iam role for event bridge rule to trigger aws glue shell job
        iam_role_event_bridge = iam.Role(self, "RssFeedProcessorEventBridgeRuleRole",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
            role_name="RssFeedProcessorEventBridgeRole",
            description="Event bridge role to trigger Glue Workflow",
        )
        

        # event bridge rule to launch glue workflow via lambda trigger 
        rule = events.Rule(self, "RssFeedProcessorEventBridgeToGlueWorkflowRule",
            description="Start an AWS Glue workflow upon new file arrival in an Amazon S3 bucket",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {
                        "name": [bucket_name]
                        },
                    "object": {
                        "key": [{ "prefix": "landing" }]
                    }
                }
            ),
        )

        # lambda target for event bridge rule to trigger glue workflow
        lambda_target_role = iam.Role(self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ]
        )

        lambda_target_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "glue:StartWorkflowRun",
                ],
                resources=[
                    f"arn:aws:glue:{region}:{account_id}:workflow/{workflow.name}",
                ]
            )
        )

        lambda_target = _lambda.Function(self, "RssFeedProcessorLambdaTarget",
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=lambda_target_role,
            code=_lambda.Code.from_asset("lambda"),
            handler="lambda_function.lambda_handler",
            timeout=Duration.seconds(15),
            environment={
                'GLUE_WORKFLOW_NAME': workflow.name
            }
        )

        # add target to event bridge rule
        rule.add_target(targets.LambdaFunction(lambda_target))
         

        


        
        