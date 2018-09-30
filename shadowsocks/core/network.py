from shadowsocks.core import eventloop, tcprelay, udprelay, asyncdns, daemon
from shadowsocks.lib import shell, socks, ssrlink
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
        self.config = []
        self.servers = []
        self.loop_thread = None
        self.alarm_period = alarm_period
        self.loop = eventloop.EventLoop()
        self.dns_resolver = asyncdns.DNSResolver()
        self.dns_resolver.add_to_loop(self.loop)
        if config is not None:
            self.add(config)

    def add(self, config):
        # TODO: what would happen if more than one server added to the eventloop?
        self.config.append(config)

        logging.info('creating tcp, udp relay')
        tcp_server = tcprelay.TCPRelay(config, self.dns_resolver, True)
        logging.info('TCPRelay created')
        udp_server = udprelay.UDPRelay(config, self.dns_resolver, True)
        logging.info('UDPRelay created')
        tcp_server.add_to_loop(self.loop)
        udp_server.add_to_loop(self.loop)
        logging.info('tcprelay, udprelay added to loop')
        self.servers.append((config, tcp_server, udp_server))

    def start(self):
        # since we have no good method to stop a thread, so we demand that
        # we can only start an eventloop, you need to stop the running
        # eventloop first to start.
        if self.loop_thread is not None:
            logging.error('already started')
            return
        assert self.loop is not None
        config = self.config[-1]

        if not config.get('dns_ipv6', False):
            asyncdns.IPV6_CONNECTION_SUPPORT = False

        logging.info(
            "local start with protocol [%s] password [%s] method [%s] obfs [%s] obfs_param [%s]"
            % (config['protocol'], config['password'], config['method'], config['obfs'], config['obfs_param']))

        try:
            logging.info("starting local at %s:%d" % (config['local_address'], config['local_port']))

            daemon.set_user(config.get('user', None))

            self.loop_thread = threading.Thread(target=self.loop.run)
            self.loop_thread.start()
            latency = self.ping(config['server'], int(config['server_port']))
            print('network started')
            print('latency: {}'.format(latency))
        except Exception as e:
            shell.print_exception(e)
            sys.exit(1)

    def remove(self, config_to_remove):  # TODO: use only one single to toggle pause/resume
        """close tcp_server, udp_server."""
        print(self.loop_thread, self.loop.is_running())
        if (not self.loop_thread) or (not self.loop.is_running()):
            logging.error('network not started')
            return
        # FIXME: what about really stop it?
        if len(self.servers) == 0:
            print("no server started")
            return
        removed = False
        for i, (config, tcp_server, udp_server) in enumerate(self.servers):
            if ssrlink.config_equal(config, config_to_remove):
                self.servers.pop(i)
                tcp_server.close()     # it itself will remove itself from eventloop
                udp_server.close()
                logging.info('server removed')
                removed = True
        if not removed:
            print('server not found')

    def pause(self):
        self.loop.pause()

    def stop(self):
        while self.servers:
            self.remove(self.servers[-1][0])
        self.loop.stop()

    def resume(self):
        # this naming is kind of misleading, since we just resume from pausing state
        if not self.loop.is_paused():
            logging.error('network not paused')
            return
        self.loop.resume()
        print('network resumed')

    def switch(self, config):
        self.pause()       # we just pause it, not really stop it
        self.remove(self.servers[-1][0])
        # FIXME: why if we remove print here, it will throw address already in use error?
        # That's weird, or just a miracle?
        # logging.info('print it to prevent address already in use error')
        self.add(config)
        self.resume()

    def get_servers(self):
        return tuple(s[0] for s in self.servers)

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
        # os.kill(os.getpid(), shell.SIGNAL1)
        logging.error('network error')
        pass

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
                s.set_proxy(socks.SOCKS5, self.config[-1]['local_address'],
                            self.config[-1]['local_port'])
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
