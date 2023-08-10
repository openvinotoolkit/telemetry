import os
import unittest
from unittest.mock import patch

from .main import Telemetry


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
                assert Telemetry("a", "b", "c").check_by_cmd_line_if_dialog_needed() is expected_result

            check()
