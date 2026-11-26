# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


import http.server
import json
import os
import socket
import threading
import time
import unittest
import uuid
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib import request

from .backend import BackendRegistry
from .backend_ga4 import GA4Backend, MAX_REQUESTS_IN_PROGRESS, is_valid_cid
from ..utils.cid import get_or_generate_cid
from ..utils.opt_in_checker import OptInChecker
from ..utils.sender import TelemetrySender

# main_test.py replaces GA4Backend.send with a MagicMock without restoring it, so keep the original implementation
GA4_SEND = GA4Backend.send


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

    def test_is_docker(self):
        from .backend_ga4 import is_docker
        run_from_docker = "DOCKER_RUN" in os.environ and os.environ["DOCKER_RUN"].lower() == "true"

        self.assertTrue(run_from_docker == is_docker())


class GA4SendTest(unittest.TestCase):
    def setUp(self):
        # connect to the local test server directly, ignoring proxy environment variables
        request.install_opener(request.build_opener(request.ProxyHandler({})))

    def tearDown(self):
        request.install_opener(None)

    @staticmethod
    def make_backend(port):
        backend = GA4Backend("test_tid", "test_app", "test_version")
        backend.backend_url = "http://127.0.0.1:{}/mp/collect".format(port)
        return backend

    def test_events_are_not_lost(self):
        """
        Checks that all events sent in a burst are delivered to the server.
        """
        received = []
        lock = threading.Lock()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                time.sleep(0.1)  # network latency
                with lock:
                    received.append(json.loads(body))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler, bind_and_activate=False)
        server.request_queue_size = 128  # the default listen backlog of 5 resets concurrent connections
        server.server_bind()
        server.server_activate()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            backend = self.make_backend(server.server_port)
            sender = TelemetrySender()
            num_events = 100
            with patch.object(GA4Backend, 'send', GA4_SEND):
                for i in range(num_events):
                    sender.send(backend, backend.build_event_message("category", "action", str(i)))
                deadline = time.time() + 5
                while sender.queue_size and time.time() < deadline:
                    time.sleep(0.05)

            labels = sorted(int(message['events'][0]['params']['event_label']) for message in received)
            self.assertEqual(labels, list(range(num_events)))
        finally:
            server.shutdown()
            server.server_close()

    def test_no_hang_without_internet(self):
        """
        Checks that sending does not hang longer than the timeout if the server never responds.
        """
        # the kernel accepts TCP connections to the listening socket, but nothing is ever sent back
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(('127.0.0.1', 0))
            server.listen(16)
            backend = self.make_backend(server.getsockname()[1])
            message = backend.build_event_message("category", "action", "label")

            start_time = time.time()
            GA4_SEND(backend, message)
            elapsed = time.time() - start_time

        self.assertLessEqual(backend.timeout, 3.0)
        self.assertLess(elapsed, 3.5)

    def test_no_hang_on_dns_resolution(self):
        """
        Checks that sending does not hang longer than the timeout if DNS resolution hangs.
        """
        release = threading.Event()

        def hanging_getaddrinfo(*args, **kwargs):
            release.wait(30)
            raise socket.gaierror("DNS server is not reachable")

        backend = GA4Backend("test_tid", "test_app", "test_version")
        backend.backend_url = "http://telemetry.test/mp/collect"
        message = backend.build_event_message("category", "action", "label")
        try:
            with patch.object(socket, 'getaddrinfo', hanging_getaddrinfo):
                start_time = time.time()
                GA4_SEND(backend, message)
                elapsed = time.time() - start_time
        finally:
            release.set()

        self.assertLessEqual(backend.timeout, 3.0)
        self.assertLess(elapsed, 3.5)

    def test_hanging_requests_are_bounded(self):
        """
        Checks that requests hanging on DNS resolution after the timeout are bounded, new messages are dropped when
        the bound is reached, and the slots are freed when the requests finish.
        """
        release = threading.Event()
        resolutions = []

        def hanging_getaddrinfo(*args, **kwargs):
            resolutions.append(args[0])
            release.wait(30)
            raise socket.gaierror("DNS server is not reachable")

        def request_threads():
            return [t for t in threading.enumerate() if t.name == 'openvino_telemetry_request']

        def wait_for(predicate):
            deadline = time.time() + 5
            while not predicate() and time.time() < deadline:
                time.sleep(0.01)

        backend = GA4Backend("test_tid", "test_app", "test_version")
        backend.backend_url = "http://telemetry.test/mp/collect"
        backend.timeout = 0.01
        message = backend.build_event_message("category", "action", "label")
        with patch.object(socket, 'getaddrinfo', hanging_getaddrinfo):
            try:
                for _ in range(MAX_REQUESTS_IN_PROGRESS + 10):
                    GA4_SEND(backend, message)
                wait_for(lambda: len(resolutions) >= MAX_REQUESTS_IN_PROGRESS)
                self.assertEqual(len(request_threads()), MAX_REQUESTS_IN_PROGRESS)
                self.assertEqual(len(resolutions), MAX_REQUESTS_IN_PROGRESS)
            finally:
                release.set()

            wait_for(lambda: not request_threads())
            self.assertEqual(request_threads(), [])

            # the slots are freed, so a new message is sent
            GA4_SEND(backend, message)
            wait_for(lambda: len(resolutions) > MAX_REQUESTS_IN_PROGRESS)
            self.assertEqual(len(resolutions), MAX_REQUESTS_IN_PROGRESS + 1)
