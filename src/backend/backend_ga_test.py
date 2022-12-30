# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


import os
import unittest
from unittest.mock import MagicMock

from .backend import BackendRegistry
from ..utils.guid import get_uid_path
from ..utils.opt_in_checker import OptInChecker


class InputWithTimeoutTest(unittest.TestCase):
    test_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_ga_backend')
    test_subdir = 'test_ga_backend_subdir'

    def init_backend(self):
        self.backend = BackendRegistry.get_backend('ga')("test_backend", "NONE")
        OptInChecker.consent_file_base_dir = MagicMock(return_value=self.test_directory)
        OptInChecker.consent_file_subdirectory = MagicMock(return_value=self.test_subdir)
        self.uid_path = os.path.join(self.test_directory, self.test_subdir, self.backend.uid_filename)

        self.clean_test_dir()

        if not os.path.exists(self.test_directory):
            os.mkdir(os.path.join(self.test_directory))

    def clean_test_dir(self):
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if os.path.exists(self.uid_path):
            os.remove(self.uid_path)
        if os.path.exists(test_subdir):
            os.rmdir(test_subdir)
        if os.path.exists(self.test_directory):
            os.rmdir(os.path.join(self.test_directory))

    def test_generate_new_uid_file(self):
        """
        Checks generation of new uid file.
        """
        self.init_backend()
        self.backend.generate_new_uid_file()
        self.assertTrue(os.path.exists(self.uid_path))
        self.assertTrue(self.backend.uid_file_initialized())
        self.clean_test_dir()

    def test_remove_uid_file(self):
        """
        Checks removing of uid file.
        """
        self.init_backend()
        self.backend.generate_new_uid_file()
        self.assertTrue(os.path.exists(self.uid_path))
        self.assertTrue(self.backend.uid_file_initialized())
        self.backend.remove_uid_file()
        self.assertFalse(os.path.exists(self.uid_path))
        self.assertFalse(self.backend.uid_file_initialized())
        self.clean_test_dir()
