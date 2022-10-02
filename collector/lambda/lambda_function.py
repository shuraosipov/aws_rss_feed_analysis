import os
import sys
import logging
import json
import pandas as pd
import feedparser
from common_utilities.date_helpers import generate_start_date, string_to_date, date_to_string
from common_utilities.upload import upload_to_s3
from common_utilities.notifications import publish_sns_message


def check_new_entries_exist(feed, start_time):
    feed_update_time = string_to_date(feed.feed['updated'])
    check_if_feed_was_updated_recently(start_time, feed_update_time)

def check_if_feed_was_updated_recently(start_time, update_time):
    if update_time > start_time:
        print(f"New entries found! Feed was updated on {update_time}")
    else:
        print(f"No new entries since {date_to_string(start_time)}")
        sys.exit(123)

def convert_feed_to_dataframe(feed, start_time) -> pd.DataFrame:
    df = feedparser_to_dataframe(feed)
    df = filter_old_entries(df, start_time)
    return df

def filter_old_entries(df, start_time) -> pd.DataFrame:
    return df[df['published'].apply(string_to_date) > start_time]

def feedparser_to_dataframe(feed) -> pd.DataFrame:
    df = pd.DataFrame()
    df['id'] = [entry.id for entry in feed.entries]
    df['category'] = [entry['category'] for entry in feed['entries']]
    df['title'] = [entry['title'] for entry in feed['entries']]
    df['link'] = [entry['link'] for entry in feed['entries']]
    df['published'] = [entry['published'] for entry in feed['entries']]
    df['summary'] = [entry['summary'] for entry in feed['entries']]
    return df

def generate_table(feed, days_range) -> pd.DataFrame:   
    start_time = generate_start_date(days_range)
    
    check_new_entries_exist(feed, start_time)
    return convert_feed_to_dataframe(feed, start_time)


def lambda_handler(event, context):
    
    BUCKET_NAME = os.environ['BUCKET_NAME']
    DAYS_RANGE = int(os.environ['DAYS_RANGE'])
    FEED_URL = os.environ['FEED_URL']
    SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

    try:
        feed = feedparser.parse(FEED_URL)
        df = generate_table(feed, DAYS_RANGE)
        s3_uri = upload_to_s3(BUCKET_NAME, df)
        
        publish_sns_message(
            topic_arn=SNS_TOPIC_ARN, 
            subject="RSS Feed Collector. New entries found!",
            message=f"""There are {df.shape[0]} new entries. 
            S3 URI: {s3_uri}"""
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Feed successfully uploaded to S3! New entries added {df.shape[0]}')
        }
    except Exception as e:
        logging.error(e)
        raise e