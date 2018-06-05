from shadowsocks.core import eventloop, tcprelay, udprelay, asyncdns
from shadowsocks.lib import shell, network
from shadowsocks.lib.config import ClientConfigManager
from shadowsocks.lib.ssrlink import decode_ssrlink
from shadowsocks.lib import ssrlink
from shadowsocks.subscribe import fetch_ssr
from shadowsocks import daemon
import logging
import signal


class Service:
    def __init__(self):
        pass


class Client(Service):
    def __init__(self):
        super().__init__()
        self.commands = {'server': ServerCommands, 'feed': FeedCommands, 'status': StatusCommands}

    def start(self):
        args = shell.parse_args()
        # TODO: when receive SIGUSR1, read a temp file encoded by pickle to get args;
        # and then execute correspond commmand in this process.
        if args.command:
            if args.c:
                config_path = args.c
            else:
                config_path = shell.find_config(True)
            # In cmd mode, we always load config from config file.
            # And we intentionally do not parse_config for possibly missing some arguments.
            logging.debug('loading config from: {}'.format(config_path))
            self.config = ClientConfigManager(config_path)
            if args.command == 'feed':
                if args.subcmd == 'fetch':
                    self.fetch_server_list()
                elif args.subcmd == 'add':
                    if not args.source:
                        args.source = input('Please input source address:')
                    self.add_feed_source(args.source)
                elif args.subcmd == 'list':
                    sources = self.get_source_list()
                    for source in sources:
                        print(source)
                elif args.subcmd == 'remove':
                    # print list, index by number, select number to remove.
                    pass
            if args.command == 'server':
                if args.subcmd == 'list':
                    ssrs = self.get_server_list()
                    # for ssr in ssrs:
                    #     server = decode_ssrlink(ssr)
                    #     print_server_info(server)
                    servers = [decode_ssrlink(ssr) for ssr in ssrs]
                    header = ' ' * 40 + 'SERVER LIST' + ' ' * 40
                    print_server_info(servers, header=header, verbose=True, hightlight=True)
                elif args.subcmd == 'switch':
                    # When network error, switch ssr randomly
                    # signal.signal(signal.SIGUSR1, self.random_switch_ssr)
                    # test switch ssr
                    ssrs = self.get_server_list()
                    first = True
                    import time
                    for ssr in ssrs:
                        config_from_link = decode_ssrlink(ssr)
                        config = shell.parse_config(True, config_from_link)
                        # config['daemon'] = 'start'
                        print_server_info(config)
                        if first:
                            self.network = network.ClientNetwork(config)
                            self.network.start()
                            first = False
                        else:
                            self.network.switch(config)
                        time.sleep(20)
                    print('all ssr tested')
                elif args.subcmd == 'connect':
                    ssr = self.get_server_list()[0]
                    config_from_link = decode_ssrlink(ssr)
                    config = shell.parse_config(True, config_from_link)
                    daemon.daemon_exec(config)
                    self.network = network.ClientNetwork(config)
                    self.network.start()
                elif args.subcmd == 'autoswitch':
                    # When network error, switch ssr randomly
                    signal.signal(signal.SIGUSR1, self.random_switch_ssr)
                    ssr = self.get_server_list()[0]
                    config_from_link = decode_ssrlink(ssr)
                    config = shell.parse_config(True, config_from_link)
                    daemon.daemon_exec(config)
                    print_server_info(config)
                    self.network = network.ClientNetwork(config)
                    self.network.start()

                else:
                    print('other cmd is not implemented yet')
            if args.command == 'status':
                print('this is current status')
                pass

        else:                       # old procedure
            config = shell.parse_config(True)
            daemon.daemon_exec(config)
            self.network = network.ClientNetwork(config)
            self.network.start()

    def add_feed_source(self, addr):
        self.config.add_subscription(addr)
        self.fetch_server_list()
        # self.config.fetch_server_list()

    def get_source_list(self):
        # self.config.clear()
        sources = self.config.get_subscription()
        return sources

    def get_server_list(self):
        servers = self.config.get_server()
        return servers

    def print_server_list(self, ssrs):
        for ssr in ssrs:
            server = decode_ssrlink(ssr)
            print_server_info(server)

    def fetch_server_list(self):
        # TODO: 根據server addr/port鍋爐重複的， 如果參數不一樣的話挨個測試。
        sources = self.config.get_subscription()
        servers = []
        for addr in sources:
            try:
                servers.extend(fetch_ssr(addr))
            except Exception:
                logging.error('fetching server list in {} failed'.format(addr))
        servers = self.get_server_list() + servers      # 把本地的server列表(已經去重)放在前面，去重的時候效率更高

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

        self.config.update_server_list(servers)
        self.print_server_list(servers)

    def switch_ssr(self, config):
        self.network.pause()
        import time
        time.sleep(10)
        self.network.resume()

    def random_switch_ssr(self, signum, frame):
        import random
        ssrs = self.get_server_list()
        ssr = random.choice(ssrs)
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        print_server_info(config, verbose=True, hightlight=True)
        self.network.switch(config)

class Commands:
    COMMANDS = []
    def __init__(self, target, command):
        pass


class ServerCommands(Commands):
    SUBCMDS = []
    def __init__(self, target, command):
        pass


class FeedCommands(Commands):
    SUBCMDS = []
    def __init__(self, target, command):
        if command == 'fetch':
            print('executing fetch')


class StatusCommands(Commands):
    pass


def print_server_info(servers, header=None, verbose=False, hightlight=False):
    # server = decode_ssrlink(ssr)
    if hightlight:
        print('*' * 100)
    if header:
        print(header)
    if isinstance(servers, dict):       # a single server
        servers = [servers]
    for server in servers:
        if verbose:
            # print(server['server'], server['server_port'], server['password'].decode('utf-8'), server['remarks'], server['group'], server['protocol'], server['method'], server['obfs'])         # TODO: ping value check
            print(server['server'], server['server_port'], server['password'], server['remarks'], server['group'], server['protocol'], server['method'], server['obfs'])         # TODO: ping value check
        else:
            # print(server['server'], server['server_port'], server['password'].decode('utf-8'), server['remarks'], server['group'])
            print(server['server'], server['server_port'], server['password'], server['remarks'], server['group'])
    if hightlight:
        print('*' * 100)
