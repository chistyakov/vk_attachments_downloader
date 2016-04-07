from enum import Enum

from vk_wrapper.caller import call_api
import vk_wrapper.dialog_attachments as dialog_attachments
from utils import timestamp_to_str


class MEDIA_TYPE(Enum):
    photo = 1
    audio = 2
    doc = 3
    video = 4


class Dialog(object):
    LAST_MESSAGE_PREVIEW_LENGTH = 100
    @classmethod
    def get_dialogs(cls, token, offset, count):
        dialogs_json = call_api("messages.getDialogs",
                                [
                                    ("offset", offset),
                                    ("count", count),
                                    ("preview_length", cls.LAST_MESSAGE_PREVIEW_LENGTH)
                                ],
                                token)
        return [cls(dialog_item_json, token) for dialog_item_json in dialogs_json["items"]]

    def __init__(self, dialog_json, token):
        self.token = token
        self.message = dialog_json["message"]
        self.is_chat = "chat_id" in self.message

    def __str__(self):
        return self.form_dialog_description()

    def form_dialog_description(self):
        is_last_message_out = bool(self.message["out"])
        if is_last_message_out:
            author_name_case = "dat"
            preposition = ""
        else:
            author_name_case = "gen"
            preposition = " от"
        message_author = self.get_message_author_name(author_name_case)
        datetime_str = timestamp_to_str(self.message["date"])
        last_message_str = "Последнее сообщение{0} {1}:".format(preposition, message_author)
        ps = self.form_last_message_postscriptum()
        description_str = "{0}\n{1} ({2})\n{3}{4}".format(
            self.message["title"],
            last_message_str,
            datetime_str,
            self.message["body"],
            ps)
        return description_str

    def form_last_message_postscriptum(self):
        post_scriptum = ""
        if self.message["body"]:
            post_scriptum += "\n"
        if "attachments" in self.message:
            post_scriptum += "..прикреплен материал\n"
        if "emoji" in self.message:
            post_scriptum += "..вставлен смайлик emoji\n"
        if "fwd_messages" in self.message:
            post_scriptum += "..прикреплено другое сообщение\n"
        return post_scriptum


    def get_message_author_name(self, name_case):
        return self.request_name(self.message["user_id"], name_case)

    def request_name(self, user_id, name_case):
        author_json = call_api("users.get", [("user_ids", user_id), ("name_case", name_case)])[0]
        author_str = "{0} {1}".format(
            author_json["first_name"],
            author_json["last_name"])
        return author_str

    def get_history_attachments(self, media_type, opener=None):
        attachments_fetcher = dialog_attachments.DialogHistoryAttachementsFetcher(self, media_type)
        return attachments_fetcher.get_attachments(opener)

    @property
    def str_id(self):
        if self.is_chat:
            return "c{0}".format(self.message["chat_id"])
        else:
            return str(self.message["user_id"])
