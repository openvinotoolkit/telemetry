# Copyright (C) 2018-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


import os
import unittest
from unittest.mock import MagicMock

from .backend import BackendRegistry
from ..utils.opt_in_checker import OptInChecker


class GATest(unittest.TestCase):
    test_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_ga_backend')
    test_subdir = 'test_ga_backend_subdir'

    def init_backend(self):
        self.backend = BackendRegistry.get_backend('ga')("test_backend", "NONE")
        OptInChecker.consent_file_base_dir = MagicMock(return_value=self.test_directory)
        OptInChecker.consent_file_subdirectory = MagicMock(return_value=self.test_subdir)
        self.cid_path = os.path.join(self.test_directory, self.test_subdir, self.backend.cid_filename)

        self.clean_test_dir()

        if not os.path.exists(self.test_directory):
            os.mkdir(os.path.join(self.test_directory))

    def clean_test_dir(self):
        test_subdir = os.path.join(self.test_directory, self.test_subdir)
        if os.path.exists(self.cid_path):
            os.remove(self.cid_path)
        if os.path.exists(test_subdir):
            os.rmdir(test_subdir)
        if os.path.exists(self.test_directory):
            os.rmdir(os.path.join(self.test_directory))

    def test_generate_new_cid_file(self):
        """
        Checks generation of new client id file.
        """
        self.init_backend()
        self.backend.generate_new_cid_file()
        self.assertTrue(os.path.exists(self.cid_path))
        self.assertTrue(self.backend.cid_file_initialized())
        self.clean_test_dir()

    def test_remove_cid_file(self):
        """
        Checks removing of client id file.
        """
        self.init_backend()
        self.backend.generate_new_cid_file()
        self.assertTrue(os.path.exists(self.cid_path))
        self.assertTrue(self.backend.cid_file_initialized())
        self.backend.remove_cid_file()
        self.assertFalse(os.path.exists(self.cid_path))
        self.assertFalse(self.backend.cid_file_initialized())
        self.clean_test_dir()
