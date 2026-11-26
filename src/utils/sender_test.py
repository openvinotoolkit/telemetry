# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import sys
import time
import unittest

from .sender import TelemetrySender


class FakeTelemetryBackend:
    def send(self, param):
        pass


class FakeTelemetryBackendWithSleep:
    def send(self, param):
        time.sleep(1)


class TelemetrySenderStress(unittest.TestCase):
    def test_stress(self):
        """
        Stress tests to schedule a lot of threads which works super fast (do nothing) with sending messages."
        """
        tm = TelemetrySender()
        fake_backend = FakeTelemetryBackend()
        for _ in range(100000):
            tm.send(fake_backend, None)

    def test_check_shutdown(self):
        """
        Stress test to schedule many threads taking 1 second and then ask to force shutdown. Make sure that the elapsed
        time is small.
        """
        tm = TelemetrySender()
        fake_backend = FakeTelemetryBackendWithSleep()
        # schedule many requests which just wait 1 second
        for _ in range(100000):
            tm.send(fake_backend, None)

        start_time = time.time()
        # ask to shutdown with timeout of 1 second
        tm.force_shutdown(1)
        # check that no more than 3 seconds spent
        self.assertTrue(time.time() - start_time < 3)
        # the workers stop after the messages being sent are finished
        for thread in tm._threads:
            thread.join(3)
            self.assertFalse(thread.is_alive())

    def test_check_shutdown_negative(self):
        """
        Test to check that without forcing shutdown total execution time is expected.
        """
        tm = TelemetrySender(1)  # only one worker thread
        fake_backend = FakeTelemetryBackendWithSleep()
        start_time = time.time()
        # schedule 5 requests which totally should work more than 4 seconds
        for _ in range(5):
            tm.send(fake_backend, None)

        while tm.queue_size:
            time.sleep(0.01)
        self.assertTrue(time.time() - start_time > 4.0)

    def test_exit_is_not_delayed(self):
        """
        Checks that the interpreter exits without waiting for the messages which are queued or being sent, e.g. when
        requests hang because of no Internet connection.
        """
        package = TelemetrySender.__module__.rsplit('.', 2)[0]
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        code = ("import time\n"
                "from {}.utils.sender import TelemetrySender\n"
                "class HangingBackend:\n"
                "    def send(self, message):\n"
                "        time.sleep(3)\n"
                "tm = TelemetrySender()\n"
                "for _ in range(100):\n"
                "    tm.send(HangingBackend(), None)\n"
                "time.sleep(0.5)\n").format(package)
        start_time = time.time()
        subprocess.run([sys.executable, "-c", code], cwd=root_dir, check=True, timeout=60)
        self.assertLess(time.time() - start_time, 2.5)

    def test_check_send_after_shutdown(self):
        """
        Checks that sender does not break if event is sent after shutdown
        """
        tm = TelemetrySender()
        fake_backend = FakeTelemetryBackendWithSleep()
        tm.send(fake_backend, None)

        # ask to shutdown with timeout of 1 second
        tm.force_shutdown(1)
        tm.send(fake_backend, None)