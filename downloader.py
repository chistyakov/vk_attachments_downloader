from datetime import datetime
import os
import re
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import urlopen

from vk_wrapper.dialog import MEDIA_TYPE
from utils import timestamp_to_str, print_in_encoding_of_console

class EmptyURL(Exception):
    pass


class AttachmentsDownloader(object):
    VIDEO_DURATION_LIMIT = 20*60
    FAILED_DOWNLOADS_FILENAME = "!failed_downloads.txt"
    def __init__(self):
        self.current_filename = ""
        self.current_content = b""
        self._current_url = ""
        self.current_file_extension = ""
        self.current_file_date = 0
        self.subdirectory_to_save = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.create_subdirectory_to_save_files()
        self.list_of_failed_downloads = []
        self.current_media_type = None

    @property
    def current_url(self):
        return self._current_url

    @current_url.setter
    def current_url(self, value):
        self._current_url = value
        extension_from_filename = os.path.splitext(self.current_filename)[1]
        extension_from_url = os.path.splitext(urlparse(self.current_url).path)[1]
        if extension_from_url:
            self.current_file_extension = extension_from_url
        else:
            self.current_file_extension = extension_from_filename

    def create_subdirectory_to_save_files(self):
        if not os.path.exists(self.subdirectory_to_save):
            os.mkdir(self.subdirectory_to_save)
        print_in_encoding_of_console("файлы будут сохранены в подпапку {0}".format(self.subdirectory_to_save))

    def download_list(self, data_list, media_type):
        self.current_media_type = media_type
        if media_type == MEDIA_TYPE.video:
            self.download_video_list(data_list)
        else:
            self.download_not_video_list(data_list)
        self.save_failed_downloads()

    def download_video_list(self, data_list):
        for (self.current_filename, self.current_url, self.current_file_date, duration) in data_list:
            if duration < self.VIDEO_DURATION_LIMIT and self.current_file_extension == ".mp4":
                self.download_current_file()
            else:
                self.mark_current_file_as_fail("not mp4 or too big duration")

    def download_not_video_list(self, data_list):
        for (self.current_filename, self.current_url, self.current_file_date) in data_list:
            self.download_current_file()

    def download_current_file(self):
        try:
            self.request_current_file_content()
            self.write_current_file()
        except Exception as e:
            self.mark_current_file_as_fail(str(e))

    def request_current_file_content(self):
        if self.current_url:
            print_in_encoding_of_console("скачивание {0}".format(self.current_url))
            self.current_content = urlopen(self.current_url).read()
        else:
            raise EmptyURL()

    def write_current_file(self, postfix=0):
        new_filename = self.form_filepath(postfix)
        if os.path.exists(new_filename):
            self.write_current_file(postfix + 1)
        else:
            self.current_filename = new_filename
            print_in_encoding_of_console("сохранение в {0}".format(self.current_filename))
            with open(self.current_filename, 'wb') as f:
                f.write(self.current_content)

    def form_filepath(self, postfix):
        date_str = timestamp_to_str(self.current_file_date, r"%Y-%m-%d-%H-%M-%S")
        if not self.current_filename:
            filename = date_str
        else:
            filename = " - ".join((date_str, self.current_filename))

        filename = re.sub('[^\w\-_\. ]', '_', filename)
        filename = filename[:100]
        filename = os.path.splitext(filename)[0]
        if postfix:
            filename = "{0}-{1}{2}".format(filename, postfix, self.current_file_extension)
        else:
            filename = "{0}{1}".format(filename, self.current_file_extension)
        return os.path.join(self.subdirectory_to_save, filename)

    def mark_current_file_as_fail(self, reason_str):
        self.list_of_failed_downloads.append(
            (
                self.current_media_type,
                self.current_filename,
                self.current_url, reason_str
            )
        )

    def save_failed_downloads(self):
        if self.list_of_failed_downloads:
            list_of_failed_downloads_filepath = os.path.join(
                self.subdirectory_to_save, self.FAILED_DOWNLOADS_FILENAME)
            with open(list_of_failed_downloads_filepath, 'w', encoding="utf-8") as f:
                f.write("Список нескачанных файлов. Попробуйте скачать их вручную\n")
                f.write("тип - имя - url - причина\n")
                for fail in self.list_of_failed_downloads:
                    f.write("{0} - {1} - {2} - {3}\n".format(fail[0].name, fail[1], fail[2], fail[3]))
            print_in_encoding_of_console("список неудачных загрузок ({0} шт.) сохранен в файл {1}".format(
                len(self.list_of_failed_downloads),
                list_of_failed_downloads_filepath))

