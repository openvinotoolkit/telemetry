# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import time
import unittest

from .input_with_timeout import input_with_timeout


class InputWithTimeoutTest(unittest.TestCase):
    def test(self):
        """
        Checks that input was waited no longer than specified time.
        """
        start_time = time.time()
        _ = input_with_timeout("", 3)
        self.assertTrue(time.time() - start_time < 4)
