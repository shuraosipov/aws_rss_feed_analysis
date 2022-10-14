# Set up logging
import json
import os
import logging
import boto3


# init client
glue_client = boto3.client('glue')

# configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# load environment variables
glue_workflow_name = os.environ['GLUE_WORKFLOW_NAME']

def start_glue_workflow(workflow_name):
    response = glue_client.start_workflow_run(Name=workflow_name)
    print(response)

def lambda_handler(event, context):
    logger.info('## INITIATED BY EVENT: ')
    logger.info(event['detail'])
    try:
        response = glue_client.start_workflow_run(Name = glue_workflow_name)
        logger.info('## STARTED GLUE WORKFLOW: ' + glue_workflow_name)
        logger.info('## GLUE WORKFLOW RUN ID: ' + response['RunId'])
        return response
    except glue_client.exceptions.ConcurrentRunsExceededException as e:
        logger.error(e)
        pass
    