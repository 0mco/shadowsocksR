from shadowsocks.core import eventloop, tcprelay, udprelay, asyncdns, daemon
from shadowsocks.lib import shell, socks
import socket
import logging
import time
import threading
import os
import sys
import signal


class Network:
    pass


class ClientNetwork(Network):
    def __init__(self, config=None, alarm_period=20):
        # initialize dns_resolver, loop
        self.tcp_server = None
        self.udp_server = None
        self.dns_resolver = None
        self.loop = None
        self.config = None
        self.loop_thread = None
        self.alarm_period = alarm_period
        self.loop = eventloop.EventLoop()
        self.dns_resolver = asyncdns.DNSResolver()
        self.dns_resolver.add_to_loop(self.loop)
        if config is not None:
            self.add(config)

    def add(self, config):
        # TODO: what would happen if more than one server added to the eventloop?
        self.config = config
        self.tcp_server = tcprelay.TCPRelay(config, self.dns_resolver, True)
        self.udp_server = udprelay.UDPRelay(config, self.dns_resolver, True)
        self.tcp_server.add_to_loop(self.loop)
        self.udp_server.add_to_loop(self.loop)

    def start(self):
        # since we have no good method to stop a thread, so we demand that
        # we can only start an eventloop, you need to stop the running
        # eventloop first to start.
        if self.loop_thread is not None:
            logging.error('already started')
            return
        assert self.loop is not None
        config = self.config

        if not config.get('dns_ipv6', False):
            asyncdns.IPV6_CONNECTION_SUPPORT = False

        logging.info(
            "local start with protocol [%s] password [%s] method [%s] obfs [%s] obfs_param [%s]"
            % (config['protocol'], config['password'], config['method'], config['obfs'], config['obfs_param']))

        try:
            logging.info("starting local at %s:%d" % (config['local_address'], config['local_port']))

            # uncomment
            # signal.signal(getattr(signal, 'SIGQUIT', signal.SIGTERM), self.manager)
            # signal.signal(signal.SIGINT, self.manager)

            daemon.set_user(config.get('user', None))

            # uncomment
            # signal.signal(shell.SIGNAL2, self.manager)

            if sys.platform == 'win32':
                # set timer for Windows:
                threading.Thread(target=self.period_network_check).start()
            else:
                # set timer for unix-like system:
                # NOTE: if not add SIGALRM to manager, program will auto quit somehow.

                # uncomment
                # signal.signal(signal.SIGALRM, self.manager)

                # NOTE: 每次執行完網絡檢查後在重新設置alarm，而不是設置固定的interval，
                # 避免檢查時間過長導致段時間內高頻率檢查
                # signal.setitimer(signal.ITIMER_REAL, self.alarm_period, self.manager)

                # uncomment
                # signal.alarm(self.alarm_period)
                pass

            threading.Thread(target=self.loop.run).start()
            latency = self.ping(config['server'], int(config['server_port']))
            print('network started')
            print('latency: {}'.format(latency))
        except Exception as e:
            shell.print_exception(e)
            sys.exit(1)

    def stop(self):  # TODO: use only one single to toggle pause/resume
        """close tcp_server, udp_server."""
        if (not self.loop_thread) or self.loop.is_stopped():
            logging.error('network not started')
            return
        # FIXME: what about really stop it?
        self.loop.pause()       # we just pause it, not really stop it
        self.tcp_server.close()     # it itself will remove itself from eventloop
        self.udp_server.close()
        logging.info('network stopped')

    def restart(self):
        # this naming is kind of misleading, since we just resume from pausing state
        self.loop.resume()
        print('network restarted')

    def switch(self, config):
        self.stop()
        # FIXME: why if we remove print here, it will throw address already in use error?
        # That's weird, or just a miracle?
        # logging.info('print it to prevent address already in use error')
        self.add(config)
        self.restart()

    def manager(self, signum, frame):
        # TODO: SIGNAL1 to toggle loop status, for saving limited SIGNAL numbers.
        # SIGNAL1 is for client to updat config, SIGNAL2 is for network to switch connection.
        if signum == shell.SIGNAL2:  # pause eventloop.
            if self.loop.is_paused():
                self.loop.resume()
            else:
                self.loop.pause()
                self.tcp_server.close()  # test use, just pause, not stop
                self.udp_server.close()
        elif signum == signal.SIGQUIT or signum == signal.SIGTERM:
            logging.warn('received SIGQUIT, doing graceful shutting down..')
            self.stop()
        elif signum == signal.SIGINT:
            sys.exit(1)

        elif signum == signal.SIGALRM:
            # print('received timer alarm', time.ctime())
            # print('trying to ping baidu.com')
            # latency = self.ping('www.baidu.com', True)
            # print('latency to baidu.com is', latency)
            # if latency is None:
            #     self._throw_network_error_signal()

            if not self.connectivity():
                logging.info(
                    'Network error detected, trying to switch a server')
                self._throw_network_error_signal()
            signal.alarm(self.alarm_period)

    def connectivity(self, hosts=None):
        """test connectivity to host (or hosts if iterable)."""
        if hosts is None:
            hosts = ['www.google.com', 'www.github.com', 'www.baidu.com']
        elif isinstance(hosts, str):
            hosts = [hosts]
        hosts = ['www.gogole.com']
        # otherwise we assume hosts is iterable.
        for i in range(3):
            # print('range', i)
            for host in hosts:
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, '127.0.0.1', 1080)
                s.settimeout(10)
                try:
                    s.connect((host, 80))
                    start_time = time.time()
                    s.sendall('GET / HTTP/1.1\nHost: {}\n\n'.format(host)
                              .encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        # print(data, time.time() - start_time)
                        return True
                except Exception:
                    pass
                finally:
                    s.close()
        return False

    def _throw_network_error_signal(self):
        os.kill(os.getpid(), shell.SIGNAL1)

    def ping(self, host, port, with_socks=False):
        """return None if cannnot connect."""
        latency = []
        for i in range(5):
            s = socks.socksocket()
            # FIXME: if set proxy, the connect time why is so small; and otherwise it's normal
            # 難道是那個時候並沒有真正連接？
            # s.setblocking(False)
            if with_socks is True:
                # s.set_proxy(socks.SOCKS5, '127.0.0.1', 1080)        # TODO: change to local addr/port
                s.set_proxy(socks.SOCKS5, self.config['local_address'],
                            self.config['local_port'])
            s.settimeout(2)
            # TODO: 解析ip，避免將解析ip的時間加入
            try:
                start_time = time.time()
                s.connect((host, port))
                s.send(b'0')
                latency_ = time.time() - start_time
                # print('latency to {}: {}'.format(host, latency_ * 1000))
                latency.append(latency_)
                # print('sleeping')
                # time.sleep(100)
            except Exception:
                # FIXME: socks module will not throw error even no network connection!!
                # So we need other way to detect connection failure.
                pass
            finally:
                s.close()
        # return None         # TODO: test use
        if not latency:
            return None
        else:
            return 1000 * sum(latency) / len(latency)

    def period_network_check(self):
        """this is for windows timer check."""
        time.sleep(self.alarm_period)
        if not self.connectivity():
            logging.error('Network error detected, tring to switch a server')
            # self._throw_network_error_signal()
            # TODO:
            # we directly switch here, do not send signal to service.
            # if self.config
        threading.Thread(target=self.period_network_check).start()
        sys.exit(0)


def ping(host, port):
    """return None if cannnot connect."""
    latency = []
    for i in range(5):
        s = socket.socket()
        s.settimeout(2)
        # TODO: 解析ip，避免將解析ip的時間加入
        try:
            start_time = time.time()
            s.connect((host, port))
            s.send(b'0')
            latency_ = time.time() - start_time
            latency.append(latency_)
        except Exception as e:
            # print(e)
            pass
        finally:
            s.close()
    if not latency:  # return inf if can not connect
        return float('inf')
    else:
        return 1000 * sum(latency) / len(latency)
