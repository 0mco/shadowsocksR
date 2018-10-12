from shadowsocks.core import daemon, network, command
from shadowsocks.lib import shell, ssrlink
from shadowsocks.lib.config import ClientConfigManager
from shadowsocks.lib.ssrlink import decode_ssrlink
from shadowsocks.plugins.subscribe import fetch_ssr
from shadowsocks.lib.shell import print_server_info
from shadowsocks.core.command import ServerCommands
import logging
from datetime import date
import signal
import socket
import json
import os, sys
import errno
import threading
import socketserver
import time
import io
from contextlib import redirect_stdout
from contextlib import redirect_stderr
import argparse

# TODO: move config to config/global.py
HOST = '127.0.0.1'
PORT = 6113

logger = logging.getLogger('shadowsocksr')


class Client:
    def __init__(self, host=HOST, port=PORT):
        self.sock = None
        self.host = host
        self.port = port

    def connect_to_service(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.setblocking(False)
        # self.sock.settimeout(5)
        logger.info('connected to %s:%d' % (self.host, self.port))
        threading.Thread(target=self.retrive_output, args=(self.sock,), daemon=True).start()

    def retrive_output(self, sock):
        sock.settimeout(1)
        while True:
            try:
                while True:
                    time.sleep(0.2)
                    packet = sock.recv(4096)
                    print(packet.decode('utf-8'), end='')
            except socket.error as e:       # when no data can be received
                print('network error')
            except Exception as e:
                print('connection disconnected')
                print(e)

    def start(self):
        self.connect_to_service()
        # FIXME: clear exception (SystemExit) when using ctrl-c to exit 
        args, extra_args = shell.parse_args()
        if args.command:
            if args.c:
                config_path = args.c
            else:
                config_path = shell.find_config(True)
            # In cmd mode, we always load config from config file.
            # And we intentionally do not parse_config for possibly missing some arguments.
            logger.debug('loading config from: {}'.format(config_path))

            cmd = ' '.join(s for s in sys.argv[1:])
            self.execute(cmd)
            # print(*resp, sep='', end='')
            if not args.i:
                if args.d:
                    print('daemonizing')
                    # daemon.daemon_start('/tmp/y.pid')
                time.sleep(3)
                return
            while True:
                time.sleep(0.5)
                cmd = input(">>> ")
                if cmd == '':
                    continue
                if cmd == 'quit' or cmd == 'exit':
                    break
                self.execute(cmd)
            if args.d:
                print('daemonizing')
                daemon.daemon_start()

        else:  # old procedure
            config = shell.parse_config(True)
            self.network = network.ClientNetwork(config)
            self.network.start()

    def execute(self, req, timeout=20):
        self.sock.setblocking(True)
        # TODO: in Windows we should add '\r'?
        self.sock.send((req + '\n').encode('utf-8'))
        return
