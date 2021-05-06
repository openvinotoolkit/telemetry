# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os

from .backend.backend import BackendRegistry
from .utils.opt_in_checker import OptInChecker, CFCheckResult
from .utils.sender import TelemetrySender


class SingletonMetaClass(type):
    def __init__(self, cls_name, super_classes, dic):
        self.__single_instance = None
        super().__init__(cls_name, super_classes, dic)

    def __call__(cls, *args, **kwargs):
        if cls.__single_instance is None:
            cls.__single_instance = super(SingletonMetaClass, cls).__call__(*args, **kwargs)
        return cls.__single_instance


class Telemetry(metaclass=SingletonMetaClass):
    """
    The main class to send telemetry data. It uses singleton pattern. The instance should be initialized with the
    application name, version and tracking id just once. Later the instance can be created without parameters.
    """

    def __init__(self, app_name: str = None, app_version: str = None, tid: [None, str] = None,
                 backend: [str, None] = 'ga'):
        if not hasattr(self, 'tid'):
            self.tid = None
        if app_name is not None:
            opt_in_check_result = OptInChecker().check()
            self.consent = opt_in_check_result & CFCheckResult.APPROVED
            # override default tid
            if tid is not None:
                self.tid = tid
            self.backend = BackendRegistry.get_backend(backend)(self.tid, app_name, app_version)
            self.sender = TelemetrySender()
            if opt_in_check_result & CFCheckResult.DIALOG_WAS_STARTED:
                if opt_in_check_result & CFCheckResult.APPROVED:
                    opt_in_action = "accepted"
                elif opt_in_check_result & CFCheckResult.CF_HAS_RESULT:
                    opt_in_action = "declined"
                else:
                    opt_in_action = "undefined"
                if opt_in_action == "undefined":
                    self.send_event("opt_in", "undefined", "noanswer", force_send=True)
                else:
                    self.send_event("opt_in", opt_in_action, "undefined_" + opt_in_action, force_send=True)
            if opt_in_check_result & CFCheckResult.NO_WRITABLE:
                self.send_event("opt_in", "undefined", "no_writable", force_send=True)
        else:  # use already configured instance
            assert self.sender is not None, 'The first instantiation of the Telemetry should be done with the ' \
                                            'application name and version'

    def force_shutdown(self, timeout: float = 1.0):
        """
        Stops currently running threads which may be hanging because of no Internet connection.

        :param timeout: maximum timeout time
        :return: None
        """
        self.sender.force_shutdown(timeout)

    def send_event(self, event_category: str, event_action: str, event_label: str, event_value: int = 1,
                   force_send=False, **kwargs):
        """
        Send single event.

        :param event_category: category of the event
        :param event_action: action of the event
        :param event_label: the label associated with the action
        :param event_value: the integer value corresponding to this label
        :param force_send: forces to send event ignoring the consent value
        :param kwargs: additional parameters
        :return: None
        """
        if self.consent or force_send:
            self.sender.send(self.backend, self.backend.build_event_message(event_category, event_action, event_label,
                                                                            event_value, **kwargs))

    def start_session(self, category: str, **kwargs):
        """
        Sends a message about starting of a new session.

        :param kwargs: additional parameters
        :param category: the application code
        :return: None
        """
        if self.consent:
            self.sender.send(self.backend, self.backend.build_session_start_message(category, **kwargs))

    def end_session(self, category: str, **kwargs):
        """
        Sends a message about ending of the current session.

        :param kwargs: additional parameters
        :param category: the application code
        :return: None
        """
        if self.consent:
            self.sender.send(self.backend, self.backend.build_session_end_message(category, **kwargs))

    def send_error(self, category: str, error_msg: str, **kwargs):
        if self.consent:
            self.sender.send(self.backend, self.backend.build_error_message(category, error_msg, **kwargs))

    def send_stack_trace(self, category: str, stack_trace: str, **kwargs):
        if self.consent:
            self.sender.send(self.backend, self.backend.build_stack_trace_message(category, stack_trace, **kwargs))

    @staticmethod
    def _update_opt_in_status(new_opt_in_status: bool):
        app_name = 'opt_in_out'
        # TODO: add functionality for getting openvino version
        app_version = "UNKNOWN"
        opt_in_checker = OptInChecker()

        if not os.path.exists(opt_in_checker.control_file()):
            if not opt_in_checker.create_new_cf_file():
                _ = Telemetry(app_name=app_name, app_version=app_version)
                print("Failed to update opt-in status. "
                      "Please allow write access to the following directory: {}".format(
                    os.path.join(opt_in_checker.control_file_base_dir(), opt_in_checker.control_file_subdirectory())))
                return

        prev_result = "undefined"
        if not opt_in_checker.cf_is_empty():
            read_successfully, content = opt_in_checker.get_info_from_cf()
            if read_successfully:
                if content['opt_in'] == 1:
                    prev_result = "accepted"
                elif content['opt_in'] == 0:
                    prev_result = "declined"

        if new_opt_in_status:
            updated = opt_in_checker.update_result(CFCheckResult.APPROVED)
        else:
            updated = opt_in_checker.update_result(CFCheckResult.CF_HAS_RESULT)
        if not updated:
            telemetry = Telemetry(app_name=app_name, app_version=app_version)
            if not opt_in_checker.cf_is_empty() or not opt_in_checker.check_if_ask_period_is_passed():
                telemetry.send_event("opt_in", "undefined", "nowritable")
            print("Failed to update opt-in status. "
                  "Please allow write access to the following file: {}".format(opt_in_checker.control_file()))
            return

        telemetry = Telemetry(app_name=app_name, app_version=app_version)
        if new_opt_in_status:
            if prev_result != "accepted":
                telemetry.send_event("opt_in", "accepted", prev_result + "_accepted")
            print("You have successfully opted in to send the telemetry data.")
        else:
            if prev_result != "declined":
                telemetry.send_event("opt_in", "declined", prev_result + "_declined", force_send=True)
            print("You have successfully opted out to send the telemetry data.")

    @staticmethod
    def opt_in():
        Telemetry._update_opt_in_status(True)

    @staticmethod
    def opt_out():
        Telemetry._update_opt_in_status(False)
