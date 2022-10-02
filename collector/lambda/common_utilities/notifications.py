import boto3
from botocore.exceptions import ClientError

class SNSException(Exception):
    pass

def publish_sns_message(topic_arn, subject, message):
    sns = boto3.client('sns')
    try:
        sns.publish(TopicArn=topic_arn, Subject=subject, Message=message)
    except ClientError as e:
        raise SNSException(e)
    return True

