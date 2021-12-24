# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import os
import unittest
from datetime import datetime, timedelta
from platform import system
from unittest.mock import MagicMock

from .opt_in_checker import OptInChecker, ISIPCheckResult


class OptInCheckerTest(unittest.TestCase):
    opt_in_checker = OptInChecker()
    test_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_opt_in')
    test_subdir = 'test_opt_in_subdir'

    def init_opt_in_checker(self):
        self.remove_test_subdir()
        self.opt_in_checker.isip_file_base_dir = MagicMock(return_value=self.test_directory)
        self.opt_in_checker.isip_file_subdirectory = MagicMock(return_value=self.test_subdir)
        self.opt_in_checker._check_input_is_terminal = MagicMock(return_value=True)
        if not os.path.exists(self.test_directory):
            os.mkdir(os.path.join(self.test_directory))
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if not os.path.exists(test_subdir):
            os.mkdir(test_subdir)

    def remove_test_subdir(self):
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if os.path.exists(self.opt_in_checker.isip_file()):
            os.remove(self.opt_in_checker.isip_file())
        if os.path.exists(test_subdir):
            os.rmdir(test_subdir)
        if os.path.exists(self.test_directory):
            os.rmdir(os.path.join(self.test_directory))

    def test_subdir_no_writable(self):
        # At Windows chmod() sets only the file’s read-only flag. All other bits are ignored.
        # https://docs.python.org/3/library/os.html#os.chmod
        # For this reason this test cannot be run on Windows.
        if system() == 'Windows':
            return
        self.init_opt_in_checker()
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if not os.path.exists(test_subdir):
            os.mkdir(test_subdir)
        os.chmod(test_subdir, 0o444)

        self.assertTrue(self.opt_in_checker.check() == ISIPCheckResult.NO_FILE)
        self.assertTrue(self.opt_in_checker.create_or_check_isip_dir() is False)
        self.remove_test_subdir()

    def test_dir_no_writable(self):
        # At Windows chmod() sets only the file’s read-only flag. All other bits are ignored.
        # https://docs.python.org/3/library/os.html#os.chmod
        # For this reason this test cannot be run on Windows.
        if system() == 'Windows':
            return
        self.init_opt_in_checker()
        os.chmod(self.test_directory, 0o444)

        self.assertTrue(self.opt_in_checker.check() == ISIPCheckResult.NO_FILE)
        self.assertTrue(self.opt_in_checker.create_or_check_isip_dir() is False)
        os.chmod(self.test_directory, 0o777)
        self.remove_test_subdir()

    def test_subdir_is_file(self):
        self.init_opt_in_checker()
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if os.path.exists(test_subdir):
            os.rmdir(test_subdir)
        open(test_subdir, 'w').close()
        os.chmod(test_subdir, 0o444)

        self.assertTrue(self.opt_in_checker.check() == ISIPCheckResult.NO_FILE)
        self.assertTrue(self.opt_in_checker.create_or_check_isip_dir() is False)
        os.chmod(test_subdir, 0o777)
        os.remove(test_subdir)
        self.remove_test_subdir()

    def test_incorrect_control_file_format(self):
        self.init_opt_in_checker()
        with open(self.opt_in_checker.isip_file(), 'w') as file:
            file.write("{ abc")
        result = self.opt_in_checker.check()
        self.assertTrue(result == ISIPCheckResult.DECLINED)
        self.remove_test_subdir()

    def test_incorrect_result_value(self):
        self.init_opt_in_checker()
        with open(self.opt_in_checker.isip_file(), 'w') as file:
            content = {'opt_in': 312}
            json.dump(content, file)
        result = self.opt_in_checker.check()
        self.assertTrue(result == ISIPCheckResult.DECLINED)
        self.remove_test_subdir()

    def test_subdirectory_does_not_exist(self):
        self.init_opt_in_checker()
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        os.rmdir(test_subdir)
        self.assertTrue(self.opt_in_checker.create_or_check_isip_dir() is True)
        self.remove_test_subdir()

    def test_base_directory_does_not_exist(self):
        self.init_opt_in_checker()
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        os.rmdir(test_subdir)
        os.rmdir(self.test_directory)
        self.assertTrue(self.opt_in_checker.create_or_check_isip_dir() is False)
        self.remove_test_subdir()
