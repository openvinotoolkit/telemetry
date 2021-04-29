# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import argparse
import os

import openvino_telemetry as tm
from openvino_telemetry.utils.opt_in_checker import OptInChecker, CFCheckResult

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--opt_in", default=False, action='store_true', help="Opt-in.")
    parser.add_argument("--opt_out", default=False, action='store_true', help="Opt-out.")

    args = parser.parse_args()

    if args.opt_in is args.opt_out:
        print('Choose either opt_in or opt_out option.')
        exit(1)

    app_name = 'opt_in_out.py'
    app_version = "?"
    opt_in_checker = OptInChecker()

    if not os.path.exists(opt_in_checker.control_file()):
        if not opt_in_checker.create_new_cf_file():
            telemetry = tm.Telemetry(app_name=app_name, app_version=app_version)
            print("Failed to create control file as the directory is not writable. "
                  "Please allow write access to the following directory: {}".format(
                os.path.join(opt_in_checker.control_file_base_dir(), opt_in_checker.control_file_subdirectory())))
            exit(1)

    updated = False
    if args.opt_in:
        updated = opt_in_checker.update_result(CFCheckResult.APPROVED)
    else:
        updated = opt_in_checker.update_result(CFCheckResult.CF_HAS_RESULT)
    if not updated:
        telemetry = tm.Telemetry(app_name=app_name, app_version=app_version)
        if not opt_in_checker.cf_is_empty() or not opt_in_checker.check_if_ask_period_is_passed():
            telemetry.send_event("opt_in_out", "opt_in", "no_writable")
        print("Failed to update the control file as the file is not writable. "
              "Please allow write access to the following file: {}".format(opt_in_checker.control_file()))
        exit(1)

    telemetry = tm.Telemetry(app_name=app_name, app_version=app_version)
    if args.opt_in:
        telemetry.send_event("opt_in_out", "opt_in", "accepted")
    else:
        telemetry.send_event("opt_in_out", "opt_in", "declined", force_send=True)
    print("The control file was updated successfully.")
    exit(0)
