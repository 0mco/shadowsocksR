from shadowsocks.lib.ssrlink import decode_ssrlink
from shadowsocks.lib import shell
from shadowsocks.core import daemon, network
from shadowsocks.lib.shell import print_server_info
import signal


class BaseCommands:
    """Abstract Commands class, subclass should call super.__init__(),
    and then initialize SUBCMDS, and at the end of __init__, call self.execute()."""
    def __init__(self, target, args):
        self.SUBCMDS = {}

    def execute(self, target, args):
        subcmd = args.subcmd.lower()
        if subcmd in self.SUBCMDS:
            self.SUBCMDS[subcmd](target, args)
        else:
            self._wrong_cmd(target, args)

    def _wrong_cmd(self, target, args):
        """handler fo wrong command, override by subclass."""
        print('cmd `{}` is not implemented yet'.format(args.subcmd))


class ServerCommands(BaseCommands):
    def __init__(self, target, args):
        super().__init__(target, args)
        subcmds = {
            'list': self.list,
            'switch': self.switch,
            'connect': self.connect,
            'autoswitch': self.autoswitch,
        }
        self.SUBCMDS.update(subcmds)
        self.execute(target, args)

    def list(self, target, args):
        ssrs = target.get_server_list()
        servers = [decode_ssrlink(ssr) for ssr in ssrs]
        header = ' ' * 40 + 'SERVER LIST' + ' ' * 40
        print_server_info(
            servers,
            header=header,
            indexed=True,
            verbose=True,
            hightlight=True)

    def switch(self, target, args):
        # When network error, switch ssr randomly
        # signal.signal(signal.SIGUSR1, self.random_switch_ssr)
        # test switch ssr
        ssrs = target.get_server_list()
        first = True
        import time
        for ssr in ssrs:
            config_from_link = decode_ssrlink(ssr)
            config = shell.parse_config(True, config_from_link)
            # config['daemon'] = 'start'
            print_server_info(config)
            if first:
                target.network = network.ClientNetwork(config)
                target.network.start()
                first = False
            else:
                target.network.switch(config)
            time.sleep(20)
        print('all ssr tested')

    def connect(self, target, args):
        ssr = target.get_server_list()[0]
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        daemon.daemon_exec(config)
        target.network = network.ClientNetwork(config)
        target.network.start()

    def autoswitch(self, target, args):
        # When network error, switch ssr randomly
        signal.signal(signal.SIGUSR1, target.random_switch_ssr)
        ssr = target.get_server_list()[0]
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        daemon.daemon_exec(config)
        print_server_info(config)
        target.network = network.ClientNetwork(config)
        target.network.start()


class FeedCommands(BaseCommands):
    SUBCMDS = ['fetch', 'add', 'list', 'remove']

    def __init__(self, target, args):
        super().__init__(target, args)
        subcmds = {
            'fetch': self.fetch,
            'add': self.add,
            'list': self.list,
            'remvoe': self.remove,
        }
        self.SUBCMDS.update(subcmds)
        self.execute(target, args)

    def fetch(self, target, args):
        target.fetch_server_list()

    def add(self, target, args):
        if not args.source:
            args.source = input('Please input source address:')
        target.add_feed_source(args.source)

    def list(self, target, args):
        sources = target.get_source_list()
        for source in sources:
            print(source)

    def remove(self, target, args):
        # print list, index by number, select number to remove.
        pass


class StatusCommands(BaseCommands):
    def __init__(self, target, args):
        super().__init__(target, args)
        self.execute(target, args)


class ConfigCommands(BaseCommands):
    def __init__(self, target, args):
        super().__init__(target, args)
        self.execute(target, args)
