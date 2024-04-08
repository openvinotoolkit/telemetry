# Copyright (C) 2018-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import json
import uuid
from copy import copy
from urllib import request

from .backend import TelemetryBackend
from ..utils.cid import get_or_generate_cid, remove_cid_file
from ..utils.params import telemetry_params


class GA4Backend(TelemetryBackend):
    id = 'ga4'
    cid_filename = 'openvino_ga_cid'
    old_cid_filename = 'openvino_ga_uid'

    def __init__(self, tid: str = None, app_name: str = None, app_version: str = None):
        super(GA4Backend, self).__init__(tid, app_name, app_version)
        self.measurement_id = tid
        self.app_name = app_name
        self.app_version = app_version
        self.session_id = None
        self.cid = None
        self.backend_url = "https://www.google-analytics.com/mp/collect?measurement_id={}&api_secret={}".format(
            self.measurement_id, telemetry_params["api_key"])
        self.default_message_attrs = {
            'app_name': self.app_name,
            'app_version': self.app_version,
        }

    def send(self, message: dict):
        if message is None:
            return
        try:
            data = json.dumps(message).encode()

            if self.backend_url.lower().startswith('http'):
                req = request.Request(self.backend_url, data=data)
            else:
                raise ValueError("Incorrect backend URL.")

            request.urlopen(req)  # nosec
        except Exception as err:
            pass  # nosec

    def build_event_message(self, event_category: str, event_action: str, event_label: str, event_value: int = 1,
                            app_name=None, app_version=None,
                            **kwargs):
        client_id = self.cid
        if client_id is None:
            client_id = "0"
        if self.session_id is None:
            self.generate_new_session_id()

        default_args = copy(self.default_message_attrs)
        if app_name is not None:
            default_args['app_name'] = app_name
        if app_version is not None:
            default_args['app_version'] = app_version

        payload = {
            "client_id": client_id,
            "non_personalized_ads": False,
            "events": [
                {
                    "name": event_action,
                    "params": {
                        "event_category": event_category,
                        "event_label": event_label,
                        "event_count": event_value,
                        "session_id": self.session_id,
                        **default_args,
                    }
                }
            ]
        }
        return payload

    def build_session_start_message(self, category: str, **kwargs):
        self.generate_new_session_id()
        return self.build_event_message(category, "session", "start", 1)

    def build_session_end_message(self, category: str, **kwargs):
        return self.build_event_message(category, "session", "end", 1)

    def build_error_message(self, category: str, error_msg: str, **kwargs):
        return self.build_event_message(category, "error_", error_msg, 1)

    def build_stack_trace_message(self, category: str, error_msg: str, **kwargs):
        return self.build_event_message(category, "stack_trace", error_msg, 1)

    def generate_new_cid_file(self):
        self.cid = get_or_generate_cid(self.cid_filename, lambda: str(uuid.uuid4()), is_valid_cid,
                                       self.old_cid_filename)

    def cid_file_initialized(self):
        return self.cid is not None

    def generate_new_session_id(self):
        self.session_id = str(uuid.uuid4())

    def remove_cid_file(self):
        self.cid = None
        remove_cid_file(self.cid_filename)
        remove_cid_file(self.old_cid_filename)


def is_valid_cid(cid: str):
    try:
        uuid.UUID(cid, version=4)
    except ValueError:
        return False
    return True
