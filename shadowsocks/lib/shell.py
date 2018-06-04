#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2015 clowwindy
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, \
    with_statement

import os
import json
import sys
import getopt
import argparse
import logging
from shadowsocks.core.common import to_bytes, to_str, IPNetwork, PortRange
from shadowsocks.core import encrypt
from shadowsocks.lib.ssrlink import decode_ssrlink

VERBOSE_LEVEL = 5

verbose = 0


def check_python():
    info = sys.version_info
    if info[0] == 2 and not info[1] >= 6:
        print('Python 2.6+ required')
        sys.exit(1)
    elif info[0] == 3 and not info[1] >= 3:
        print('Python 3.3+ required')
        sys.exit(1)
    elif info[0] not in [2, 3]:
        print('Python version not supported')
        sys.exit(1)


def print_exception(e):
    global verbose
    logging.error(e)
    if verbose > 0:
        import traceback
        traceback.print_exc()


def __version():
    version_str = ''
    try:
        import pkg_resources
        version_str = pkg_resources.get_distribution('shadowsocks').version
    except Exception:
        try:
            from shadowsocks import version
            version_str = version.version()
        except Exception:
            pass
    return version_str


def print_shadowsocks():
    print('ShadowsocksR %s' % __version())


def log_shadowsocks_version():
    logging.info('ShadowsocksR %s' % __version())


def find_config(cmd_mode=False):
    file_dir = os.path.dirname(os.path.abspath(__file__))
    if cmd_mode:

        return os.path.abspath(os.path.join(file_dir, '../config/client_config.json'))
    else:
        user_config_path = 'user-config.json'
        config_path = 'config.json'

        def sub_find(file_name):
            if os.path.exists(file_name):
                return file_name
            file_name = os.path.join(os.path.abspath('..'), file_name)
            return file_name if os.path.exists(file_name) else None

        return sub_find(user_config_path) or sub_find(config_path)


def check_config(config, is_local):
    if config.get('daemon', None) == 'stop':
        # no need to specify configuration for daemon stop
        return

    if is_local and not config.get('password', None):
        logging.error('password not specified')
        print_help(is_local)
        sys.exit(2)

    if not is_local and not config.get('password', None) \
            and not config.get('port_password', None):
        logging.error('password or port_password not specified')
        print_help(is_local)
        sys.exit(2)

    if 'local_port' in config:
        config['local_port'] = int(config['local_port'])

    if 'server_port' in config and type(config['server_port']) != list:
        config['server_port'] = int(config['server_port'])

    if config.get('local_address', '') in [b'0.0.0.0']:
        logging.warning(
            'warning: local set to listen on 0.0.0.0, it\'s not safe')
    if config.get('server', '') in ['127.0.0.1', 'localhost']:
        logging.warning('warning: server set to listen on %s:%s, are you sure?'
                        % (to_str(config['server']), config['server_port']))
    if config.get('timeout', 300) < 100:
        logging.warning('warning: your timeout %d seems too short' % int(
            config.get('timeout')))
    if config.get('timeout', 300) > 600:
        logging.warning('warning: your timeout %d seems too long' % int(
            config.get('timeout')))
    if config.get('password') in [b'mypassword']:
        logging.error('DON\'T USE DEFAULT PASSWORD! Please change it in your '
                      'config.json!')
        sys.exit(1)
    if config.get('user', None) is not None:
        if os.name != 'posix':
            logging.error('user can be used only on Unix')
            sys.exit(1)

    encrypt.try_cipher(config['password'], config['method'])


