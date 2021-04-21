# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import json
import os
import time
from datetime import datetime
from enum import IntEnum
from platform import system

from .input_with_timeout import input_with_timeout


class CFCheckResult(IntEnum):
    UNKNOWN = 0
    CF_HAS_RESULT = 1
    APPROVED = 2
    UPDATED = 4
    NO_WRITABLE = 8


class OptInChecker:
    dialog_timeout = 60  # seconds
    asking_period = 14  # days
    opt_in_question = """To improve our software and customer experience, Intel would like to collect technical 
    information abjjout your software installation and runtime status (such as metrics, software SKU/serial, counters, 
    flags and timestamps), and development environment (such as operating system, CPU architecture, last 4-digits of
    the MAC address, 3rd party API usage and other Intel products installed). Information that cannot be linked to 
    an identifiable person may be retained by Intel as long as it is necessary to support the software. You can revoke
    your consent at any time by running opt_in_out.py script. DO YOU ACCEPT? ("Y" if you consent to the collection of 
    your information or "N" if you do NOT consent to the collection of your information)"""
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
            return CFCheckResult.UPDATED
        if answer == "y" or answer == "yes":
            return CFCheckResult.APPROVED | CFCheckResult.UPDATED
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
    def _control_file_base_dir():
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
    def _control_file_subdirectory():
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

    def _control_file(self):
        """
        Returns the control file path.
        :return: control file path.
        """
        return os.path.join(self._control_file_base_dir(), self._control_file_subdirectory(), "openvino_telemetry.json")

    def _create_new_cf_file(self):
        """
        Creates a new control file.
        :return: True if the file is created successfully, otherwise False
        """
        cf_dir = os.path.join(self._control_file_base_dir(), self._control_file_subdirectory())
        if not os.path.exists(cf_dir):
            if not os.access(self._control_file_base_dir(), os.W_OK):
                return False
            os.mkdir(cf_dir)
        if not os.access(cf_dir, os.W_OK):
            return False
        try:
            open(self._control_file(), 'w').close()
        except Exception:
            return False
        return True

    def _update_timestamp(self):
        """
        Updates modification time attribute of the control file.
        :return: False if the control file is not writable, otherwise True
        """
        if not os.access(self._control_file(), os.W_OK):
            return False
        os.utime(self._control_file(), (datetime.now().timestamp(), datetime.now().timestamp()))
        return True

    def _update_result(self, result: CFCheckResult):
        """
        Updates the 'result' value in the control file.
        :param result: opt-in dialog result.
        :return: False if the control file is not writable, otherwise True
        """
        if not os.access(self._control_file(), os.W_OK):
            return False
        try:
            with open(self._control_file(), 'w') as file:
                if result & CFCheckResult.APPROVED:
                    content = {'result': 1}
                else:
                    content = {'result': 0}
                json.dump(content, file)
        except Exception:
            return False
        return True

    def _cf_is_empty(self):
        """
        Checks if the control file is empty.
        :return: True if control file is empty, otherwise False.
        """
        if os.stat(self._control_file()).st_size == 0:
            return True
        _, content = self._get_info_from_cf()
        return 'result' not in content

    def _get_info_from_cf(self):
        """
        Gets information from control file.
        :return: the tuple, where the first element is True if the file is read successfully, otherwise False
        and the second element is the content of the control file.
        """
        if not os.access(self._control_file(), os.R_OK):
            return False, {}
        try:
            with open(self._control_file(), 'r') as file:
                content = json.load(file)
        except Exception:
            return False, {}
        return True, content

    def _check_if_ask_period_is_passed(self):
        """
        Checks if asking period is passed.
        :return: True if the period is passed, otherwise False
        """
        delta = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self._control_file()))
        return delta.days > self.asking_period

    def check(self):
        """
        Checks if user has accepted the collection of the information using a control file.
        If the answer is unknown runs the opt-in dialog and updates the control file when the answer is obtained.
        :return: bitmask with opt-in dialog result and information of whether the control file was updated and
        whether the control file is not writable.
        """
        if not os.path.exists(self._control_file()):
            if not self._create_new_cf_file():
                return CFCheckResult.NO_WRITABLE
        else:
            if not self._cf_is_empty():
                _, content = self._get_info_from_cf()
                if content['result'] == 1:
                    return CFCheckResult.APPROVED | CFCheckResult.CF_HAS_RESULT
                elif content['result'] == 0:
                    return CFCheckResult.CF_HAS_RESULT
                else:
                    raise Exception('Incorrect format of control file.')
            else:
                if not self._check_if_ask_period_is_passed():
                    return CFCheckResult.UNKNOWN

        if not self._update_timestamp():
            return CFCheckResult.NO_WRITABLE

        try:
            answer = self._opt_in_dialog()
        except KeyboardInterrupt:
            return CFCheckResult.UNKNOWN
        if answer & CFCheckResult.UPDATED:
            self._update_result(answer)
            answer = answer | CFCheckResult.CF_HAS_RESULT
        return answer
