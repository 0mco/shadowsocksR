#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012-2015 clowwindy
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, \
    with_statement
import os, sys
import logging


file_dir = os.path.dirname(os.path.realpath(__file__))
log_dir = os.path.realpath(os.path.join(file_dir, '../log'))
if __name__ == '__main__':
    sys.path.insert(0, os.path.join(file_dir, '../../'))

# NOTE: add '../../' to path if you want to execute directly.
from shadowsocks.lib import shell
from shadowsocks.core import service


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='[%m-%d %H:%M]',
                    filename=os.path.join(log_dir, 'client.log'),
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


def main():
    shell.check_python()
    shell.startup_init()

    # fix py2exe
    if hasattr(sys, "frozen") and sys.frozen in \
            ("windows_exe", "console_exe"):
        p = os.path.dirname(os.path.realpath(sys.executable))
        os.chdir(p)

    s = service.Service()
    # FIXME: somehow a daemon cannot be killed, and cannot connect to it
    if not s.is_running():
        logging.info('starting daemon')
        s.start()
    else:
        logging.info('daemon already started')
    # s.start()
    service.Client().start()


if __name__ == '__main__':
    main()
