from urllib.error import URLError
import re

import vk_wrapper.dialog
from vk_wrapper.caller import call_api
from utils import encode_data_for_request, print_in_encoding_of_console


class VideoNotFoundException(Exception):
    pass


class DialogHistoryAttachementsFetcher(object):
    def __init__(self, dialog, media_type):
        self.dialog = dialog
        self.token = self.dialog.token
        self.peer_id = self.form_peer_id()
        self.single_request_size = 200
        self.attachments = []
        post_process_func_dict = {
            vk_wrapper.dialog.MEDIA_TYPE.photo: self.photo_json_post_processing,
            vk_wrapper.dialog.MEDIA_TYPE.video: self.video_json_post_processing,
            vk_wrapper.dialog.MEDIA_TYPE.audio: self.audio_json_post_processing,
            vk_wrapper.dialog.MEDIA_TYPE.doc: self.doc_json_post_processing,
        }
        self.media_type = media_type
        self.postprocess_func = post_process_func_dict[self.media_type]
        self.video_parsed_download_urls = {}

    def form_peer_id(self):
        if self.dialog.is_chat:
            return self.dialog.message["chat_id"] + 2000000000
        else:
            return self.dialog.message["user_id"]

    def get_attachments(self, opener=None):
        if self.media_type == vk_wrapper.dialog.MEDIA_TYPE.video:
            self.get_video_download_links(opener)
        first_subset_json = self._request_subset_of_attachments(None)
        next_from = first_subset_json.get("next_from")
        self.add_attachemets_to_list(first_subset_json["items"])
        while next_from:
            subset_json = self._request_subset_of_attachments(next_from)
            next_from = subset_json.get("next_from")
            self.add_attachemets_to_list(subset_json["items"])
        return self.attachments

    def get_video_download_links(self, opener):
        print_in_encoding_of_console("получение прямых ссылок на видео через парсинг html")
        try:
            video_attachments_parser = VideoAttachmentsParser(
                self.dialog, opener)
            self.video_parsed_download_urls = video_attachments_parser.get_download_urls()
        except (URLError, FailToExtractDirectVideoLinks) as e:
            print_in_encoding_of_console("произошла ошибка при попытке получения прямых ссылок на видео\n{0}".format(e))

    def _request_subset_of_attachments(self, start_from):
        params = [
            ("peer_id", self.peer_id),
            ("media_type", self.media_type.name),
            ("count", self.single_request_size)
            ]
        if start_from:
            params.append(("start_from", start_from))
        return call_api("messages.getHistoryAttachments", params, self.token)

    def add_attachemets_to_list(self, new_subset):
        self.attachments += [self.postprocess_func(item) for item in new_subset]

    def photo_json_post_processing(self, item_json):
        photo_json = item_json['photo']
        url = self.choose_photo_url_with_max_size(photo_json)
        text = photo_json.get('text')
        date = photo_json['date']
        return (text, url, date)

    def choose_photo_url_with_max_size(self, photo_json):
        sizes = []
        for key in photo_json:
            m = re.search(r"photo_(\d*)", key)
            if m:
                sizes.append(int(m.groups()[0]))
        max_size = max(sizes)
        return photo_json["photo_{0}".format(max_size)]

    def video_json_post_processing(self, item_json):
        video_json = item_json['video']
        owner_id = video_json['owner_id']
        video_id = video_json['id']
        access_key = video_json['access_key']
        date = video_json['date']
        title = video_json["title"]
        duration = video_json["duration"]
        download_url = self.get_video_download_url(owner_id, video_id, access_key)

        return (title, download_url, date, duration)

    def get_video_download_url(self, owner_id, video_id, access_key):
        video_page_url = r"http://vk.com/video{0}_{1}".format(owner_id, video_id)
        for video_parsed_page_url in self.video_parsed_download_urls:
            if video_parsed_page_url.startswith(video_page_url):
                return self.video_parsed_download_urls[video_parsed_page_url]
        try:
            video_data_json = self.get_video_info(owner_id, video_id, access_key)
        except VideoNotFoundException:
            return "Not found"
        return video_data_json["player"]

    def get_video_info(self, owner_id, video_id, access_key):
        video_id_str = "_".join(str(x) for x in (owner_id, video_id, access_key))
        video = call_api("video.get", [("videos", video_id_str)], self.token)
        if video["count"]:
            return video["items"][0]
        else:
            raise VideoNotFoundException()

    def audio_json_post_processing(self, item_json):
        audio_json = item_json['audio']
        url = audio_json['url']
        name = " - ".join((audio_json.get('artist'), audio_json.get('title')))
        date = audio_json['date']
        return (name, url, date)

    def doc_json_post_processing(self, item_json):
        doc_json = item_json['doc']
        url = doc_json['url']
        name = doc_json['title']
        date = doc_json['date']
        return (name, url, date)


