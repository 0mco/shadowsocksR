from shadowsocks.core import daemon, network, command
from shadowsocks.lib import shell, ssrlink
from shadowsocks.lib.config import ClientConfigManager
from shadowsocks.lib.ssrlink import decode_ssrlink
from shadowsocks.plugins.subscribe import fetch_ssr
from shadowsocks.lib.shell import print_server_info
import logging
from datetime import date
import signal


class Service:
    def __init__(self):
        self.config_manager = None
        self.config = None
        self.server_link = None
        pass


class Client(Service):
    def __init__(self):
        super().__init__()

    def start(self):
        args = shell.parse_args()
        signal.signal(shell.SIGNAL1, self.manager)
        # TODO: when receive SIGNAL1, read a temp file encoded by pickle to get args;
        # and then execute correspond commmand in this process.
        if args.command:
            if args.c:
                config_path = args.c
            else:
                config_path = shell.find_config(True)
            # In cmd mode, we always load config from config file.
            # And we intentionally do not parse_config for possibly missing some arguments.
            logging.debug('loading config from: {}'.format(config_path))
            self.config_manager = ClientConfigManager(config_path)
            if self.config_manager.get_auto_update_config() and \
                    (self.config_manager.get_last_update_time() != date.today().strftime('%Y-%m-%d')):
                logging.info('checking feed update')
                self.fetch_server_list()

            command.Commands(args.command, self, args)

        else:  # old procedure
            config = shell.parse_config(True)
            daemon.daemon_exec(config)
            self.network = network.ClientNetwork(config)
            self.network.start()

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
        self.print_server_list(servers, header='*' * 20 + "SERVER LIST AFTER UPDATE" + '*' * 20)

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
        if signum == shell.SIGNAL1:            # network error signal
            if self.config_manager.get_auto_switch_config():
                # move this server to dead group
                self.config_manager.set_server_dead(self.server_link)
                # switch ssr randomly if autoswitch is set.
                self.random_switch_ssr()
