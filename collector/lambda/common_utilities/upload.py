import logging
import boto3
from botocore.exceptions import ClientError
from common_utilities.date_helpers import current_date

class S3UploadException(Exception):
    pass

def upload_to_s3(bucket_name, df, object_name) -> str:
    """ This function publishes a dataframe to S3 bucket """
    s3 = boto3.resource('s3')

    try:
        s3.Object(bucket_name, object_name).put(Body=df.to_csv(index=False, sep=';'))
    except ClientError as e:
        logging.error(e)
        raise S3UploadException(e)
    
    s3_uri = f"s3://{bucket_name}/{object_name}"
    return s3_uri