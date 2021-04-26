# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import os
import unittest
from datetime import datetime, timedelta
from platform import system

from .opt_in_checker import OptInChecker, CFCheckResult
from unittest.mock import MagicMock


class OptInCheckerTest(unittest.TestCase):
    opt_in_checker = OptInChecker()
    test_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_opt_in')
    test_subdir = 'test_opt_in_subdir'

    def init_opt_in_checker(self):
        self.opt_in_checker.control_file_base_dir = MagicMock(return_value=self.test_directory)
        self.opt_in_checker._control_file_subdirectory = MagicMock(return_value=self.test_subdir)
        if not os.path.exists(self.test_directory):
            os.mkdir(os.path.join(self.test_directory))
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if not os.path.exists(test_subdir):
            os.mkdir(test_subdir)

    def remove_test_subdir(self):
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if os.path.exists(self.opt_in_checker._control_file()):
            os.remove(self.opt_in_checker._control_file())
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
        result = self.opt_in_checker.check()

        self.assertTrue(result == CFCheckResult.NO_WRITABLE)
        self.remove_test_subdir()

    def test_dir_no_writable(self):
        # At Windows chmod() sets only the file’s read-only flag. All other bits are ignored.
        # https://docs.python.org/3/library/os.html#os.chmod
        # For this reason this test cannot be run on Windows.
        if system() == 'Windows':
            return
        self.init_opt_in_checker()
        os.chmod(self.test_directory, 0o444)
        result = self.opt_in_checker.check()

        self.assertTrue(result == CFCheckResult.NO_WRITABLE)
        os.chmod(self.test_directory, 0o777)
        self.remove_test_subdir()

    def test_subdir_is_file(self):
        self.init_opt_in_checker()
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if os.path.exists(test_subdir):
            os.rmdir(test_subdir)
        open(test_subdir, 'w').close()
        result = self.opt_in_checker.check()

        self.assertTrue(result == CFCheckResult.NO_WRITABLE)
        os.remove(test_subdir)
        self.remove_test_subdir()

    def test_incorrect_control_file_format(self):
        self.init_opt_in_checker()
        with open(self.opt_in_checker._control_file(), 'w') as file:
            file.write("{ abc")
        result = self.opt_in_checker.check()
        self.assertTrue(result == CFCheckResult.UNKNOWN)
        self.remove_test_subdir()

    def test_incorrect_result_value(self):
        self.init_opt_in_checker()
        with open(self.opt_in_checker._control_file(), 'w') as file:
            content = {'opt_in': 312}
            json.dump(content, file)
        try:
            self.opt_in_checker.check()
        except Exception as e:
            assert 'Incorrect format of control file.' == str(e)

        self.remove_test_subdir()

    def test_cf_no_writable(self):
        self.init_opt_in_checker()

        open(self.opt_in_checker._control_file(), 'w').close()
        update_date = datetime.fromtimestamp(datetime.now().timestamp()) - timedelta(
            days=self.opt_in_checker.asking_period + 1)
        os.utime(self.opt_in_checker._control_file(), (update_date.timestamp(), update_date.timestamp()))
        os.chmod(self.opt_in_checker._control_file(), 0o444)

        result = self.opt_in_checker.check()
        self.assertTrue(result == CFCheckResult.NO_WRITABLE)

        os.chmod(self.opt_in_checker._control_file(), 0o777)
        self.remove_test_subdir()