def parse_config(is_local, config_=None):
    global verbose
    global config
    global config_path
    # config = {}
    # config_path = None
    logging.basicConfig(
        level=logging.INFO, format='%(levelname)-s: %(message)s')
    if is_local:  # check this is a client or a server.
        shortopts = 'hd:s:b:p:k:l:m:O:o:G:g:c:t:L:vq'
        longopts = [
            'help', 'fast-open', 'link', 'pid-file=', 'log-file=', 'user=',
            'version'
        ]
    else:
        shortopts = 'hd:s:p:k:m:O:o:G:g:c:t:vq'
        longopts = [
            'help', 'fast-open', 'pid-file=', 'log-file=', 'workers=',
            'forbidden-ip=', 'user=', 'manager-address=', 'version'
        ]
    if config_:
        config.update(config_)
    else:
        args = parse_args()

    config['password'] = to_bytes(config.get('password', b''))
    config['method'] = to_str(config.get('method', 'aes-256-cfb'))
    config['protocol'] = to_str(config.get('protocol', 'origin'))
    config['protocol_param'] = to_str(config.get('protocol_param', ''))
    config['obfs'] = to_str(config.get('obfs', 'plain'))
    config['obfs_param'] = to_str(config.get('obfs_param', ''))
    config['port_password'] = config.get('port_password', None)
    config['additional_ports'] = config.get('additional_ports', {})
    config['additional_ports_only'] = config.get('additional_ports_only',
                                                 False)
    config['timeout'] = int(config.get('timeout', 300))
    config['udp_timeout'] = int(config.get('udp_timeout', 120))
    config['udp_cache'] = int(config.get('udp_cache', 64))
    config['fast_open'] = config.get('fast_open', False)
    config['workers'] = config.get('workers', 1)
    config['pid-file'] = config.get('pid-file', '/var/run/shadowsocksr.pid')
    config['log-file'] = config.get('log-file', '/var/log/shadowsocksr.log')
    config['verbose'] = config.get('verbose', False)
    config['connect_verbose_info'] = config.get('connect_verbose_info', 0)
    config['local_address'] = to_str(config.get('local_address', '127.0.0.1'))
    config['local_port'] = config.get('local_port', 1080)
    if is_local:
        # FIXME: enable not provide server addr if daemon stop or restart
        # if config.get('server', None) is None and not args.command and (not args.d or args.d == 'starat'):
        if config.get('server', None) is None:
            logging.error('server addr not specified')
            print_local_help()
            sys.exit(2)
        else:
            config['server'] = to_str(config['server'])
    else:
        config['server'] = to_str(config.get('server', '0.0.0.0'))
        try:
            config['forbidden_ip'] = \
                IPNetwork(config.get('forbidden_ip', '127.0.0.0/8,::1/128'))
        except Exception as e:
            logging.error(e)
            sys.exit(2)
        try:
            config['forbidden_port'] = PortRange(
                config.get('forbidden_port', ''))
        except Exception as e:
            logging.error(e)
            sys.exit(2)
        try:
            config['ignore_bind'] = \
                IPNetwork(config.get('ignore_bind', '127.0.0.0/8,::1/128,10.0.0.0/8,192.168.0.0/16'))
        except Exception as e:
            logging.error(e)
            sys.exit(2)
    config['server_port'] = config.get('server_port', 8388)

    logging.getLogger('').handlers = []
    logging.addLevelName(VERBOSE_LEVEL, 'VERBOSE')
    if config['verbose'] >= 2:
        level = VERBOSE_LEVEL
    elif config['verbose'] == 1:
        level = logging.DEBUG
    elif config['verbose'] == -1:
        level = logging.WARN
    elif config['verbose'] <= -2:
        level = logging.ERROR
    else:
        level = logging.INFO
    verbose = config['verbose']
    logging.basicConfig(
        level=level,
        format=
        '%(asctime)s %(levelname)-8s %(filename)s:%(lineno)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    check_config(config, is_local)

    return config


def parse_args(args_=None):
    # FIXME: called twice, service, parse_config
    def args_error(message):        # TODO: print help information when invalid arguments
        nonlocal parser
        sys.stderr.write('error: %s\n'.format(message))
        print('something wrong')
        parser.print_help()

    parser = argparse.ArgumentParser(description='A fast tunnel proxy that helps you bypass firewalls.', usage='ssclient command [OPTION]', epilog='Online help: <https://github.com/shadowsocks/shadowsocks>')
    # TODO: add conflicts of -L with others.
    # default to old version config path, if args.command is set, change it to new version config path
    parser.add_argument('-c', metavar='CONFIG', help='path to config file')
    parser.add_argument('-s', metavar='SERVER_ADDR', help='server address')
    parser.add_argument('-p', metavar='SERVER_PORT', help='server port', default='8388')
    parser.add_argument('-b', metavar='LOCAL_ADDR', help='local address', default='127.0.0.1')
    parser.add_argument('-l', metavar='LOCAL_PORT', help='local port', default='1080')
    parser.add_argument('-k', metavar='PASSWORD', help='password')
    parser.add_argument('-m', metavar='METHOD', help='encryption method', default='aes-256-cfb')
    parser.add_argument('-O', metavar='PROTOCOL', help='protocol', default='http_simple')
    parser.add_argument('-G', metavar='PROTOCOL_PARAM', help='protocol param', default='')
    parser.add_argument('-o', metavar='OBFS', help='obfsplugin', default='http_simple')
    parser.add_argument('-g', metavar='OBFS_PARAM', help='obfs param', default='')
    parser.add_argument('-L', metavar='SSR_LINK', help='connect using ssr link')
    parser.add_argument('-t', metavar='TIMEOUT', help='timeout in seconds', default=300)
    parser.add_argument('--fast-open', action='store_true', help='use TCP_FAST_OPEN, requires Linux 3.7+')
    parser.add_argument('-d', metavar='', help='daemon mode (start/stop/restart)', choices=['start', 'stop', 'restart'])
    parser.add_argument('--pid-file', metavar='PID_FILE', help='pid file for daemon mode')
    parser.add_argument('--log-file', metavar='LOG_FILE', help='log file daemon mode')
    parser.add_argument('--user', metavar='USER', help='run as user')
    parser.add_argument('--workers', metavar='WORKERS', default=1)
    parser.add_argument('-v', '-vv', action='count', help='verbose mode', default=0)
    parser.add_argument('-q', '-qq', action='count', help='quiet mode')
    parser.add_argument('--version', metavar='version', help='show version information')

    subparsers = parser.add_subparsers(dest='command', help='sub-commands')
    server_parser = subparsers.add_parser('server', help='xxx')
    feed_parser = subparsers.add_parser('feed', help='yyy')
    status_parser = subparsers.add_parser('status', help='show current status')

    server_parser.add_argument('subcmd', help='server command')
    feed_parser.add_argument('--link', help='ssr link')     # TODO: if no link, ask later.
    feed_parser.add_argument('subcmd', help='subscription command')
    feed_parser.add_argument('--source', help='souurce address')
    status_parser.add_argument('subcmd', help='show current status')

    if args_:
        args = parser.parse_args(args_)
    else:
        args = parser.parse_args()

    global verbose
    global config
    config = {}
    global config_path
    config_path = None
    logging.basicConfig(
        level=logging.INFO, format='%(levelname)-s: %(message)s')
    if args.version:
        print_shadowsocks()
        sys.exit(0)

    if args.c:
        # FIXME: enable default config_path
        if args.command:
            # if args.c == 'default':
            #     config_path = find_config(True)
            # else:
            config_path = args.c
        else:
            # if args.c == 'default':
            #     config_path = find_config(False)
            # else:
            config_path = args.c
            logging.debug('loading config from %s' % config_path)
            with open(config_path, 'rb') as f:
                try:
                    config = parse_json_in_str(
                        remove_comment(f.read().decode('utf8')))
                except ValueError as e:
                    logging.error('found an error in config.json: %s', str(e))
                    sys.exit(1)
    if config_path:
        config['config_path'] = config_path
    else:
        config['config_path'] = find_config(args.command)

    if args.p:
        config['server_port'] = int(args.p)
    if args.k:
        config['password'] = to_bytes(args.k)
    if args.l:
        config['local_port'] = int(args.l)
    if args.s:
        config['server'] = to_str(args.s)
    if args.m:
        config['method'] = to_str(args.m)
    if args.O:
        config['protocol'] = to_str(args.O)
    if args.o:
        config['obfs'] = to_str(args.o)
    if args.G:
        config['protocol_param'] = to_str(args.G)
    if args.g:
        config['obfs_param'] = to_str(args.g)
    if args.b:
        config['local_address'] = to_str(args.b)
    if args.t:
        config['timeout'] = int(args.t)
    # FIXME:
    # if key == '--fast-open':
    #     config['fast_open'] = True
    if args.workers:
        config['workers'] = int(args.workers)
    # FIXME:
    # if key == '--manager-address':
    #     config['manager_address'] = value
    if args.user:
        config['user'] = to_str(args.user)
    # FIXME:
    # if key == '--forbidden-ip':
    #     config['forbidden_ip'] = to_str(value)
    if args.d:
        config['daemon'] = to_str(args.d)
    # FIXME:
    # if key == '--pid-file':
    #     config['pid-file'] = to_str(value)
    # FIXME:
    # if key == '--log-file':
    #     config['log-file'] = to_str(value)
    config['verbose'] = args.v
    if args.q:
        config['verbose'] -= 1
    if args.L:
        config_from_ssrlink = decode_ssrlink(args.L)
        config.update(config_from_ssrlink)

    return args


def print_help(is_local):
    if is_local:
        print_local_help()
    else:
        print_server_help()


def print_local_help():
    print('''A fast tunnel proxy that helps you bypass firewalls.
usage: sslocal [OPTION]...
You can supply configurations via either config file or command line arguments.

Proxy options:
  -c CONFIG              path to config file
  -s SERVER_ADDR         server address
  -p SERVER_PORT         server port, default: 8388
  -b LOCAL_ADDR          local binding address, default: 127.0.0.1
  -l LOCAL_PORT          local port, default: 1080
  -k PASSWORD            password
  -m METHOD              encryption method, default: aes-256-cfb
  -o OBFS                obfsplugin, default: http_simple
  -t TIMEOUT             timeout in seconds, default: 300
  --fast-open            use TCP_FASTOPEN, requires Linux 3.7+

General options:
  -h, --help             show this help message and exit
  -d start/stop/restart  daemon mode
  --pid-file PID_FILE    pid file for daemon mode
  --log-file LOG_FILE    log file for daemon mode
  --user USER            username to run as
  -v, -vv                verbose mode
  -q, -qq                quiet mode, only show warnings/errors
  --version              show version information

Online help: <https://github.com/shadowsocks/shadowsocks>
''')


def print_server_help():
    print('''usage: ssserver [OPTION]...
A fast tunnel proxy that helps you bypass firewalls.

You can supply configurations via either config file or command line arguments.

Proxy options:
  -c CONFIG              path to config file
  -s SERVER_ADDR         server address, default: 0.0.0.0
  -p SERVER_PORT         server port, default: 8388
  -k PASSWORD            password
  -m METHOD              encryption method, default: aes-256-cfb
  -o OBFS                obfsplugin, default: http_simple
  -t TIMEOUT             timeout in seconds, default: 300
  --fast-open            use TCP_FASTOPEN, requires Linux 3.7+
  --workers WORKERS      number of workers, available on Unix/Linux
  --forbidden-ip IPLIST  comma seperated IP list forbidden to connect
  --manager-address ADDR optional server manager UDP address, see wiki

General options:
  -h, --help             show this help message and exit
  -d start/stop/restart  daemon mode
  --pid-file PID_FILE    pid file for daemon mode
  --log-file LOG_FILE    log file for daemon mode
  --user USER            username to run as
  -v, -vv                verbose mode
  -q, -qq                quiet mode, only show warnings/errors
  --version              show version information

Online help: <https://github.com/shadowsocks/shadowsocks>
''')


def _decode_list(data):
    rv = []
    for item in data:
        if hasattr(item, 'encode'):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.items():
        if hasattr(value, 'encode'):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


class JSFormat:
    def __init__(self):
        self.state = 0

    def push(self, ch):
        ch = ord(ch)
        if self.state == 0:
            if ch == ord('"'):
                self.state = 1
                return to_str(chr(ch))
            elif ch == ord('/'):
                self.state = 3
            else:
                return to_str(chr(ch))
        elif self.state == 1:
            if ch == ord('"'):
                self.state = 0
                return to_str(chr(ch))
            elif ch == ord('\\'):
                self.state = 2
            return to_str(chr(ch))
        elif self.state == 2:
            self.state = 1
            if ch == ord('"'):
                return to_str(chr(ch))
            return "\\" + to_str(chr(ch))
        elif self.state == 3:
            if ch == ord('/'):
                self.state = 4
            else:
                return "/" + to_str(chr(ch))
        elif self.state == 4:
            if ch == ord('\n'):
                self.state = 0
                return "\n"
        return ""


def remove_comment(json):
    fmt = JSFormat()
    return "".join([fmt.push(c) for c in json])


def parse_json_in_str(data):
    # parse json and convert everything from unicode to str
    return json.loads(data, object_hook=_decode_dict)
