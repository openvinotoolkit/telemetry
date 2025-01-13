# Copyright (C) 2018-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from .opt_in_checker import OptInChecker
import logging as log
import os
import json


class StatsProcessor:
    def __init__(self):
        self.opt_in_checker = OptInChecker()

    def stats_file(self):
        """
        Returns the statistics file path.
        """
        return os.path.join(self.opt_in_checker.consent_file_base_dir(), self.opt_in_checker.consent_file_subdirectory(), "stats")

    def create_new_stats_file(self):
        """
        Creates a new statistics file.
        :return: True if the file is created successfully, otherwise False
        """
        if not self.opt_in_checker.create_or_check_consent_dir():
            return False
        try:
            open(self.stats_file(), 'w').close()
        except Exception:
            return False
        return True

    def update_stats(self, stats: dict):
        """
        Updates the statistics in the statistics file.
        :param stats: the dictionary with statistics.
        :return: False if the statistics file is not writable, otherwise True
        """
        if self.opt_in_checker.consent_file_base_dir() is None or self.opt_in_checker.consent_file_subdirectory() is None:
            return False
        if not os.path.exists(self.stats_file()):
            if not self.create_new_stats_file():
                return False
        if not os.access(self.stats_file(), os.W_OK):
            log.warning("Failed to usage statistics. "
                        "Please allow write access to the following file: {}".format(self.stats_file()))
            return False
        try:
            str_data = json.dumps(stats, indent=4)
            with open(self.stats_file(), 'w') as file:
                file.write(str_data)
        except Exception:
            return False
        return True

    def get_stats(self):
        """
        Gets information from statistics file.
        :return: the tuple, where the first element is True if the file is read successfully, otherwise False
        and the second element is the content of the statistics file.
        """
        if not os.access(self.stats_file(), os.R_OK):
            return False, {}
        try:
            with open(self.stats_file(), 'r') as file:
                data = json.load(file)
        except Exception:
            return False, {}
        return True, data

    def remove_stats_file(self):
        """
        Removes statistics file.
        :return: None
        """
        stats_file = self.stats_file()
        if os.path.exists(stats_file):
            if not os.access(stats_file, os.W_OK):
                log.warning("Failed to remove statistics file {}.".format(stats_file))
                return
            os.remove(stats_file)
