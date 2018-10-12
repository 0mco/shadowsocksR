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
import time
import signal

file_dir = os.path.dirname(os.path.realpath(__file__))
log_dir = os.path.realpath(os.path.join(file_dir, '../log'))
if __name__ == '__main__':
    sys.path.insert(0, os.path.join(file_dir, '../../'))

# NOTE: add '../../' to path if you want to execute directly.
from shadowsocks.lib import shell
from shadowsocks.core import service, client

logger = logging.getLogger('shadowsocksr')


def main():
    shell.check_python()
    shell.startup_init()

    # fix py2exe
    if hasattr(sys, "frozen") and sys.frozen in \
            ("windows_exe", "console_exe"):
        p = os.path.dirname(os.path.realpath(sys.executable))
        os.chdir(p)

    s = service.Service()

    if s.is_running():
        client.Client().start()
    else:
        pid = os.fork()
        if pid > 0:     # parent
            time.sleep(3)           # waiting for service to start
            del s
            client.Client().start()
        else:
            os.setsid()         # detach from current session
            signal.signal(signal.SIGHUP, signal.SIG_IGN)        # handle terminal closed signal
            _input = open('/dev/null', 'r')
            # _stdout = open('/dev/null', 'w')
            # FIXME: replace with /dev/null
            _output = open('/tmp/shadowsocks_output', 'w')
            os.close(0)
            os.close(1)
            os.close(2)
            os.dup2(_input.fileno(), 0)
            os.dup2(_output.fileno(), 1)
            os.dup2(_output.fileno(), 2)
            s.start()


if __name__ == '__main__':
    main()
