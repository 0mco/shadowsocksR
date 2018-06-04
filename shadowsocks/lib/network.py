from shadowsocks.core import eventloop, tcprelay, udprelay, asyncdns
from shadowsocks import daemon
from shadowsocks.lib import shell
import logging
import time
import threading
import os
import sys
import signal


class Network:
    def sigusr1_handler(self, signum, frame):
        pass

    def sigusr2_handler(self, signum, frame):
        pass


class ClientNetwork(Network):
    def __init__(self, config):
        # initialize dns_resolver, loop
        self.tcp_server = None
        self.udp_server = None
        self.dns_resolver = None
        self.loop = None
        self.config = None
        self.loop = eventloop.EventLoop()
        self.dns_resolver = asyncdns.DNSResolver()
        self.dns_resolver.add_to_loop(self.loop)
        if config is not None:
            self.init(config)

    def init(self, config):
        self.config = config
        self.tcp_server = tcprelay.TCPRelay(config, self.dns_resolver, True)
        self.udp_server = udprelay.UDPRelay(config, self.dns_resolver, True)
        self.tcp_server.add_to_loop(self.loop)
        self.udp_server.add_to_loop(self.loop)

    def start(self):
        assert self.loop is not None
        config = self.config

        if not config.get('dns_ipv6', False):
            asyncdns.IPV6_CONNECTION_SUPPORT = False

        logging.info(
            "local start with protocol [%s] password [%s] method [%s] obfs [%s] obfs_param [%s]"
            % (config['protocol'], config['password'], config['method'],
               config['obfs'], config['obfs_param']))

        try:
            logging.info("starting local at %s:%d" % (config['local_address'],
                                                      config['local_port']))

            signal.signal(getattr(signal, 'SIGQUIT', signal.SIGTERM), self.manager)
            signal.signal(signal.SIGINT, self.manager)

            daemon.set_user(config.get('user', None))

            # TODO: here, you will start.
            # write a manager for this try block.
            # update config
            # 用signal.alarm 定時更新

            signal.signal(signal.SIGUSR1, self.manager)
            signal.signal(signal.SIGUSR2, self.manager)
            threading.Thread(target=self.loop.run).start()
            # test use, test connection pause/resume/close
            # while True:
            #     time.sleep(5)
            #     os.kill(os.getpid(), signal.SIGUSR1)
            #     time.sleep(20)
            #     os.kill(os.getpid(), signal.SIGUSR1)
            #     time.sleep(40)
            # print('all done')

        except Exception as e:
            shell.print_exception(e)
            sys.exit(1)

    def stop(self):        # TODO: use only one single to toggle pause/resume
        """close tcp_server, udp_server."""
        os.kill(os.getpid(), signal.SIGUSR2)

    def restart(self):
        os.kill(os.getpid(), signal.SIGUSR2)

    def switch(self, config):
        self.stop()
        self.init(config)
        self.restart()
        pass

    def manager(self, signum, frame):
        # TODO: SIGUSR1 to toggle loop status, for saving limited SIGUSR numbers.
        # SIGUSR1 is for client to updat config, SIGUSR2 is for network to switch connection.
        if signum == signal.SIGUSR2:        # pause eventloop.
            if self.loop.is_paused():
                self.loop.resume()
            else:
                self.loop.pause()
                self.tcp_server.close()       # test use, just pause, not stop
                self.udp_server.close()
        elif signum == signal.SIGQUIT or signum == signal.SIGTERM:
            logging.warn('received SIGQUIT, doing graceful shutting down..')
            self.stop()
        elif signum == signal.SIGINT:
            sys.exit(1)
