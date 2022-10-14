import sys
import pandas as pd
import boto3
import pyathena
import re
from botocore.exceptions import ClientError
import logging

def read_file_from_s3(bucket, key):
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    return pd.read_csv(obj.get()['Body'])





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



def read_file_from_s3(bucket, table):
    """ use pyathena to query data from S3, and save results to a pandas dataframe"""
    conn = pyathena.connect(s3_staging_dir=f's3://{bucket}/athena_output/', region_name='us-east-1') 
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
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

if __name__ == "__main__":
    bucket = 'shuraosipov-rss-feed-analysis'

    df = read_file_from_s3(bucket, table='aws_feed_landing')

    df = cleanup_data(df)

    df = enrich_data(df)

    df = explode(df)

    save_df_to_s3(bucket, df, 'processed/feed_2.csv')

    print('Done')
    #print(df.head())


    # send email with the link to the result


