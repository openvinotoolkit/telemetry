#!/usr/bin/env python3

# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import argparse

import openvino_telemetry as tm

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--opt_in", default=False, action='store_true',
                        help="Enabling sending anonymous telemetry data.")
    parser.add_argument("--opt_out", default=False, action='store_true',
                        help="Disabling sending anonymous telemetry data.")

    args = parser.parse_args()

    if args.opt_in is args.opt_out:
        print('Specify either "--opt_in" or "--opt_out" command line parameter.')
        exit(1)

    if args.opt_in:
        tm.Telemetry.opt_in()
    else:
        tm.Telemetry.opt_out()
    exit(0)
