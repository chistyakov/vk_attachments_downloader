import time
import json
from urllib.request import urlopen

from utils import encode_data_for_request


class VKAPIError(Exception):
    pass


def call_api(method, params, token=None, delay_sec=0):
    time.sleep(delay_sec)
    params.append(("v", "5.46"))
    if token:
        params.append(("access_token", token))
    url = "https://api.vk.com/method/{0}?{1}".format(
        method, encode_data_for_request(params, False))
    response = urlopen(url)
    response_str = response.read().decode("utf-8", errors="ignore")
    response_json = json.loads(response_str)
    if "error" in response_json:
        error_json = response_json["error"]
        if error_json["error_code"] == 6:
            return call_api(method, params, token, delay_sec+2)
        else:
            raise VKAPIError(error_json)
    else:
        return response_json["response"]
