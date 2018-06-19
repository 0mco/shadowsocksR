from shadowsocks.lib.ssrlink import decode_ssrlink, encode_to_link
from shadowsocks.lib import shell
from shadowsocks.core import daemon, network
from shadowsocks.lib.shell import print_server_info

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
    and then initialize SUBCMDS, and at the end of __init__, call self._execute().
    All method that are not started with underline will be automatically added
    to self.SUBCMDS with the funciton name, if you want to use other name,
    you can update the self.SUBCMDS dict in your __init__()."""

    # TODO: automatically add function to SUBCMDS dict.

    def __init__(self, cmd, target, args):
        self.cmd = cmd
        self.target = target
        self.args = args
        if not hasattr(self, 'SUBCMDS'):
            self.SUBCMDS = {}

        for method in dir(self):
            if callable(getattr(self, method)) and not method.startswith('_'):
                if method not in self.SUBCMDS:
                    self.SUBCMDS.update({method: getattr(self, method)})
        self._execute()

    def _execute(self):
        # subcmd = args.subcmd.lower()
        cmd = self.cmd.lower()
        if cmd in self.SUBCMDS:
            self.SUBCMDS[cmd]()
        else:
            self._wrong_cmd()

    def _wrong_cmd(self):
        """handler fo wrong command, override by subclass."""
        print('command `{}` is not implemented yet'.format(self.cmd))
        print('those commands are currently implemented:',
              *self.SUBCMDS.keys())


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

    def _test_switch(self):
        target = self.target
        # When network error, switch ssr randomly
        # signal.signal(shell.SIGNAL1, self.random_switch_ssr)
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

    def switch(self):
        import os
        pid = daemon.get_daemon_pid()
        if pid is not None:
            os.kill(pid,
                    shell.SIGNAL1)  # notify process with this pid to switch
            # FIXME: it will switch only when autoswitch is set :(
        else:
            print('daemon not started')

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
        ssr = target.get_server_list()[0]

        # this latency to server is not a good choice to determine whether the connection speed via this server
        # best = (float('inf'), '')           # tuple of (latency, ssr-link)
        # for link in target.get_server_list():
        #     server_config = decode_ssrlink(link)
        #     latency = network.ping(server_config['server'], int(server_config['server_port']))
        #     print('server %s:%s\t\tlatency: %.2f' % (server_config['server'], server_config['server_port'], latency))
        #     if latency < best[0]:
        #         best = (latency, link)
        #     if latency == float('inf'):
        #         print('setting to dead')
        #         target.config_manager.set_server_dead(link)
        # if best[1] == '':
        #     raise RuntimeError('can not connect to any server')
        # ssr = best[1]

        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        target.config = config
        target.server_link = ssr
        if self.args.d:
            daemon.daemon_start()
        print_server_info(target.config, verbose=True, hightlight=True)
        target.network = network.ClientNetwork(target.config)
        target.network.start()

    def add(self):
        if self.args.L:
            link = self.args.L
        else:
            # config = {}
            # config['server'] = input('sever address:')
            # config['server_port'] = input('sever port:')
            # config['protocol'] = input('protocol:')
            # config['method'] = input('method:')
            # config['obfs'] = input('obfs:')
            # config['password'] = input('password:')
            config = shell.parse_config(True)
            link = encode_to_link(config)
            print(link)
            return
        self.target.config.add_server(link)

    def remove(self):
        server_list = self.target.config.get_server()
        choice = user_chooice(
            server_list,
            message='please input the number which you want to remove')
        choice = int(choice) - 1
        del server_list[choice]
        self.target.config.update_server_list(server_list)
        pass

    def stop(self):
        daemon.daemon_stop()

    def restart(self):
        self.stop()
        self.start()

    def status(self):
        """print network information (ping/connectivity) of servers."""
        pass

    def rediscover(self):
        target = self.target
        for link in target.get_dead_server_list():
            server_config = decode_ssrlink(link)
            latency = network.ping(server_config['server'],
                                   int(server_config['server_port']))
            print('server %s:%s\t\tlatency: %.2f' %
                  (server_config['server'], server_config['server_port'],
                   latency))
            if latency != float('inf'):
                print('move server to alive group')
                target.config_manager.set_server_valid(link)

    def filter(self):
        target = self.target
        for link in target.get_server_list():
            server_config = decode_ssrlink(link)
            latency = network.ping(server_config['server'],
                                   int(server_config['server_port']))
            print('server %s:%s\t\tlatency: %.2f' %
                  (server_config['server'], server_config['server_port'],
                   latency))
            if latency == float('inf'):
                print('move server to dead group')
                target.config_manager.set_server_dead(link)


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
    # TODO: maybe change command name to toggle
    def __init__(self, cmd, target, args):
        if not hasattr(self, 'SUBCMDS'):
            self.SUBCMDS = {'import': self._import}
        else:
            self.SUBCMDS.update({'import': self._import})
        # import is python keyword, we need toadd `import` command
        # manually to self.SUBCMDS.
        super().__init__(cmd, target, args)

    def autostart(self):
        # TODO: config autostart yes/no
        autostart = self.target.config.get_auto_startup_config()
        if autostart:
            self.target.config.cancel_auto_startup()
            print('set autostart')
        else:
            self.target.config.set_auto_startup()
            print('cancel autostart')

    def autoswitch(self):
        autoswitch = self.target.config.get_auto_switch_config()
        if autoswitch:
            self.target.config.cancel_auto_switch()
            print('set autoswitch')
        else:
            self.target.config.set_auto_switch()
            print('cancel autoswitch')

    def autoupdate(self):
        autoupdate = self.target.config.get_auto_update_config()
        if autoupdate:
            self.target.config.cancel_auto_update()
            print('set autoupdate')
        else:
            self.target.config.set_auto_update()
            print('cancel autoupdate')

    def _import(self):
        if not self.args.c:
            print('config file is not set')
        pass

    def export(self):
        pass


def user_chooice(options, message):
    # for i in range(len(options)):
    #     print('%-2d ' % (i+1) + options[i])
    print_server_info((decode_ssrlink(ssr) for ssr in options), indexed=True)
    print(message)
    return input()
