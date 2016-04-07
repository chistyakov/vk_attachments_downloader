from datetime import datetime
import urllib.parse
import sys


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

def print_in_encoding_of_console(*objects, sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)
