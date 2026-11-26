# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import unittest
import uuid
from platform import system
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
                                         'os': system(),
                                         'docker': 'False',
                                         'usage_count': 1,
                                         'usage_group': 'first_usage'}
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

    def test_env_opt_out(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create consent file with 1 value, no client id and stats files
                save_to_file(OptInChecker().consent_file(), "1")
                files_before = sorted(os.listdir(test_subdir))

                with patch.dict(os.environ, {"OPENVINO_TELEMETRY_OPTOUT": "1"}):
                    for enable_opt_in_dialog in [True, False]:
                        tm = Telemetry()
                        tm.init("app", "version", "tid", backend='ga4', enable_opt_in_dialog=enable_opt_in_dialog)
                        tm.send_event("a", "b", "c", 3)
                        tm.send_event("a", "b", "c", 3, force_send=True)
                        tm.start_session("a")
                        tm.end_session("a")
                        tm.send_error("a", "b")
                        tm.send_stack_trace("a", "b")
                    Telemetry.opt_in("tid")
                    Telemetry.opt_out("tid")

                # check that telemetry is not sent and nothing is written
                GA4Backend.send.assert_not_called()
                self.assertEqual(sorted(os.listdir(test_subdir)), files_before)
                with open(OptInChecker().consent_file()) as file:
                    self.assertEqual(file.read(), "1")

    def test_env_opt_out_after_init_with_consent(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id and consent file with 1 value
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)
                save_to_file(OptInChecker().consent_file(), "1")

                # init telemetry with consent, the variable is not set yet
                with patch.dict(os.environ):
                    os.environ.pop("OPENVINO_TELEMETRY_OPTOUT", None)
                    tm = Telemetry()
                    tm.init("app", "version", "tid", backend='ga4')
                self.assertTrue(tm.consent)

                # set the variable after initialization
                with patch.dict(os.environ, {"OPENVINO_TELEMETRY_OPTOUT": "1"}):
                    tm.send_event("a", "b", "c", 3)
                    tm.send_event("a", "b", "c", 3, force_send=True)
                    tm.start_session("a")
                    tm.end_session("a")
                    tm.send_error("a", "b")
                    tm.send_stack_trace("a", "b")

                # check that telemetry is not sent
                GA4Backend.send.assert_not_called()

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

    @unittest.skipIf(system() == 'Windows' or os.geteuid() == 0, "requires POSIX permissions and non-root user")
    def test_opt_out_read_only_home_no_consent_file(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # no consent file was created, home directory is read-only
                os.chmod(test_dir, 0o555)
                try:
                    tm = Telemetry()
                    tm.init("app", "version", "tid", backend='ga4', enable_opt_in_dialog=False)
                    tm.send_event("a", "b", "c", 3)
                finally:
                    os.chmod(test_dir, 0o755)

                # check that telemetry is not sent
                self.assertFalse(tm.consent)
                GA4Backend.send.assert_not_called()

    @unittest.skipIf(system() == 'Windows' or os.geteuid() == 0, "requires POSIX permissions and non-root user")
    def test_opt_out_read_only_home_with_consent(self):
        from .backend.backend_ga4 import GA4Backend

        with TemporaryDirectory(prefix=self.test_directory) as test_dir:
            with TemporaryDirectory(prefix=test_dir + os.sep) as test_subdir:

                self.init_backend(test_dir, test_subdir)
                GA4Backend.send = MagicMock()

                # create client id
                client_id = str(uuid.uuid4())
                save_to_file(os.path.join(test_subdir, self.backend.cid_filename), client_id)

                # create consent file with 1 value, home directory is read-only
                save_to_file(OptInChecker().consent_file(), "1")
                os.chmod(test_dir, 0o555)
                try:
                    tm = Telemetry()
                    tm.init("app", "version", "tid", backend='ga4', enable_opt_in_dialog=False)
                    tm.send_event("a", "b", "c", 3)
                finally:
                    os.chmod(test_dir, 0o755)

                # check that telemetry is sent (usage stats can't be stored in a read-only home)
                tm.sender.force_shutdown(10)  # waits until the queued message is sent
                GA4Backend.send.assert_called_once()
                message = GA4Backend.send.call_args[0][0]
                self.assertEqual(message['client_id'], client_id)
                self.assertEqual(message['events'][0]['name'], "b")
                GA4Backend.send.reset_mock()
