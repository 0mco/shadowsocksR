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
PORT = 4113


class Service:
    def __init__(self, host=HOST, port=PORT):
        self.config_manager = None
        self.config = None
        self.server_link = None
        self.network = None
        self.sock = None
        self.host = host
        self.port = port

    def execute(self, cmd, *args, **kwargs):
        return getattr(self, cmd)(*args, **kwargs)

    def start(self):
        service = self

        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            def server_bind(self):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind(self.server_address)

        class RequestHandler(socketserver.BaseRequestHandler):
            def handle(self):
                nonlocal service
                logging.info("new client:")
                # logging.info("new client:", addr)
                while True:
                    try:
                        while True:
                            request = self.request.recv(4096).decode('utf-8')
                            if not request:
                                print('closed', file=sys.stderr)
                                break
                            output = io.StringIO()
                            # with redirect_stderr(output):
                            with open('/dev/null', 'w'):
                                with redirect_stdout(output):
                                    args = shell.parse_args(request.split())
                                    if args.command:
                                        if args.c:
                                            config_path = args.c
                                        else:
                                            config_path = shell.find_config(True)
                                        # In cmd mode, we always load config from config file.
                                        # And we intentionally do not parse_config for possibly missing some arguments.
                                        logging.debug('loading config from: {}'.format(config_path))
                                        service.config_manager = ClientConfigManager(config_path)
                                        # TODO: check update after connection is established
                                        # if service.config_manager.get_auto_update_config() and \
                                        #         (service.config_manager.get_last_update_time() != \
                                        #           date.today().strftime('%Y-%m-%d')):
                                        #    logging.info('checking feed update')
                                        #    self.fetch_server_list()

                                    print('executing: `%s %s`' % (args.command, args.subcmd), file=sys.stderr)
                                    # execute in another thread, and using pipe to async direct output another fd, and send the output async to client
                                    command.Commands(args.command, service, args)
                                    print('execute `%s %s` done' % (args.command, args.subcmd), file=sys.stderr)
                            resp = output.getvalue()
                            resp += '\n[DONE]\n'
                            # TODO: async sending data to client
                            self.request.sendall(resp.encode('utf-8'))
                            print(resp)
                            print('result sent', file=sys.stderr)
                    except ConnectionResetError:
                        print('peer closed', file=sys.stderr)
                        break
                    except Exception as e:
                        self.request.sendall(str(e).encode('utf-8'))
                        print(e)

        logging.info("binding on %s:%d" % (self.host, self.port))
        try:
            # server = socketserver.TCPServer((self.host, self.port), RequestHandler)
            server = ThreadedTCPServer((self.host, self.port), RequestHandler)
            threading.Thread(target=server.serve_forever).start()
        except socket.error as e:
            logging.error(str(e))
            if e.errno != errno.EADDRINUSE:
                raise
        except Exception as e:
            print(e)

    def add_feed_source(self, addr):
        self.config_manager.add_subscription(addr)
        self.fetch_server_list()
        # self.config_manager.fetch_server_list()

    def get_source_list(self):
        # self.config_manager.clear()
        sources = self.config_manager.get_subscription()
        return sources

    def get_server_list(self):
        servers = self.config_manager.get_server()
        return servers

    def get_dead_server_list(self):
        return self.config_manager.get_dead_server_list()

    def get_server_by_addr(self, addr):
        links = self.get_server_list()
        for link in links:
            server = ssrlink.decode_ssrlink(link)
            if server['server'] == addr:
                return link

    def print_server_list(self,
                          ssrs,
                          header=None,
                          indexed=True,
                          verbose=True,
                          hightlight=True):
        shell.print_server_info((decode_ssrlink(link) for link in ssrs))
        for ssr in ssrs:
            server = decode_ssrlink(ssr)
            print_server_info(server)

    def fetch_server_list(self):
        sources = self.config_manager.get_subscription()
        servers = []
        for addr in sources:
            try:
                servers.extend(fetch_ssr(addr))
            except Exception:
                logging.error('fetching server list in {} failed'.format(addr))
        servers = self.get_server_list(
        ) + servers  # 把本地的server列表(已經去重)放在前面，去重的時候效率更高

        i = len(servers) - 1
        while i >= 0:
            j = i - 1
            while 0 <= j < i < len(servers):
                if ssrlink.is_duplicated(servers[i], servers[j]):
                    del servers[i]
                    break
                else:
                    j -= 1
            i -= 1

        self.config_manager.update_server_list(servers)
        today = date.today().strftime('%Y-%m-%d')
        self.config_manager.set_last_update_time(today)
        self.print_server_list(
            servers, header='*' * 20 + "SERVER LIST AFTER UPDATE" + '*' * 20)

    def switch_ssr(self, config):
        self.network.pause()
        import time
        time.sleep(10)
        self.network.resume()

    def random_switch_ssr(self):
        import random
        ssrs = self.get_server_list()
        ssr = random.choice(ssrs)
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        print_server_info(config, verbose=True, hightlight=True)
        self.network.switch(config)

    def manager(self, signum, frame):
        if signum == shell.SIGNAL1:  # network error signal
            if self.config_manager.get_auto_switch_config():
                # move this server to dead group
                # self.config_manager.set_server_dead(self.server_link)
                # switch ssr randomly if autoswitch is set.
                self.random_switch_ssr()

    def is_running(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
            return False
        except socket.error as e:
            if e.errno != errno.EADDRINUSE:
                raise
            return True
        finally:
            sock.close()


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
        args = shell.parse_args()
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
                return
            while True:
                commands = input(">>> ")
                if commands == 'quit' or commands == 'exit':
                    exit(0)
                resp = self.request(commands)
                print(*resp, sep='', end='')

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
