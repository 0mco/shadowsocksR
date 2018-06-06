from shadowsocks.lib.ssrlink import decode_ssrlink, encode_to_link
from shadowsocks.lib import shell
from shadowsocks.core import daemon, network
from shadowsocks.lib.shell import print_server_info
import signal


# won't work, because it will not automatically execute.
# def register(func):
#     def decorated(self, *args, **kwargs):
#         funcname = str(func).split('.')[1].split(' ')[0]
#         self.SUBCMDS.update({funcname: func})
#         print(self.SUBCMDS)
#         print('*' * 40)
#         return func(self, *args, **kwargs)
#
#     return decorated


class BaseCommands:
    """Abstract Commands class, subclass should call super.__init__(),
    and then initialize SUBCMDS, and at the end of __init__, call self.execute().
    All method that are not started with underline will be automatically added
    to self.SUBCMDS with the funciton name, if you want to use other name,
    you can update the self.SUBCMDS dict in your __init__()."""
    # TODO: automatically add function to SUBCMDS dict.
    def __init__(self, cmd, target, args):
        self.cmd = cmd
        self.target = target
        self.args = args
        self.SUBCMDS = {}

        for method in dir(self):
            if callable(getattr(self, method)) and not str.startswith(method, '_'):
                # funcname = method.split('.')[1].split(' ')[0]
                self.SUBCMDS.update({method: getattr(self, method)})
                # self.cmd.append(getattr(self, method))
        self.execute()

    def execute(self):
        # subcmd = args.subcmd.lower()
        cmd = self.cmd.lower()
        if cmd in self.SUBCMDS:
            self.SUBCMDS[cmd]()
        else:
            self._wrong_cmd()

    def _wrong_cmd(self):
        """handler fo wrong command, override by subclass."""
        print('command `{}` is not implemented yet'.format(self.cmd))
        print('those commands are currently implemented:', *self.SUBCMDS.keys())


class Commands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    # @register
    def server(self):
        target, args = self.target, self.args
        ServerCommands(args.subcmd, target, args)

    def feed(self):
        target, args = self.target, self.args
        FeedCommands(args.subcmd, target, args)

    def status(self):
        target, args = self.target, self.args
        if hasattr(args, 'subcmd'):
            StatusCommands(args.subcmd, target, args)
        else:
            StatusCommands('info', target, args)

    def config(self):
        target, args = self.target, self.args
        ConfigCommands(args.subcmd, target, args)


class ServerCommands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    def list(self):
        target = self.target
        ssrs = target.get_server_list()
        servers = [decode_ssrlink(ssr) for ssr in ssrs]
        header = ' ' * 40 + 'SERVER LIST' + ' ' * 40
        print_server_info(
            servers,
            header=header,
            indexed=True,
            verbose=True,
            hightlight=True)

    def switch(self):
        target = self.target
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

    def connect(self):
        target = self.target
        ssr = target.get_server_list()[0]
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        daemon.daemon_exec(config)
        target.network = network.ClientNetwork(config)
        target.network.start()

    def start(self):
        target = self.target
        # When network error, switch ssr randomly
        signal.signal(signal.SIGUSR1, target.random_switch_ssr)
        ssr = target.get_server_list()[0]
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        daemon.daemon_exec(config)
        print_server_info(config)
        target.network = network.ClientNetwork(config)
        target.network.start()

    def add(self):
        if self.args.L:
            link = self.args.L
        else:
            config = {}
            config['server'] = input('sever address:')
            config['server_port'] = input('sever port:')
            config['protocol'] = input('protocol:')
            config['method'] = input('method:')
            config['obfs'] = input('obfs:')
            config['password'] = input('password:')
            link = encode_to_link(config)
        self.target.config.add_server(link)

    def remove(self):
        pass

    def disconnect(self):
        pass


class FeedCommands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    def fetch(self):
        target = self.target
        target.fetch_server_list()

    def add(self):
        target, args = self.target, self.args
        if not args.source:
            args.source = input('Please input source address:')
        target.add_feed_source(args.source)

    def list(self):
        target = self.target
        sources = target.get_source_list()
        for source in sources:
            print(source)

    def remove(self):
        # print list, index by number, select number to remove.
        pass


class StatusCommands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    def info(self):
        print('this is status info')


class ConfigCommands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    def autostart(self):
        pass

    def autoswitch(self):
        pass

    def autoupdate(self):
        pass


def user_chooice(options, message):
    for i in range(len(options)):
        print('%-2d' % (i+1) + options[i])
    print(message)
    return input()
