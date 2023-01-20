# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import logging as log
import uuid

from .backend import TelemetryBackend
from ..utils.guid import get_or_generate_uid, remove_uid_file
from ..utils.message import Message, MessageType


class MatomoBackend(TelemetryBackend):
    backend_url = None
    id = 'matomo'
    uid_filename = 'openvino_ga_uid'

    def __init__(self, tid: str = None, app_name: str = None, app_version: str = None):
        super(MatomoBackend, self).__init__(tid, app_name, app_version)
        self.backend_url = tid + "/matomo.php"
        self.uid = None
        self.app_name = app_name
        self.app_version = app_version
        self.default_message_attrs = {
            'idsite': '1',
            'rec': '1',
            'dimension1': self.app_name,
            'dimension2': self.app_version,
        }

    def send(self, message: Message):
        if self.uid is None:
            message.attrs['uid'] = str(uuid.uuid4())
        try:
            import requests
            requests.post(self.backend_url, message.attrs, timeout=1.0, proxies={"http": self.backend_url})
        except Exception as err:
            log.warning("Failed to send event with the following error: {}".format(err))

    def build_event_message(self, event_category: str, event_action: str, event_label: str, event_value: int = 1,
                            **kwargs):
        data = self.default_message_attrs.copy()
        data.update({
            'e_c': event_category,
            'e_a': event_action,
            'e_n': event_label,
            'e_v': event_value,
        })
        return Message(MessageType.EVENT, data)

    def build_session_start_message(self, category: str, **kwargs):
        data = self.default_message_attrs.copy()
        data.update({
            'new_visit': 1,
            'e_c': category,
            'e_a': 'session',
            'e_n': 'start',
            'e_v': 1,
        })
        return Message(MessageType.SESSION_START, data)

    def build_session_end_message(self, category: str, **kwargs):
        data = self.default_message_attrs.copy()
        data.update({
            'e_c': category,
            'e_a': 'session',
            'e_n': 'end',
            'e_v': 1,
        })
        return Message(MessageType.SESSION_END, data)

    def build_error_message(self, category: str, error_msg: str, **kwargs):
        data = self.default_message_attrs.copy()
        data.update({
            'e_c': category,
            'e_a': 'error',
            'e_n': error_msg,
            'e_v': 1,
        })
        return Message(MessageType.ERROR, data)

    def build_stack_trace_message(self, category: str, error_msg: str, **kwargs):
        data = self.default_message_attrs.copy()
        data.update({
            'e_c': category,
            'e_a': 'stack_trace',
            'e_n': error_msg,
            'e_v': 1,
        })
        return Message(MessageType.STACK_TRACE, data)

    def remove_uid_file(self):
        self.uid = None
        self.default_message_attrs['uid'] = None
        remove_uid_file(self.uid_filename)

    def generate_new_uid_file(self):
        self.uid = get_or_generate_uid(self.uid_filename, lambda: str(uuid.uuid4()), is_valid_uuid4)
        self.default_message_attrs['uid'] = self.uid

    def uid_file_initialized(self):
        return self.uid is not None


def is_valid_uuid4(uid: str):
    try:
        uuid.UUID(uid, version=4)
    except ValueError:
        return False
    return True
