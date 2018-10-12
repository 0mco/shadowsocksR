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
    # FIXME: somehow a daemon cannot be killed, and cannot connect to it
    # if not s.is_running():
    #     logger.info('starting service')
    #     s.start()
    # else:
    #     logger.info('service already started')
    # logger.error('started')
    # client.Client().start()

    if s.is_running():
        client.Client().start()
    else:
        # args = shell.parse_args()[0]
        # if args.d:
        pid = os.fork()
        if pid > 0:     # parent
            import time
            time.sleep(3)
            client.Client().start()
        else:
            import signal
            os.setsid()         # detach from current session
            signal.signal(signal.SIGHUP, signal.SIG_IGN)        # handle terminal closed signal
            _stdin = open('/dev/null', 'r')
            # _stdout = open('/dev/null', 'w')
            _stdout = open('/tmp/x', 'w')
            # this is the wrong way!!
            # sys.stdin.close()
            # sys.stdout.close()
            # sys.stderr.close()
            os.close(0)
            os.close(1)
            os.close(2)
            os.dup2(_stdin.fileno(), 0)
            os.dup2(_stdout.fileno(), 1)
            os.dup2(_stdout.fileno(), 2)
            s.start()
        # else:                 # we cannot do the io tricks in one single process
        #     import threading
        #     import time
        #     threading.Thread(target=s.start).start()
        #     time.sleep(3)
        #     client.Client().start()


if __name__ == '__main__':
    main()
