# Copyright (C) 2018-2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from .stats_processor import StatsProcessor
from .opt_in_checker import OptInChecker


class StatsProcessorTest(unittest.TestCase):
    test_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_stats')
    test_subdir = 'test_stats_subdir'
    stats_processor = StatsProcessor()

    def init_stats_processor(self, test_directory):
        self.stats_processor.consent_file_base_dir = MagicMock(return_value=test_directory)
        self.stats_processor.consent_file_subdirectory = MagicMock(return_value=self.test_subdir)

    def test_stats_usage(self):
        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with patch.object(OptInChecker, 'consent_file_base_dir', return_value=test_dir):
                with patch.object(OptInChecker, 'consent_file_subdirectory', return_value=self.test_subdir):
                    if not os.path.exists(test_dir):
                        os.mkdir(test_dir)
                    stats_filename = os.path.join(test_dir, self.test_subdir, 'stats')
                    test_data1 = {"value1": 12, "value2": 7, "value3": 8}

                    # Test first creation of statistics file
                    self.stats_processor.update_stats(test_data1)
                    self.assertTrue(os.path.exists(stats_filename))
                    with open(stats_filename, 'r') as file:
                        self.assertTrue(file.readlines() == ['{\n', '    "value1": 12,\n', '    "value2": 7,\n', '    "value3": 8\n', '}'])

                    status, res = self.stats_processor.get_stats()
                    self.assertTrue(status)
                    self.assertTrue(res == test_data1)

                    # Test updating of statistics file
                    test_data2 = {"value1": 15, "a": "abs"}
                    self.stats_processor.update_stats(test_data2)
                    self.assertTrue(os.path.exists(stats_filename))
                    with open(stats_filename, 'r') as file:
                        self.assertTrue(file.readlines() == ['{\n', '    "value1": 15,\n', '    "a": "abs"\n', '}'])

                    status, res = self.stats_processor.get_stats()
                    self.assertTrue(status)
                    self.assertTrue(res == test_data2)

                    # Test removing of statistics file
                    self.stats_processor.remove_stats_file()
                    self.assertFalse(os.path.exists(stats_filename))

                    status, res = self.stats_processor.get_stats()
                    self.assertFalse(status)
                    self.assertTrue(res == {})

                    # Test attempt to read incorrect statistics file
                    with open(stats_filename, 'w') as file:
                        file.write("{ abc")
                    status, res = self.stats_processor.get_stats()
                    self.assertFalse(status)
                    self.assertTrue(res == {})
