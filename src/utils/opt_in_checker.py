# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import json
import os
import time
from enum import Enum
from platform import system
from sys import stdin

from .input_with_timeout import input_with_timeout


class CFCheckResult(Enum):
    DECLINED = 0
    ACCEPTED = 1
    NO_FILE = 2


class DialogResult(Enum):
    DECLINED = 0
    ACCEPTED = 1
    TIMEOUT_REACHED = 2


class OptInChecker:
    dialog_timeout = 25  # seconds
    asking_period = 14  # days
    path_to_opt_in_out_script = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                             "opt_in_out.py")
    opt_in_question = "Intel collects technical Information about your software installation statistics, " \
                      "and development environment to improve product and developer experience.  " \
                      "Intel may retain Information as long as necessary to support our products.  " \
                      "You can revoke your consent at any time by running {}. DO YOU ACCEPT? " \
                      "(\"Y\" if you consent to the collection of your information or \"N\" if you do NOT " \
                      "consent to the collection of your information)".format(path_to_opt_in_out_script)
    opt_in_question_incorrect_input = """DO YOU ACCEPT? ("Y" if you consent to the collection of your information 
    or "N" if you do NOT consent to the collection of your information)"""

    @staticmethod
    def _ask_opt_in(question: str, timeout: int):
        """
        Runs input with timeout and checks user input.
        :param question: question that will be printed on the screen.
        :param timeout: timeout to wait.
        :return: opt-in dialog result.
        """
        print(question)
        answer = input_with_timeout(prompt='>>', timeout=timeout)
        answer = answer.lower()
        if answer == "n" or answer == "no":
            return DialogResult.DECLINED
        if answer == "y" or answer == "yes":
            return DialogResult.ACCEPTED
        return DialogResult.TIMEOUT_REACHED

    def opt_in_dialog(self):
        """
        Runs opt-in dialog until the timeout is expired.
        :return: opt-in dialog result.
        """
        start_time = time.time()
        answer = self._ask_opt_in(self.opt_in_question, self.dialog_timeout)
        time_passed = time.time() - start_time
        while time_passed < self.dialog_timeout and answer == DialogResult.TIMEOUT_REACHED:
            answer = self._ask_opt_in(self.opt_in_question_incorrect_input, self.dialog_timeout - time_passed)
            time_passed = time.time() - start_time
        return answer

    @staticmethod
    def control_file_base_dir():
        """
        Returns the base directory of the control file.
        :return: base directory of the control file.
        """
        platform = system()

        dir_to_check = None

        if platform == 'Windows':
            dir_to_check = '$LOCALAPPDATA'
        elif platform in ['Linux', 'Darwin']:
            dir_to_check = '$HOME'

        if dir_to_check is None:
            raise Exception('Failed to find location of the control file.')

        return os.path.expandvars(dir_to_check)

    @staticmethod
    def control_file_subdirectory():
        """
        Returns control file subdirectory.
        :return: control file subdirectory.
        """
        platform = system()
        if platform == 'Windows':
            return 'Intel Corporation'
        elif platform in ['Linux', 'Darwin']:
            return 'intel'
        raise Exception('Failed to find location of the control file.')

    def control_file(self):
        """
        Returns the control file path.
        :return: control file path.
        """
        return os.path.join(self.control_file_base_dir(), self.control_file_subdirectory(), "openvino_telemetry.json")

    def create_new_cf_file(self):
        """
        Creates a new control file.
        :return: True if the file is created successfully, otherwise False
        """
        if not self.create_or_check_cf_dir():
            return False
        try:
            open(self.control_file(), 'w').close()
        except Exception:
            return False
        return True

    def create_or_check_cf_dir(self):
        """
        Creates control file directory and checks if the directory is writable.
        :return: True if the directory is created and writable, otherwise False
        """
        cf_dir = os.path.join(self.control_file_base_dir(), self.control_file_subdirectory())
        if not os.path.isdir(cf_dir):
            if not os.access(cf_dir, os.W_OK):
                print("Failed to update opt-in status. "
                      "Cannot create a file when that file already exists: {}".format(cf_dir))
                return
            os.remove(cf_dir)
        if not os.path.exists(cf_dir):
            if not os.access(self.control_file_base_dir(), os.W_OK):
                print("Failed to update opt-in status. "
                      "Please allow write access to the following directory: {}".format(self.control_file_base_dir()))
                return False
            os.mkdir(cf_dir)
        if not os.access(cf_dir, os.W_OK):
            print("Failed to update opt-in status. "
                  "Please allow write access to the following directory: {}".format(cf_dir))
            return False
        return True

    def update_result(self, result: CFCheckResult):
        """
        Updates the 'opt_in' value in the control file.
        :param result: opt-in dialog result.
        :return: False if the control file is not writable, otherwise True
        """
        if not os.path.exists(self.control_file()):
            if not self.create_new_cf_file():
                return False
        if not os.access(self.control_file(), os.W_OK):
            print("Failed to update opt-in status. "
                  "Please allow write access to the following file: {}".format(self.control_file()))
            return False
        try:
            with open(self.control_file(), 'w') as file:
                if result == CFCheckResult.ACCEPTED:
                    content = {'opt_in': 1}
                else:
                    content = {'opt_in': 0}
                json.dump(content, file)
        except Exception:
            return False
        return True

    def cf_is_empty(self):
        """
        Checks if the control file is empty.
        :return: True if control file is empty, otherwise False.
        """
        if os.stat(self.control_file()).st_size == 0:
            return True
        _, content = self.get_info_from_cf()
        return 'opt_in' not in content

    def get_info_from_cf(self):
        """
        Gets information from control file.
        :return: the tuple, where the first element is True if the file is read successfully, otherwise False
        and the second element is the content of the control file.
        """
        if not os.access(self.control_file(), os.R_OK):
            return False, {}
        try:
            with open(self.control_file(), 'r') as file:
                content = json.load(file)
        except Exception:
            return False, {}
        return True, content

    @staticmethod
    def _check_input_is_terminal():
        """
        Checks if stdin is terminal.
        :return: True if stdin is terminal, otherwise False
        """
        return stdin.isatty()

    @staticmethod
    def _check_run_in_notebook():
        """
        Checks that script is executed in Jupyter Notebook.
        :return: True script is executed in Jupyter Notebook, otherwise False
        """
        try:
            return get_ipython().__class__.__name__ == 'ZMQInteractiveShell'
        except NameError:
            pass
        return False

    def check(self):
        """
        Checks if user has accepted the collection of the information using a control file.
        If the answer is unknown runs the opt-in dialog and updates the control file when the answer is obtained.
        :return: bitmask with opt-in dialog result and information of whether the control file was updated and
        whether the control file is not writable.
        """
        if not self._check_input_is_terminal() or self._check_run_in_notebook():
            return CFCheckResult.DECLINED

        if not os.path.exists(self.control_file()):
            return CFCheckResult.NO_FILE

        if not self.cf_is_empty():
            _, content = self.get_info_from_cf()
            if content['opt_in'] == 1:
                return CFCheckResult.ACCEPTED
            elif content['opt_in'] == 0:
                return CFCheckResult.DECLINED
        print('Incorrect format of the file with opt-in status.')
        return CFCheckResult.DECLINED
