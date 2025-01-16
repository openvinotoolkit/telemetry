# Copyright (C) 2018-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import unittest
import uuid
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, call, patch

from .backend.backend import BackendRegistry
from .main import Telemetry
from .utils.opt_in_checker import OptInChecker


def save_to_file(file_name: str, cid: str):
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w') as file:
        file.write(cid)


class TelemetryTest(unittest.TestCase):
    data = [
        ('demo.py', False),
        (os.path.join('dir1', 'dir2', 'demo.py'), False),
        (os.path.join('dir1', 'dir2', 'demo'), False),
        ("app", False),
        ('mo.py', True),
        (os.path.join('openvino', 'tools', 'mo', 'main.py'), True),
        (os.path.join('openvino', 'tools', 'ovc', 'main.py'), True),
        ('mo', True),
        ('pot', True),
        ('omz_downloader', True),
        ('omz_converter', True),
        ('omz_data_downloader', True),
        ('omz_info_dumper', True),
        ('omz_quantizer', True),
        ('accuracy_check', True)
    ]

    def test_check_by_cmd_line_if_dialog_needed(self):
        for test_data in self.data:
            app_name = test_data[0]
            expected_result = test_data[1]

            @patch('sys.argv', [app_name])
            def check():
                if not Telemetry("a", "b", "c").check_by_cmd_line_if_dialog_needed() is expected_result:
                    raise Exception("Expected result is not equal to dialog result.")

            check()


class GeneralTelemetryTest(unittest.TestCase):
    test_directory = os.path.dirname(os.path.realpath(__file__))

    def init_backend(self, test_dir, test_subdir):
        self.backend = BackendRegistry.get_backend('ga4')("test_backend", "NONE")
        OptInChecker.consent_file_base_dir = MagicMock(return_value=test_dir)
        OptInChecker._run_in_ci = MagicMock(return_value=False)
        self.cid_path = os.path.join(test_subdir, self.backend.cid_filename)
        OptInChecker.consent_file_subdirectory = MagicMock(return_value=os.path.basename(test_subdir))
        _ = Telemetry("a", "b", "c")

    def make_message(self, client_id, app_name, app_version, category, action, label, value, session_id):
        return {'client_id': client_id,
                               'non_personalized_ads': False,
                               'events': [
                                   {'name': action,
                                    'params':
                                        {'event_category': category,
                                         'event_label': label,
                                         'event_count': value,
                                         'session_id': session_id,
                                         'app_name': app_name,
                                         'app_version': app_version,
                                         'usage_count': 1}
                                    }
                               ]}

    def test_send_with_consent(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)

                # create consent file with 1 value
                save_to_file(OptInChecker().consent_file(), "1")

                # init telemetry
                tm = Telemetry()
                tm.init("app", "version", "tid", backend='ga4')

                # check that telemetry is sent
                tm.send_event("a", "b", "c", 3)
                session_id = tm.backend.session_id
                calls = [call(self.make_message(client_id, "app", "version", "a", "b", "c", 3, session_id))]
                GA4Backend.send.assert_has_calls(calls)
                GA4Backend.send.reset_mock()

    def test_no_send_with_no_consent(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)

                # create consent file with 0 value
                save_to_file(OptInChecker().consent_file(), "0")

                # init telemetry
                tm = Telemetry()
                tm.init("app", "version", "tid", backend='ga4')

                # check that telemetry is not sent
                tm.send_event("a", "b", "c", 3)
                GA4Backend.send.assert_has_calls([])
                GA4Backend.send.reset_mock()

    def test_opt_out_with_consent(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)

                # create consent file with 1 value
                save_to_file(OptInChecker().consent_file(), "1")

                # init telemetry with opt-out approach
                tm = Telemetry()
                tm.init("app", "version", "tid", backend='ga4', enable_opt_in_dialog=False)

                # check that telemetry is sent
                tm.send_event("a", "b", "c", 3)
                session_id = tm.backend.session_id
                calls = [call(self.make_message(client_id, "app", "version", "a", "b", "c", 3, session_id))]
                GA4Backend.send.assert_has_calls(calls)
                GA4Backend.send.reset_mock()

    def test_opt_out_with_no_consent(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)

                # create consent file with 0 value
                save_to_file(OptInChecker().consent_file(), "0")

                # init telemetry with opt-out approach
                tm = Telemetry()
                tm.init("app", "version", "tid", backend='ga4', enable_opt_in_dialog=False)

                # check that telemetry is not sent
                tm.send_event("a", "b", "c", 3)
                GA4Backend.send.assert_has_calls([])
                GA4Backend.send.reset_mock()

    def test_opt_out_with_no_consent_file(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)

                # no consent file was created

                # init telemetry with opt-out approach
                tm = Telemetry()
                tm.init("app", "version", "tid", backend='ga4', enable_opt_in_dialog=False)
                tm.send_event("a", "b", "c", 3)

                # check that telemetry is sent
                session_id = tm.backend.session_id
                calls = [call(self.make_message(client_id, "app", "version", "a", "b", "c", 3, session_id))]
                GA4Backend.send.assert_has_calls(calls)
                GA4Backend.send.reset_mock()
