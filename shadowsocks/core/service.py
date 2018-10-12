from shadowsocks.core import command
from shadowsocks.lib import shell, ssrlink
from shadowsocks.lib.config import ClientConfigManager
from shadowsocks.lib.ssrlink import decode_ssrlink
from shadowsocks.plugins.subscribe import fetch_ssr
from shadowsocks.lib.shell import print_server_info
import logging
from datetime import date
import signal
import socket
import os, sys
import errno
import threading
import socketserver
import time

logger = logging.getLogger('shadowsocksr')
# TODO: move config to config/global.py
HOST = '127.0.0.1'
PORT = 6113


class Service:
    def __init__(self, host=HOST, port=PORT):
        self.config_manager = None
        self.config = None
        self.server_link = None
        self.alarm_period = 20
        self.network = None
        self.service_server = None
        self.sock = None
        self.host = host
        self.port = port

    def execute(self, cmd, *args, **kwargs):
        return getattr(self, cmd)(*args, **kwargs)

    def start(self):
        service = self

        # class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        class ThreadedTCPServer(socketserver.TCPServer):
            def server_bind(self):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind(self.server_address)

        class RequestHandler(socketserver.BaseRequestHandler):
            # TODO: restore io fd when finished!!
            def handle(self):
                nonlocal service
                logger.info("new client:")

                # NOTE: if you want to use /dev/null, you need first open
                # the file, and then close fd 0, and finally dup2.
                # FIXME: daemon stdin/out/err error, maybe os.setsid() will help?
                os.close(0)
                os.close(1)
                # os.close(2)
                os.dup2(self.request.fileno(), 0)
                os.dup2(self.request.fileno(), 1)
                # os.dup2(self.request.fileno, 2)

                while True:
                    try:
                        while True:
                            request = input()
                            args, extra_args = shell.parse_args(request.split())
                            if args.command:
                                if args.c:
                                    config_path = args.c
                                else:
                                    config_path = shell.find_config(True)
                                # In cmd mode, we always load config from config file.
                                # And we intentionally do not parse_config for possibly missing some arguments.
                                logger.debug('loading config from: {}'.format(config_path))
                                service.config_manager = ClientConfigManager(config_path)
                                # TODO: check update after connection is established (using threading)
                                # if service.config_manager.get_auto_update_config() and \
                                #         (service.config_manager.get_last_update_time() != \
                                #           date.today().strftime('%Y-%m-%d')):
                                #    logging.info('checking feed update')
                                #    self.fetch_server_list()

                            print('executing: `%s %s`' % (args.command, args.subcmd), file=sys.stderr)
                            # execute in another thread, and using pipe to async direct output another fd,
                            # and send the output async to client
                            command.Commands(args.command, service, (args, extra_args))
                            print('execute `%s %s` done' % (args.command, args.subcmd), file=sys.stderr)

                    except (BrokenPipeError, ConnectionResetError, EOFError) as e:
                        print("connection lost", file=sys.stderr)
                        print(e)

                        _stdin = open('/dev/null', 'r')
                        _stdout = open('/dev/null', 'w')
                        os.close(0)
                        os.close(1)
                        # os.close(2)
                        os.dup2(_stdin.fileno(), 0)
                        os.dup2(_stdout.fileno(), 1)
                        # os.dup2(_stdout.fileno(), 2)
                        break
                    except Exception as e:
                        print(e, file=sys.stderr)
                        print("**[3]**", file=sys.stderr)
                        print(e)
                        logger.error(e)
                    # finally:

                print("connection lost", file=sys.stderr)

        # FIXME: why two copy of error output? and the format of info
        # and error level are different
        logger.info("binding on %s:%d" % (self.host, self.port))
        # logger.error("binding on %s:%d" % (self.host, self.port))
        try:
            # server = socketserver.TCPServer((self.host, self.port), RequestHandler)
            self.service_server = ThreadedTCPServer((self.host, self.port), RequestHandler)
            # FIXME: it seems that socketserver catch SystemExit?
            # sys.exit(0)
            # threading.Thread(target=server.serve_forever).start()
            self.service_server.serve_forever()

            # set timer for unix-like system:
            # NOTE: if not add SIGALRM to manager, program will auto quit somehow.

            # uncomment
            signal.signal(signal.SIGALRM, self.manager)

            # NOTE: 每次執行完網絡檢查後在重新設置alarm，而不是設置固定的interval，
            # 避免檢查時間過長導致段時間內高頻率檢查
            # signal.setitimer(signal.ITIMER_REAL, self.alarm_period, self.manager)

            # uncomment
            signal.alarm(self.alarm_period)
        except socket.error as e:
            logger.error(str(e))
            if e.errno != errno.EADDRINUSE:
                raise
        except Exception as e:
            print(e)

    def daemonize(self):
        # TODO: change the pid file, and add dedaemonize
        # args, extra_args = shell.parse_args()
        # shell.daemon_start('/tmp/zzz.pid')
        pass

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

    def print_server_list(self, ssrs, header=None, indexed=True, verbose=True, hightlight=True):
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
                logger.error('fetching server list in {} failed'.format(addr))
        servers = self.get_server_list(
        ) + servers  # 把本地的server列表(已經去重)放在前面，去重的時候效率更高

        i = len(servers) - 1
        while i >= 0:
            j = i - 1
            while 0 <= j < i < len(servers):
                if ssrlink.ssrlink_equal(servers[i], servers[j]):
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
        pass

    def random_switch_ssr(self):
        import random
        ssrs = self.get_server_list()
        ssr = random.choice(ssrs)
        config_from_link = decode_ssrlink(ssr)
        self.config = shell.parse_config(True, config_from_link)
        print_server_info(self.config, verbose=True, hightlight=True)
        self.network.switch(self.config)

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

    def manager(self, signum, frame):
        return
        if signum == signal.SIGALRM:
            # print('received timer alarm', time.ctime())
            # print('trying to ping baidu.com')
            # latency = self.ping('www.baidu.com', True)
            # print('latency to baidu.com is', latency)
            # if latency is None:
            #     self._throw_network_error_signal()

            if not self.connectivity():
                logger.info(
                    'Network error detected, trying to switch a server')
                self._throw_network_error_signal()
            signal.alarm(self.alarm_period)
