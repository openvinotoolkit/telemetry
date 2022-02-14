# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

from .backend.backend import BackendRegistry
from .utils.sender import TelemetrySender
from .utils.opt_in_checker import OptInChecker, ISIPCheckResult, DialogResult
import os

class OptInStatus(Enum):
    ACCEPTED = "accepted"
    DECLINED = "declined"
    UNDEFINED = "undefined"


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
    def __init__(self, app_name: str = None, app_version: str = None, tid: str = None,
                 backend: [str, None] = 'ga'):
        # The case when instance is already configured
        if app_name is None:
            if not hasattr(self, 'sender') or self.sender is None:
                raise RuntimeError('The first instantiation of the Telemetry should be done with the '
                                   'application name, version and TID.')
            return

        opt_in_checker = OptInChecker()
        opt_in_check_result = opt_in_checker.check()
        self.consent = opt_in_check_result == ISIPCheckResult.ACCEPTED

        if tid is None:
            print('[ WARNING ] Telemetry will not be sent as TID is not specified.')

        self.tid = tid
        self.backend = BackendRegistry.get_backend(backend)(self.tid, app_name, app_version)
        self.sender = TelemetrySender()

        if self.consent and not self.backend.uid_file_initialized():
            self.backend.generate_new_uid_file()

        # ISIP file may be absent, for example, during the first run of Openvino tool.
        # In this case we trigger opt-in dialog that asks user permission for sending telemetry.
        if opt_in_check_result == ISIPCheckResult.NO_FILE:
            if opt_in_checker.create_or_check_isip_dir():
                answer = ISIPCheckResult.DECLINED
                # create ISIP file if possible with "0" value
                if not opt_in_checker.update_result(answer):
                    pass
                try:
                    # run opt-in dialog
                    answer = opt_in_checker.opt_in_dialog()
                    if answer == DialogResult.ACCEPTED:
                        # If the dialog result is "accepted" we generate new GUID file and update ISIP
                        # file with "1" value. Telemetry data will be collected in this case.
                        self.consent = True
                        self.backend.generate_new_uid_file()
                        self.send_opt_in_event(OptInStatus.ACCEPTED)

                        # Here we send telemetry with "accepted" dialog result
                        opt_in_checker.update_result(ISIPCheckResult.ACCEPTED)
                    elif answer == DialogResult.TIMEOUT_REACHED:
                        # If timer was reached and we have no response from user, we should not send
                        # any data except for dialog result.
                        # At this point we have already created ISIP file with "0" value,
                        # which means that no telemetry data will be collected in further functions.
                        # As ISIP file exists on the system the dialog won't be shown again.

                        # Here we send telemetry with "timer reached" dialog result
                        self.send_opt_in_event(OptInStatus.UNDEFINED, force_send=True)
                    else:
                        # If the dialog result is "declined" we should not send any data except for dialog result.
                        # At this point we have already created ISIP file with "0" value,
                        # which means that no telemetry data will be collected in further functions.
                        # As ISIP file exists on the system the dialog won't be shown again.

                        # Here we send telemetry with "declined" dialog result
                        self.send_opt_in_event(OptInStatus.DECLINED, force_send=True)
                except KeyboardInterrupt:
                    pass

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
    def _update_opt_in_status(tid: str, new_opt_in_status: bool):
        """
        Updates opt-in status.

        :param tid: ID of telemetry base.
        :param new_opt_in_status: new opt-in status.
        :return: None
        """
        app_name = 'opt_in_out'
        app_version = Telemetry.get_version()
        opt_in_checker = OptInChecker()
        opt_in_check = opt_in_checker.check()

        prev_status = OptInStatus.UNDEFINED
        if opt_in_check == ISIPCheckResult.DECLINED:
            prev_status = OptInStatus.DECLINED
        elif opt_in_check == ISIPCheckResult.ACCEPTED:
            prev_status = OptInStatus.ACCEPTED

        if new_opt_in_status:
            updated = opt_in_checker.update_result(ISIPCheckResult.ACCEPTED)
        else:
            updated = opt_in_checker.update_result(ISIPCheckResult.DECLINED)
        if not updated:
            return

        telemetry = Telemetry(tid=tid, app_name=app_name, app_version=app_version)

        # In order to prevent sending of duplicate events, after multiple run of opt_in_out --opt_in/--opt_out
        # we send opt_in event only if consent value is changed
        if new_opt_in_status:
            telemetry.backend.generate_new_uid_file()
            if prev_status != OptInStatus.ACCEPTED:
                telemetry.send_opt_in_event(OptInStatus.ACCEPTED, prev_status)
            print("You have successfully opted in to send the telemetry data.")
        else:
            if prev_status != OptInStatus.DECLINED:
                telemetry.send_opt_in_event(OptInStatus.DECLINED, prev_status, force_send=True)
            telemetry.backend.remove_uid_file()
            print("You have successfully opted out to send the telemetry data.")

    def send_opt_in_event(self, new_state: OptInStatus, prev_state: OptInStatus = OptInStatus.UNDEFINED,
                          label: str = "", force_send=False):
        """
        Sends opt-in event.

        :param new_state: new opt-in status.
        :param prev_state: previous opt-in status.
        :param label: the label with the information of opt-in status change.
        :param force_send: forces to send event ignoring the consent value
        :return: None
        """
        if new_state == OptInStatus.UNDEFINED:
            self.send_event("opt_in", "timer_reached", label, force_send=force_send)
        else:
            label = "{{prev_state:{}, new_state: {}}}".format(prev_state.value, new_state.value)
            self.send_event("opt_in", new_state.value, label, force_send=force_send)

    @staticmethod
    def opt_in(tid: str):
        """
        Enables sending anonymous telemetry data.

        :param tid: ID of telemetry base.
        :return: None
        """
        Telemetry._update_opt_in_status(tid, True)

    @staticmethod
    def opt_out(tid: str):
        """
        Disables sending anonymous telemetry data.

        :param tid: ID of telemetry base.
        :return: None
        """
        Telemetry._update_opt_in_status(tid, False)

    @staticmethod
    def get_version():
        """
        Returns version of telemetry library.
        """
        return '2022.1.1'
