# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import logging as log
import uuid

from .backend import TelemetryBackend
from ..utils.guid import get_or_generate_uid, remove_uid_file
import json


class GA4Backend(TelemetryBackend):
    api_secret = "P3wk33kgTY6ijVm66zWf3g"
    measurement_id = "G-3FVYJZJGXR" #rm
    id = 'ga4'
    uid_filename = 'openvino_ga_uid'

    def __init__(self, tid: str = None, app_name: str = None, app_version: str = None):
        super(GA4Backend, self).__init__(tid, app_name, app_version)
        #self.measurement_id = tid
        self.app_name = app_name
        self.app_version = app_version
        self.session_id = None
        self.uid = None
        self.backend_url = "https://www.google-analytics.com/mp/collect?measurement_id={}&api_secret={}".format(self.measurement_id, self.api_secret)
        self.default_message_attrs = {
            'app_name': self.app_name,
            'app_version': self.app_version,
        }

    def send(self, message: dict):
        if message is None:
            return
        try:
            import requests
            requests.post(self.backend_url, data=json.dumps(message),verify=True, timeout=1.0)
        except Exception as err:
            log.warning("Failed to send event with the following error: {}".format(err))

    def build_event_message(self, event_category: str, event_action: str, event_label: str, event_value: int = 1,
                            **kwargs):
        client_id = self.uid
        if client_id is None:
            client_id = "0"
        if self.session_id is None:
            self.generate_new_session_id()

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
                **self.default_message_attrs,
              }
            }
          ]
        }
        return payload

    def build_session_start_message(self, category: str, **kwargs):
        self.generate_new_session_id()
        return None

    def build_session_end_message(self, category: str, **kwargs):
        return None

    def build_error_message(self, category: str, error_msg: str, **kwargs):
        return None

    def build_stack_trace_message(self, category: str, error_msg: str, **kwargs):
        return None

    def remove_client_id_file(self):
        self.uid = None
        remove_uid_file(self.uid_filename)

    def generate_new_uid_file(self):
        self.uid = get_or_generate_uid(self.uid_filename, lambda: str(uuid.uuid4()), is_valid_uuid4)

    def uid_file_initialized(self):
        return self.uid is not None

    def generate_new_session_id(self):
        self.session_id = str(uuid.uuid4())

    def remove_uid_file(self):
        self.uid = None
        remove_uid_file(self.uid_filename)


def is_valid_uuid4(uid: str):
    try:
        uuid.UUID(uid, version=4)
    except ValueError:
        return False
    return True
