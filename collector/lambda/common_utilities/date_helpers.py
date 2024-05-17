from datetime import datetime, timedelta

def current_date():
    return datetime.now().replace(
        microsecond=0
    ).isoformat()

def generate_start_date(days_range) -> datetime:
    """ This function creates a datetime object in the past by subtracting number of days from now. """
    result = (datetime.utcnow() - timedelta(days=days_range)).strftime("%a, %d %b %Y 00:00:05 GMT")
    return string_to_date(result)

def string_to_date(string):
    """ This function converts a string representation of date to the datetime object """
    return datetime.strptime(string, "%a, %d %b %Y %H:%M:%S %Z")

def date_to_string(datetime_obj):
    """ This function converts datetime object to a string """
    return datetime_obj.strftime("%a, %d %b %Y %H:%M:%S")