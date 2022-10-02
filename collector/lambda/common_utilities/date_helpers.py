from datetime import datetime, timedelta

def current_date():
    return datetime.now().replace(
        microsecond=0
    ).isoformat()

def generate_start_date(range) -> datetime:
    """ This function creates a datetime object in the past by substracting number of days from now. """
    result = (datetime.now() - timedelta(days=range)).strftime("%a, %d %b %Y 00:00:05 %z +0000")
    return string_to_date(result)

def string_to_date(string):
    """ This function converts a string representation of date to the datetime object """
    return datetime.strptime(string, "%a, %d %b %Y %H:%M:%S %z")

def date_to_string(datetime_obj):
    """ This function converts datetime object to a string """
    return datetime_obj.strftime("%a, %d %b %Y %H:%M:%S")