class FailToExtractDirectVideoLinks(Exception):
    pass


class VideoAttachmentsParser(object):
    def __init__(self, dialog, opener):
        self.dialog = dialog
        self.opener = opener
        """
        self.opener.addheaders = [
            ("X-Requested-With", "XMLHttpRequest"),
            ("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36"),
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Accept", "*/*"),
            ("Referer", "http://vk.com/im?sel=c31&w=historyc31_video"),
            #("Accept-Encoding", "gzip, deflate"),
            ("Accept-Language", "ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4")
        ]
        """
        self.count = 10000
        self.offset = 0
        self.request_data = {
            "act": "show",
            "al": 1,
            "loc": "im",
            "w": "history{0}_video".format(self.dialog.str_id),
            "offset": self.offset,
            "part": 1,
        }

    def get_download_urls(self):
        download_urls = {}
        video_page_url_list = self.get_video_pages_list()
        for video_page_url in video_page_url_list:
            video_html_str = self.get_video_page_html(video_page_url)
            mp4_urls = self.extract_mp4_urls(video_html_str)
            if mp4_urls:
                download_urls[video_page_url] = mp4_urls[max(mp4_urls)]
        return download_urls

    def get_video_pages_list(self):
        video_page_url_list = []
        while self.count > self.offset:
            video_page_url_list.extend(self.get_video_pages_subset())
        return video_page_url_list

    def get_video_pages_subset(self):
        videos_list_url = "http://vk.com/wkview.php"
        self.request_data['offset'] = self.offset
        encoded_data = encode_data_for_request(self.request_data)
        response = self.opener.open(videos_list_url, encoded_data)
        if response.getcode() == 200:
            self.videos_list_html = str(response.read())

            self.count = self.extract_count()
            self.offset = self.extract_offset()
            return self.extract_video_page_links()
        else:
            self.count = 0
            return []

    def extract_video_page_links(self):
        relative_video_links = re.findall('a href=\"(.*?)\"', self.videos_list_html)
        return ["http://vk.com{0}".format(r_link) for r_link in relative_video_links]

    def get_video_page_html(self, video_url):
        return str(self.opener.open(video_url).read())

    def extract_mp4_urls(self, video_html_str):
        overescaped_urls_tuples = re.findall(r'(https:\\*?/\\*?/cs\d+\.vk\.me\\*?(?:/\d+)?\\*?/\w\d+\\*?/videos\\*?/\w+?\.(\d+)\.mp4)', video_html_str)
        return {int(size):self.unescape_mp4_url(url) for (url, size) in overescaped_urls_tuples}

    def unescape_mp4_url(self, overescaped_url):
        return re.sub(r"\\*/", r"/", overescaped_url)

    def extract_count(self):
        count_regexp = r'\"count\":(?:\")?(\d+)(?:\")?'
        m = re.search(count_regexp, self.videos_list_html)
        if m:
            return int(m.group(1))
        else:
            raise FailToExtractDirectVideoLinks('no "count" on the fetched page\n{0}'.format(
                self.videos_list_html))

    def extract_offset(self):
        offset_regexp = r'\"offset\":(\d+)'
        m = re.search(offset_regexp, self.videos_list_html)
        if m:
            return int(m.group(1))
        else:
            raise FailToExtractDirectVideoLinks('no "offset" on the fetched page\n{0}'.format(
                self.videos_list_html))
