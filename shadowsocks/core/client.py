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


class Client:
    def __init__(self, host=HOST, port=PORT):
        self.config_manager = None
        self.config = None
        self.server_link = None
        self.network = None
        self.sock = None
        self.host = host
        self.port = port

        self.connect_to_service()

    def connect_to_service(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.setblocking(False)
        # self.sock.settimeout(5)
        logging.info('connected to %s:%d' % (self.host, self.port))

    def start(self):
        # FIXME: clear exception (SystemExit) when using ctrl-c to exit 
        args, extra_args = shell.parse_args()
        if args.command:
            if args.c:
                config_path = args.c
            else:
                config_path = shell.find_config(True)
            # In cmd mode, we always load config from config file.
            # And we intentionally do not parse_config for possibly missing some arguments.
            logging.debug('loading config from: {}'.format(config_path))

            cmd = ' '.join(s for s in sys.argv[1:])
            resp = self.request(cmd)
            print(*resp, sep='', end='')
            if not args.i:
                if args.d:
                    print('daemonizing')
                    daemon.daemon_start('/tmp/y.pid')
                return
            while True:
                commands = input(">>> ")
                if commands == 'quit' or commands == 'exit':
                    break
                resp = self.request(commands)
                print(*resp, sep='', end='')
            if args.d:
                print('daemonizing')
                daemon.daemon_start()

        else:  # old procedure
            config = shell.parse_config(True)
            self.network = network.ClientNetwork(config)
            self.network.start()

    def request(self, req, timeout=20):
        self.sock.setblocking(True)
        self.sock.send(req.encode('utf-8'))
        resp = []

        # FIXME: exit if any connection problem
        # TODO: 'ACK' as marker for start communication and acception, 'FIN' as communication end
        _READ = False
        self.sock.settimeout(0.1)
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                packet = self.sock.recv(4096)
                resp.append(packet.decode('utf-8'))
                if not _READ:
                    _READ = True
                    self.sock.setblocking(False)
            except socket.error as e:       # when no data can be received
                if not _READ:
                    pass
                else:
                    break
        return resp if resp else ('timeout\n')
