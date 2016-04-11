#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import http.cookiejar
import urllib.request
import urllib
from urllib.parse import urlparse
from html.parser import HTMLParser

from utils import encode_data_for_request, input_with_prompt_on_encoding_of_console


class FormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = "GET"

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "form":
            if self.form_parsed:
                raise RuntimeError("Second form on page")
            if self.in_form:
                raise RuntimeError("Already in form")
            self.in_form = True
        if not self.in_form:
            return
        attrs = dict((name.lower(), value) for name, value in attrs)
        if tag == "form":
            self.url = attrs["action"]
            if "method" in attrs:
                self.method = attrs["method"].upper()
        elif tag == "input" and "type" in attrs and "name" in attrs:
            if attrs["type"] in ["hidden", "text", "password"]:
                self.params[attrs["name"]] = attrs["value"] if "value" in attrs else ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "form":
            if not self.in_form:
                raise RuntimeError("Unexpected end of <form>")
            self.in_form = False
            self.form_parsed = True

    @property
    def encoded_params(self):
        return encode_data_for_request(self.params)


class WrongCredentialsChecker(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.service_msg_warning_on_page = False
        self.current_tag_is_service_msg_warning = False
        self.service_msg_warning_text = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag_is_service_msg_warning = False
        if tag == "div":
            if attrs and attrs[0][1] == 'service_msg service_msg_warning':
                self.service_msg_warning_on_page = True
                self.current_tag_is_service_msg_warning = True

    def handle_data(self, data):
        if self.current_tag_is_service_msg_warning:
            self.service_msg_warning_text = data

    def handle_endtag(self, tag):
        self.current_tag_is_service_msg_warning = False


def auth(email, password, client_id, scope):
    def split_key_value(kv_pair):
        kv = kv_pair.split("=")
        return kv[0], kv[1]

    # Authorization form
    def auth_user(email, password, client_id, scope, opener):
        response = opener.open(
            "http://oauth.vk.com/oauth/authorize?" + \
            "redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
            "client_id=%s&scope=%s&display=wap" % (client_id, ",".join(scope))
            )
        doc = str(response.read())
        parser = FormParser()
        parser.feed(doc)
        parser.close()
        if not parser.form_parsed or parser.url is None or "pass" not in parser.params or \
            "email" not in parser.params:
            raise RuntimeError("Something wrong")
        parser.params["email"] = email
        parser.params["pass"] = password
        if parser.method == "POST":
            response = opener.open(parser.url, parser.encoded_params)
        else:
            raise NotImplementedError("Method '%s'" % parser.method)
        return response.read().decode("utf-8", errors="ignore"), response.geturl()

    #2nd step of authentification
    def sms_code(doc, opener):
        parser = FormParser()
        parser.feed(doc)
        parser.close()
        parser.params["code"] = input_with_prompt_on_encoding_of_console("Type code from SMS: ")
        if parser.method == "POST":
            response = opener.open("https://m.vk.com" + parser.url, parser.encoded_params)
        else:
            raise NotImplementedError("Method '%s'" % parser.method)
        return response.read().decode("utf-8", errors="ignore"), response.geturl()

    # Permission request form
    def give_access(doc, opener):
        parser = FormParser()
        parser.feed(doc)
        parser.close()
        if not parser.form_parsed or parser.url is None:
            raise RuntimeError("Something wrong")
        if parser.method == "POST":
            response = opener.open(parser.url, parser.encoded_params)
        else:
            raise NotImplementedError("Method '%s'" % parser.method)
        return response.read().decode("utf-8", errors="ignore"), response.geturl()

    def check_wrong_credentials(doc):
        parser = WrongCredentialsChecker()
        parser.feed(doc)
        parser.close()
        return parser.service_msg_warning_on_page, parser.service_msg_warning_text


    if not isinstance(scope, list):
        scope = [scope]
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPRedirectHandler())
    doc, url = auth_user(email, password, client_id, scope, opener)
    if "/login" in urlparse(url).path:
        doc, url = sms_code(doc, opener)
    if urlparse(url).path != "/blank.html":
        wrong_creds, warning_message = check_wrong_credentials(doc)
        if wrong_creds:
            raise RuntimeError(warning_message)
        else:
            # Need to give access to requested scope
            doc, url = give_access(doc, opener)
    if urlparse(url).path != "/blank.html":
        raise RuntimeError("Expected success here. Maybe capture was shown?\n{0}".format(doc))
    answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
    if "access_token" not in answer or "user_id" not in answer:
        raise RuntimeError("Missing some values in answer")
    return answer["access_token"], answer["user_id"], opener

