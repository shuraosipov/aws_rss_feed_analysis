import logging
import boto3
from botocore.exceptions import ClientError
from common_utilities.date_helpers import current_date

def upload_to_s3(bucket_name, df, object_name=None):
    """ This function publishes a dataframe to S3 bucket """
    s3 = boto3.resource('s3')

    if object_name is None:
        object_name = f"{current_date()}_feed.csv"

    try:
        s3.Object(bucket_name, object_name).put(Body=df.to_csv(index=False))
    except ClientError as e:
        logging.error(e)
        return False
    return True