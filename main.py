#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import getpass
from urllib.error import URLError
import sys
import traceback

from vk_wrapper.dialog import MEDIA_TYPE
from vk_wrapper.auth import auth
from dialog_chooser import DialogChooser
from downloader import AttachmentsDownloader
from utils import print_in_encoding_of_console, input_with_prompt_on_encoding_of_console

VK_APPLICATION_ID = 5345641
AUTH_RIGHTS = "messages,video"

def call_main_with_prompt_on_exit():
    try:
        main()
    except Exception as e:
        print_in_encoding_of_console(e)
        print_in_encoding_of_console(traceback.format_exc())
        input()


def main():
    print_in_encoding_of_console("Привет, Сандар!")
    print_in_encoding_of_console("Программа для скачивания материалов из бесед и диалогов ВК")
    print_in_encoding_of_console("Введите данные для логина")
    email = input_with_prompt_on_encoding_of_console("Email: ")
    password = getpass.getpass()
    token, opener = login(email, password)

    dialog = choose_dialog(token)

    downloader = AttachmentsDownloader()

    for media_type in MEDIA_TYPE:
        print_in_encoding_of_console("Загрузка {0}".format(media_type.name))
        data_list = dialog.get_history_attachments(media_type, opener)
        if not data_list:
            print_in_encoding_of_console("{0} в диалоге нет".format(media_type.name))
        downloader.download_list(data_list, media_type)


def login(email, password):
    try:
        token, user_id, opener = auth(email, password, VK_APPLICATION_ID, AUTH_RIGHTS)
    except URLError:
        print_in_encoding_of_console("=" * 40)
        print_in_encoding_of_console("проверьте подключение к интернету")
        raise
    return token, opener

def choose_dialog(token):
    try:
        dialog = DialogChooser(token).choose_dialog()
    except StopIteration:
        print_in_encoding_of_console("Выход")
        sys.exit()
    return dialog



if __name__ == "__main__":
    call_main_with_prompt_on_exit()
