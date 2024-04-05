# Copyright (C) 2018-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import json
import os
import stat
import unittest
from platform import system
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from .opt_in_checker import OptInChecker, ConsentCheckResult


class OptInCheckerTest(unittest.TestCase):
    opt_in_checker = OptInChecker()
    test_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_opt_in')
    test_subdir = 'test_opt_in_subdir'

    def init_opt_in_checker(self, test_directory):
        self.opt_in_checker.consent_file_base_dir = MagicMock(return_value=test_directory)
        self.opt_in_checker.consent_file_subdirectory = MagicMock(return_value=self.test_subdir)
        self.opt_in_checker._check_input_is_terminal = MagicMock(return_value=True)
        self.opt_in_checker._check_main_process = MagicMock(return_value=True)

    def test_subdir_no_writable(self):
        # At Windows chmod() sets only the file’s read-only flag. All other bits are ignored.
        # https://docs.python.org/3/library/os.html#os.chmod
        # For this reason this test cannot be run on Windows.
        if system() == 'Windows':
            return
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            test_subdir = os.path.join(test_dir, self.test_subdir)
            if not os.path.exists(test_subdir):
                os.mkdir(test_subdir)
            os.chmod(test_subdir, 0o444)

            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=False) == ConsentCheckResult.NO_FILE)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=True) == ConsentCheckResult.NO_FILE)
            self.assertTrue(self.opt_in_checker.create_or_check_consent_dir() is False)


    def test_dir_no_writable(self):
        # At Windows chmod() sets only the file’s read-only flag. All other bits are ignored.
        # https://docs.python.org/3/library/os.html#os.chmod
        # For this reason this test cannot be run on Windows.
        if system() == 'Windows':
            return
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            os.chmod(test_dir, 0o444)

            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=False) == ConsentCheckResult.NO_FILE)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=True) == ConsentCheckResult.NO_FILE)
            self.assertTrue(self.opt_in_checker.create_or_check_consent_dir() is False)

    def test_subdir_is_file(self):

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            test_subdir = os.path.join(test_dir, self.test_subdir)
            if os.path.exists(test_subdir):
                os.rmdir(test_subdir)
            open(test_subdir, 'w').close()
            os.chmod(test_subdir, 0o444)

            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=False) == ConsentCheckResult.NO_FILE)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=True) == ConsentCheckResult.NO_FILE)

            # Linux allows delete read-only files, while Windows doesn't
            if system() == 'Windows':
                self.assertTrue(self.opt_in_checker.create_or_check_consent_dir() is False)
            else:
                self.assertTrue(self.opt_in_checker.create_or_check_consent_dir() is True)


    def test_incorrect_control_file_format(self):
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            os.mkdir(os.path.join(test_dir, self.test_subdir))
            with open(self.opt_in_checker.consent_file(), 'w') as file:
                file.write("{ abc")
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=False) == ConsentCheckResult.DECLINED)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=True) == ConsentCheckResult.DECLINED)

    def test_incorrect_result_value(self):
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            os.mkdir(os.path.join(test_dir, self.test_subdir))
            with open(self.opt_in_checker.consent_file(), 'w') as file:
                content = {'opt_in': 312}
                json.dump(content, file)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=False) == ConsentCheckResult.DECLINED)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=True) == ConsentCheckResult.DECLINED)

    def test_subdirectory_does_not_exist(self):
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            self.assertTrue(self.opt_in_checker.create_or_check_consent_dir() is True)

    def test_base_directory_does_not_exist(self):
        self.init_opt_in_checker(self.test_directory)
        self.assertTrue(self.opt_in_checker.create_or_check_consent_dir() is False)

    def test_send_telemetry_from_non_cmd_tool(self):
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            self.init_opt_in_checker(test_dir)
            self.opt_in_checker._check_input_is_terminal = MagicMock(return_value=False)
            os.mkdir(os.path.join(test_dir, self.test_subdir))
            with open(self.opt_in_checker.consent_file(), 'w') as file:
                file.write("1")
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=True) == ConsentCheckResult.ACCEPTED)
            self.assertTrue(self.opt_in_checker.check(enable_opt_in_dialog=False) == ConsentCheckResult.ACCEPTED)
