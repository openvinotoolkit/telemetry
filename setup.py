#!/usr/bin/env python3

# Copyright (C) 2018-2021 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""
Use this script to create a wheel with the telemetry library code:
$ python setup.py sdist bdist_wheel
"""

from setuptools import setup
from setuptools.command.build_py import build_py
from src.main import Telemetry


class BuildCmd(build_py):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        return [
            (pkg, module, filename)
            for (pkg, module, filename) in modules
            if not filename.endswith('_test.py')
        ]


packages = ['openvino_telemetry', 'openvino_telemetry.backend', 'openvino_telemetry.utils']

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='openvino-telemetry',
      version=Telemetry.get_version(),
      author='Intel® Corporation',
      license='OSI Approved :: Apache Software License',
      author_email='openvino_pushbot@intel.com',
      description="OpenVINO™ Telemetry package for sending statistics with user's consent, used in combination "
                  "with other OpenVINO™ packages.",
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/openvinotoolkit/telemetry',
      packages=packages,
      package_dir={'openvino_telemetry': 'src'},
      py_modules=[],
      entry_points={
          'console_scripts': [
              'opt_in_out = openvino_telemetry.opt_in_out:main',
          ],
      },
      cmdclass={
          'build_py': BuildCmd,
      },
      classifiers=[
          'Programming Language :: Python :: 3',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
      ],
      install_requires=['requests>=2.20.0'],
      )
