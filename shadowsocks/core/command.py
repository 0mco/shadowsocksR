from shadowsocks.lib.ssrlink import decode_ssrlink, encode_to_link
from shadowsocks.lib import ssrlink
from shadowsocks.lib import shell
from shadowsocks.core import network
from shadowsocks.lib.shell import print_server_info
import sys
import logging

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


logger = logging.getLogger('shadowsocksr')


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
        self.args, self.extra_args = args
        # self.args = args
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
            self._cmd_error()

    def _cmd_error(self):
        """handler fo wrong command, override by subclass."""
        print('command `{}` is not implemented yet'.format(self.cmd))
        print('currently implemented commands:',
              *self.SUBCMDS.keys())


class Commands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    # @register
    def server(self):
        target, args = self.target, self.args
        ServerCommands(args.subcmd, target, (self.args, self.extra_args))

    def feed(self):
        target, args = self.target, self.args
        FeedCommands(args.subcmd, target, (self.args, self.extra_args))

    def status(self):
        target, args = self.target, self.args
        if hasattr(args, 'subcmd'):
            StatusCommands(args.subcmd, target, (self.args, self.extra_args))
        else:
            StatusCommands('info', target, (self.args, self.extra_args))

    def config(self):
        target, args = self.target, self.args
        ConfigCommands(args.subcmd, target, (self.args, self.extra_args))

    def service(self):
        target, args = self.target, self.args
        ServiceCommands(args.subcmd, target, (self.args, self.extra_args))


class ServerCommands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    def list(self):
        target = self.target
        ssrs = target.get_server_list()
        servers = [decode_ssrlink(ssr) for ssr in ssrs]
        header = ' ' * 40 + 'SERVER LIST' + ' ' * 40
        print_server_info(servers, header=header, indexed=True, verbose=True, hightlight=True)

    def switch(self):
        self.target.random_switch_ssr()

    def connect(self):
        target = self.target
        if self.extra_args:
            try:
                ssr = target.get_server_list()[int(self.extra_args[0]) - 1]
            except ValueError as e:
                print(e)
                return
        else:
            ssr = target.get_server_list()[0]
        config_from_link = decode_ssrlink(ssr)
        config = shell.parse_config(True, config_from_link)
        target.config = config
        target.server_link = ssr
        print_server_info(target.config, verbose=True, hightlight=True)
        if target.network is None:
            print('creating ClientNetwork')
            target.network = network.ClientNetwork(target.config)
            target.network.start()
        else:
            print('ClientNetwork already exists')
            target.network.add(target.config)

    def disconnect(self):
        connected_servers = self.target.network.get_servers()
        if self.extra_args:
            try:
                choice = int(self.extra_args[0]) - 1
            except ValueError as e:
                print(e)
                return
        else:
            choice = user_chooice(connected_servers, message='please input the number which you want to disconnect')
            choice = int(choice) - 1
        self.target.network.remove(connected_servers[choice])

    def add(self):
        if self.args.L:
            link = self.args.L
        elif self.extra_args and ssrlink.is_valide_ssrlink(self.extra_args[0]):
            link = self.extra_args[0]
        else:
            config = shell.parse_config(True)
            link = encode_to_link(config)
            print(link)
        self.target.config.add_server(link)

    def remove(self):
        server_list = self.target.get_server_list()
        if self.extra_args:
            try:
                choice = int(self.extra_args[0]) - 1
            except ValueError as e:
                print(5)
                print(e)
                return
        else:
            choice = user_chooice(server_list, message='please input the number which you want to remove')
            choice = int(choice) - 1
        print_server_info(decode_ssrlink(server_list[choice]), verbose=True, hightlight=True)
        del server_list[choice]
        self.target.config_manager.update_server_list(server_list)
        # answer = input('you want to remove it from server list?\n')
        # if answer == 'y':
        #     del server_list[choice]
        #     self.target.config.update_server_list(server_list)
        #     print('removed it')
        # else:
        #     print('nothing done')

    def stop(self):
        # FIXME: assert started first
        # TODO: server.shutdown(), server.close()
        self.target.network.stop()

    def restart(self):
        self.stop()
        self.start()

    def quit(self):
        """quit the daemon"""
        pass

    def status(self):
        """print network information (ping/connectivity) of servers."""
        # print(self.target.config, self.target.server_link)
        if not self.target.network:
            print('no server connected to')
            return
        connected_servers = self.target.network.get_servers()
        print_server_info(connected_servers)

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


class ServiceCommands(BaseCommands):
    def __init__(self, cmd, target, args):
        super().__init__(cmd, target, args)

    def stop(self):
        pass

    def start(self):
        pass

    def restart(self):
        pass

    def daemonize(self):
        pass

    def quit(self):
        # FIXME: how to exit in socketserver?!!
        print('exiting')
        self.target.service_server.shutdown()
        logger.info('service exiting')
        import os
        os._exit()
        try:
            # sys.exit(0)
            import os
            os._exit()
            pass
        except SystemExit:
            print("**[17]**", file=sys.stderr)
            pass


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
        autostart = self.target.config_manager.get_auto_startup_config()
        if autostart:
            self.target.config_manager.cancel_auto_startup()
            print('set autostart')
        else:
            self.target.config_manager.set_auto_startup()
            print('cancel autostart')

    def autoswitch(self):
        autoswitch = self.target.config_manager.get_auto_switch_config()
        if autoswitch:
            self.target.config_manager.cancel_auto_switch()
            print('set autoswitch')
        else:
            self.target.config_manager.set_auto_switch()
            print('cancel autoswitch')

    def autoupdate(self):
        autoupdate = self.target.config_manager.get_auto_update_config()
        if autoupdate:
            self.target.config_manager.cancel_auto_update()
            print('set autoupdate')
        else:
            self.target.config_manager.set_auto_update()
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
    print_server_info((decode_ssrlink(ssr) if isinstance(ssr, str) else ssr for ssr in options), indexed=True)
    print(message)
    return input()
