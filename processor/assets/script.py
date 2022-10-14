from ast import arg
import sys
import re
import logging
from datetime import datetime
import boto3
import pyathena
import pandas as pd
from botocore.exceptions import ClientError
from awsglue.utils import getResolvedOptions


def current_date():
    return datetime.now().replace(
        microsecond=0
    ).isoformat()

def extract_product_names(string) -> str:
    """
    This function extracts a product name from a string.
    The product name is assumed to be everything after 'general:products/' and before the next comma or end of the string.
    If there is no product name in the string, the empty string is returned.
    """
    products = re.findall(r'general:products/(.*?)(?:,|$)', string)
    return " ".join(products)


def extract_category_names(string) -> str:
    """
    This function extracts a category name from a string.
    The category is assumed to be everything after 'marketing:*/' and before the next comma or end of the string.
    If there is no category name in the string, the empty string is returned.
    """
    categories = re.findall(r'marketing:.*?/(.*?)(?:,|$)', string)
    return " ".join(categories)


def read_file_from_s3(bucket, database, table):
    """ use pyathena to query data from S3, and save results to a pandas dataframe"""
    conn = pyathena.connect(s3_staging_dir=f's3://{bucket}/athena_output/', region_name='us-east-1') 
    df = pd.read_sql(f"SELECT * FROM {database}.{table}", conn)
    return df

def cleanup_data(df):
    # drop rows with NaN values
    df = df.dropna()
    # remove spaces from the beginning and end of the string in the 'services' column
    df['services'] = df['services'].str.strip()
    #print(df['services'])
    return df

# enrich dataframe with new columns
def enrich_data(df):
    # extract product names from the 'services' column
    df['product'] = df['services'].apply(extract_product_names)
    # extract category names from the 'services' column
    df['category'] = df['services'].apply(extract_category_names)
    return df

# split cell into multiple rows based on the space separator
def explode(df):
    # explode the 'product' column
    df = df.assign(product=df['product'].str.split(' ')).explode('product')
    # explode the 'category' column
    df = df.assign(category=df['category'].str.split(' ')).explode('category')
    return df

# save dataframe to s3 as a csv file
def save_df_to_s3(bucket_name, df, object_name=None) -> str:
    s3 = boto3.resource('s3')

    try:
        s3.Object(bucket_name, object_name).put(
            Body=df.to_csv(
                index=False, 
                sep=';', 
                columns=['id','date', 'product', 'category', 'link', 'title', 'description']
            )
        )
    except ClientError as e:
        logging.error(e)
        raise e
    
    s3_uri = f"s3://{bucket_name}/{object_name}"
    return s3_uri

def send_sns_message(topic_arn, s3_uri):
    sns = boto3.client('sns')

    try:
        response = sns.publish(
            TopicArn=topic_arn,
            Message=f"""New data has been processed and saved to {s3_uri}.""",
            Subject='RSS Feed Data Processing Notification'
        )
        return response
    except ClientError as e:
        logging.error(e)
        raise e

if __name__ == "__main__":

    args = getResolvedOptions(sys.argv, ['bucket','topic_arn','table', 'database'])
    
    bucket = args['bucket']
    topic_arn = args['topic_arn']
    table = args['table']
    database = args['database']

    df = read_file_from_s3(bucket, database, table)

    df = cleanup_data(df)

    df = enrich_data(df)

    df = explode(df)

    s3_uri = save_df_to_s3(bucket, df, f'processed/report_{current_date()}.csv')

    send_sns_message(topic_arn, s3_uri)

    print('Done')
    


