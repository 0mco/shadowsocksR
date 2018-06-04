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
        if config is not None:
            self.config(config)

    def config(self, config):
        self.config = config
        self.dns_resolver = asyncdns.DNSResolver()
        self.tcp_server = tcprelay.TCPRelay(config, self.dns_resolver, True)
        self.udp_server = udprelay.UDPRelay(config, self.dns_resolver, True)
        self.loop = eventloop.EventLoop()
        self.dns_resolver.add_to_loop(self.loop)
        self.tcp_server.add_to_loop(self.loop)
        self.udp_server.add_to_loop(self.loop)

    def start(self):
        assert self.loop is not None
        config = self.config

        if not config.get('dns_ipv6', False):
            asyncdns.IPV6_CONNECTION_SUPPORT = False

        daemon.daemon_exec(config)          # TODO: move daemon to service
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
            # while True:
            #     time.sleep(5)
            #     os.kill(os.getpid(), signal.SIGUSR1)
            #     time.sleep(20)
            #     os.kill(os.getpid(), signal.SIGUSR2)
            #     time.sleep(40)
            print('all done')

            # loop.run()
        except Exception as e:
            shell.print_exception(e)
            sys.exit(1)

    def stop(self):
        os.kill(os.getpid(), signal.SIGUSR1)

    def resume(self):
        os.kill(os.getpid(), signal.SIGUSR2)

    def manager(self, signum, frame):
        # TODO: SIGUSR1 to toggle loop status, for saving limited SIGUSR numbers.
        if signum == signal.SIGUSR1:        # pause eventloop.
            self.loop.pause()
            self.tcp_server.close()
            self.udp_server.close()
        elif signum == signal.SIGUSR2:        # rersume eventloop.
            self.loop.resume()
            self.tcp_server = tcprelay.TCPRelay(self.config, self.dns_resolver, True)
            self.udp_server = udprelay.UDPRelay(self.config, self.dns_resolver, True)
            self.tcp_server.add_to_loop(self.loop)
            self.udp_server.add_to_loop(self.loop)
        elif signum == signal.SIGQUIT or signum == signal.SIGTERM:
            logging.warn('received SIGQUIT, doing graceful shutting down..')
            self.tcp_server.close(next_tick=True)
            self.udp_server.close(next_tick=True)
        elif signum == signal.SIGINT:
            sys.exit(1)
