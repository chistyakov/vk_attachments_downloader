import urllib.parse
from datetime import datetime


def timestamp_to_str(timestamp, str_format="%Y-%m-%d %H:%M:%S"):
    d = datetime.fromtimestamp(timestamp)
    datetime_str = d.strftime(str_format)
    return datetime_str


def encode_data_for_request(params, bin_format=True):
    urlencoded = urllib.parse.urlencode(params)
    if bin_format:
        return urlencoded.encode('utf-8', errors="ignore")
    else:
        return urlencoded
