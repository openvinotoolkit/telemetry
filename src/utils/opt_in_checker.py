# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import json
import os
import time
from datetime import datetime
from enum import IntEnum
from platform import system
from sys import stdin

from .input_with_timeout import input_with_timeout


class CFCheckResult(IntEnum):
    UNKNOWN = 0
    CF_HAS_RESULT = 1
    APPROVED = 2
    DIALOG_WAS_STARTED = 4
    NO_WRITABLE = 8


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
            return CFCheckResult.CF_HAS_RESULT
        if answer == "y" or answer == "yes":
            return CFCheckResult.APPROVED | CFCheckResult.CF_HAS_RESULT
        return CFCheckResult.UNKNOWN

    def _opt_in_dialog(self):
        """
        Runs opt-in dialog until the timeout is expired.
        :return: opt-in dialog result.
        """
        start_time = time.time()
        answer = self._ask_opt_in(self.opt_in_question, self.dialog_timeout)
        time_passed = time.time() - start_time
        while time_passed < self.dialog_timeout and answer == CFCheckResult.UNKNOWN:
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
        cf_dir = os.path.join(self.control_file_base_dir(), self.control_file_subdirectory())
        if not os.path.exists(cf_dir):
            if not os.access(self.control_file_base_dir(), os.W_OK):
                return False
            os.mkdir(cf_dir)
        if not os.access(cf_dir, os.W_OK):
            return False
        try:
            open(self.control_file(), 'w').close()
        except Exception:
            return False
        return True

    def _update_timestamp(self):
        """
        Updates the 'timestamp' value in the control file.
        :return: False if the control file is not writable, otherwise True
        """
        if not os.access(self.control_file(), os.W_OK):
            return False
        os.utime(self.control_file(), (datetime.now().timestamp(), datetime.now().timestamp()))
        return True

    def update_result(self, result: CFCheckResult):
        """
        Updates the 'opt_in' value in the control file.
        :param result: opt-in dialog result.
        :return: False if the control file is not writable, otherwise True
        """
        if not os.access(self.control_file(), os.W_OK):
            return False
        try:
            with open(self.control_file(), 'w') as file:
                if result & CFCheckResult.APPROVED:
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

    def check_if_ask_period_is_passed(self):
        """
        Checks if asking period has passed.
        :return: True if the period has passed, otherwise False
        """
        delta = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.control_file()))
        return delta.days > self.asking_period

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
            shell = get_ipython().__class__.__name__
            if shell == 'ZMQInteractiveShell':
                return True
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
            return CFCheckResult.UNKNOWN

        if not os.path.exists(self.control_file()):
            if not self.create_new_cf_file():
                return CFCheckResult.NO_WRITABLE
        else:
            if not self.cf_is_empty():
                read_successfully, content = self.get_info_from_cf()
                if not read_successfully:
                    return CFCheckResult.UNKNOWN
                if content['opt_in'] == 1:
                    return CFCheckResult.APPROVED | CFCheckResult.CF_HAS_RESULT
                elif content['opt_in'] == 0:
                    return CFCheckResult.CF_HAS_RESULT
                else:
                    raise Exception('Incorrect format of the file with opt-in status.')
            else:
                if not self.check_if_ask_period_is_passed():
                    return CFCheckResult.UNKNOWN

        if not self._update_timestamp():
            return CFCheckResult.NO_WRITABLE

        try:
            answer = self._opt_in_dialog()
        except KeyboardInterrupt:
            return CFCheckResult.UNKNOWN | CFCheckResult.DIALOG_WAS_STARTED
        if answer & CFCheckResult.CF_HAS_RESULT:
            self.update_result(answer)
        answer = answer | CFCheckResult.DIALOG_WAS_STARTED
        return answer
