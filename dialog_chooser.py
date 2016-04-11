from vk_wrapper.dialog import Dialog
from utils import print_in_encoding_of_console, input_with_prompt_on_encoding_of_console


class DialogChooser(object):
    def __init__(self, token):
        self.token = token
        self.choice = -1
        self.offset = 0
        self.count_to_get = 5
        self.shown_dialogs = []

    def choose_dialog(self):
        self.print_greating()
        while self.choice == -1:
            self.show_next_dialogs()
            self.ask_number()
        return self.shown_dialogs[self.choice]

    def print_greating(self):
        print_in_encoding_of_console("=" * 40)
        print_in_encoding_of_console("Последние беседы и диалоги:")

    def show_next_dialogs(self):
        subset_of_dialogs = self.get_next_subset_of_dialogs()
        for num, dialog in enumerate(subset_of_dialogs):
            print_in_encoding_of_console("{0}) {1}\n".format(self.offset + num + 1, dialog))
        self.shown_dialogs += subset_of_dialogs
        self.offset += self.count_to_get

    def get_next_subset_of_dialogs(self):
        return Dialog.get_dialogs(self.token, self.offset, self.count_to_get)

    def ask_number(self):
        while self.choice not in range(len(self.shown_dialogs)):
            inputed_str = input_with_prompt_on_encoding_of_console(
                "Выберите номер диалога ('n' --- загрузка следующих "
                "{0} диалогов, 'q' --- выход): ".format(
                    self.count_to_get))
            if inputed_str == "q":
                raise StopIteration
            if inputed_str == "n":
                self.choice = -1
                break
            if not inputed_str.isdigit():
                continue
            self.choice = int(inputed_str) - 1


