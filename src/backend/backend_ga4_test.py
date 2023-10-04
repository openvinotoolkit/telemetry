# Copyright (C) 2018-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


import os
import unittest
import uuid
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from .backend import BackendRegistry
from .backend_ga4 import is_valid_cid
from ..utils.cid import get_or_generate_cid
from ..utils.opt_in_checker import OptInChecker


def save_to_file(file_name: str, cid: str):
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w') as file:
        file.write(cid)


class GA4Test(unittest.TestCase):
    test_directory = os.path.dirname(os.path.realpath(__file__)) + os.sep

    def init_backend(self, test_dir, test_subdir):
        self.backend = BackendRegistry.get_backend('ga4')("test_backend", "NONE")
        OptInChecker.consent_file_base_dir = MagicMock(return_value=test_dir)
        self.cid_path = os.path.join(test_subdir, self.backend.cid_filename)
        OptInChecker.consent_file_subdirectory = MagicMock(return_value=os.path.basename(test_subdir))

    def test_generate_new_cid_file(self):
        """
        Checks generation of new client id file.
        """
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                self.backend.generate_new_cid_file()
                self.assertTrue(os.path.exists(self.cid_path))
                self.assertTrue(self.backend.cid_file_initialized())

    def test_remove_cid_file(self):
        """
        Checks removing of client id file.
        """
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)

                self.backend.generate_new_cid_file()
                self.assertTrue(os.path.exists(self.cid_path))
                self.assertTrue(self.backend.cid_file_initialized())
                self.backend.remove_cid_file()
                self.assertFalse(os.path.exists(self.cid_path))
                self.assertFalse(self.backend.cid_file_initialized())

    def test_get_cid_from_old_file(self):
        """
        Checks that the client ID value was taken from legacy file
        """
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)

                old_cid_value = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.old_cid_filename), old_cid_value)

                old_cid_value = get_or_generate_cid(self.backend.cid_filename,
                                                    lambda: str(uuid.uuid4()),
                                                    is_valid_cid,
                                                    self.backend.old_cid_filename)
                self.assertTrue(os.path.exists(self.cid_path))

                with open(test_subdir + os.sep + self.backend.cid_filename, 'r') as file:
                    new_cid_value = file.readline().strip()

                self.assertTrue(new_cid_value == old_cid_value)

    def test_new_cid_priority_over_old_file(self):
        """
        Checks that the client ID value was taken from legacy file
        """
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)

                new_cid = str(uuid.uuid4())
                old_cid = str(uuid.uuid4())

                save_to_file(os.path.join(test_subdir, self.backend.old_cid_filename), old_cid)
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), new_cid)

                cid_value = get_or_generate_cid(self.backend.cid_filename,
                                                    lambda: str(uuid.uuid4()),
                                                    is_valid_cid,
                                                    self.backend.old_cid_filename)

                self.assertTrue(cid_value == new_cid)
