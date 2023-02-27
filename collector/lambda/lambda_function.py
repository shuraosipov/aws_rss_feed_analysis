import os
import sys
import logging
import pandas as pd
import feedparser
from datetime import datetime
from typing import Optional

from common_utilities.date_helpers import (
    generate_start_date,
    string_to_date,
    date_to_string,
    current_date,
)
from common_utilities.upload import upload_to_s3
from common_utilities.notifications import publish_sns_message


class NoNewEntriesError(Exception):
    pass


# custom type alias for better readability
FeedDict = feedparser.FeedParserDict


def check_new_entries(feed: FeedDict, start_time: datetime) -> Optional[str]:
    feed_update_time = string_to_date(feed.feed["updated"])
    try:
        check_if_feed_updated(start_time, feed_update_time)
    except NoNewEntriesError as e:
        print(f"Error: {e}")
        sys.exit(123)


def check_if_feed_updated(start_time: datetime, update_time: datetime) -> Optional[str]:
    if update_time > start_time:
        print(f"New entries found! Feed was updated on {update_time}")
    else:
        print(f"No new entries since {date_to_string(start_time)}")
        raise NoNewEntriesError("No new entries found in feed")


def feed_to_dataframe(feed: FeedDict, start_time: datetime) -> pd.DataFrame:
    entries = feed.entries
    data = {
        "id": [entry.id for entry in entries],
        "category": [entry["tags"] for entry in entries],
        "title": [entry["title"] for entry in entries],
        "link": [entry["link"] for entry in entries],
        "published": [entry["published"] for entry in entries],
        "summary": [entry["summary"] for entry in entries],
    }

    df = pd.DataFrame(data)

    # filter out old entries
    df = df[df["published"].apply(string_to_date) > start_time]

    return df


def generate_table(feed: FeedDict, days_range: int) -> pd.DataFrame:
    start_time = generate_start_date(days_range)

    check_new_entries(feed, start_time)
    return feed_to_dataframe(feed, start_time)


def get_feed_data(url: str) -> FeedDict:
    feed = feedparser.parse(url)
    return feed


def lambda_handler(event, context):
    try:
        # Get environment variables
        feed_url = os.environ.get("FEED_URL")
        bucket_name = os.environ.get("BUCKET_NAME")
        days_range = int(os.environ.get("DAYS_RANGE"))
        sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")

        # Get feed data and generate DataFrame
        feed = get_feed_data(feed_url)
        df = generate_table(feed, days_range)

        # Upload to S3
        s3_uri = upload_to_s3(
            bucket_name, df, object_name=f"landing/{current_date()}_feed.csv"
        )

        # Publish SNS message
        message = f"There are {df.shape[0]} new entries. S3 URI: {s3_uri}"
        publish_sns_message(
            topic_arn=sns_topic_arn,
            subject="RSS Feed Collector. New entries found!",
            message=message,
        )

        # Return success response
        return {
            "statusCode": 200,
            "body": f"Feed successfully uploaded to S3! New entries added {df.shape[0]}",
        }
    except Exception as e:
        # Log error and publish SNS message
        logging.error(e)
        publish_sns_message(
            topic_arn=sns_topic_arn,
            subject="RSS Feed Collector. Exception!",
            message=f"Exception occurred: {e}",
        )
        raise e
