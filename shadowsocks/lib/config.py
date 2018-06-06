#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python module documentation.
"""

import json
import os
import sys


_key_sep = '/'          # seperator for recurive key, e.g. masterkey/subkey/subsubkey/...


def check_config_path():
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../config'))
    if not os.path.exists(config_path):
        os.makedirs(config_path)


check_config_path()


def load_before_read(func):
    """load config from file every read operation to make sure everything is up-to-date (though it cannot really ensure that)."""
    # FIXME: read/write safe when multi-processing
    def decorated(self, *args, **kwargs):
        if self._hold is False:
            self.read()
        result = func(self, *args, **kwargs)
        return result

    return decorated


def save_on_change(func):
    def decorated(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if self._hold is False:
            self.save()
        return result

    return decorated


class Indicator:
    """Indicator for some case."""
    _instance = None

    def __new__(cls):
        if Indicator._instance is None:
            Indicator._instance = super(Indicator, cls).__new__(cls)
        return Indicator._instance


# class NoKey(UniqueObject):
#     pass


def expand_key(d, keys):
    """return d[key] (key recursively), create indicates whether create recursively when no such key exists. keys can be a string, or a list."""
    if isinstance(keys, str):
        keys = keys.split(_key_sep)
    cur = d
    for key_ in keys:
        if key_ not in cur:
            raise Exception('no key: {} in {}'.format(key_, cur))
        cur = cur[key_]
    return cur


class BaseConfigManager:
    # TODO: single mode according to unique file.
    __version = '0.0.1'
    __pool = {}
    _platform = ''

    def __new__(cls, config_path=None, *args, **kwargs):
        if config_path is not None:
            real_path = os.path.realpath(config_path)
            if real_path in cls.__pool:
                return cls.__pool[real_path]
        return super(BaseConfigManager, cls).__new__(cls)

    def __init__(self, config_path=None, *args, **kwargs):
        self._hold = False         # when this is set to true, config will not save on change.
        self.config = {}
        self.config_path = None
        if config_path is not None:
            self.load(config_path)

    def init(self, *args, **kwargs):
        """init when config file not exists, override by subclasses."""
        pass

    def load(self, config_path):
        assert self.config_path is None         # make sure that an instance only
                                                # work for one config.
        real_path = os.path.realpath(config_path)
        self.config_path = real_path
        if real_path not in self.__pool:
            if not os.path.exists(real_path):   # if no such file, create it
                open(real_path, 'w')
                self.init()
                self.save()
            else:
                with open(real_path, 'r') as f:
                    try:
                        self.config = json.load(f)
                    except json.decoder.JSONDecodeError as e:
                        # TODO: print file content here
                        print(e)
                        choice = input("do you want to init config file? (yes/no)")
                        if choice.lower() == 'yes':
                            self.init()
                        else:
                            sys.exit(1)
            self.__pool[real_path] = self
            return self
        else:
            return self.__pool[real_path]

    def read(self):
        """read config from file."""
        with open(self.config_path) as f:
            self.config = json.load(f)

    def save(self, config_path=None):
        if config_path is None:
            config_path = self.config_path
        assert self.config is not None
        with open(config_path, 'w+') as f:
            json.dump(self.config, f)

    def clear(self):
        """initialize" config."""
        self.init()

    @save_on_change
    @load_before_read
    def create(self, key, value):
        """direct update whole self.config[key]."""
        keys = key.split(_key_sep)
        container = expand_key(self.config, keys[:-1])
        container[keys[-1]] = value

    def update(self, key, value):
        self.create(key, value)

    @save_on_change
    @load_before_read
    def add(self, key, value):
        """this method is for when self.config[key] is a container."""
        container = expand_key(self.config, key)
        if isinstance(container, list):
            container.append(value)
        elif isinstance(container, dict):
            container.update(value)
        elif isinstance(container, set):
            container.add(value)
        else:
            raise Exception('unknown container type ' + type(container))

    @save_on_change
    @load_before_read
    def union(self, key, value):
        container = expand_key(self.config, key)
        if isinstance(container, list):
            container.extend(value)
        elif isinstance(container, dict):
            container.update(value)
        elif isinstance(container, set):
            container.update(value)
        else:
            raise Exception('unknown container type ' + type(container))

    @load_before_read
    def get(self, key, value_=None):
        """return value with key or the default value if no such key."""
        try:
            value = expand_key(self.config, key)
        except Exception:
            value = value_          # set to default value
            raise
        return value

    @save_on_change
    @load_before_read
    def remove(self, key, value=Indicator):
        """if value is set to Indicator, then del self.config[key],
        else delete value in self.config[key]."""
        if value is Indicator:
            keys = key.split(_key_sep)
            parent_key = expand_key(self.config, keys[:-1])
            del parent_key[keys[-1]]
        else:
            container = expand_key(self.config, key)
            if isinstance(container, list):
                container.remove(value)
            elif isinstance(container, dict):
                del container[value]

    @property
    def version(self):
        return self.__version


class ClientConfigManager(BaseConfigManager):
    _platform = 'client (ver: {})'.format(BaseConfigManager.version)

    def init(self, *args, **kwargs):
        self._hold = True

        self.config = {}
        self.create('servers', [])      # TODO: priority queue
        self.create('subscriptions', {'auto_update': 1, 'list': []})
        self.create('auto_switch', 1)
        self.create('auto_start', 0)

        self._hold = False
        print('Initializing...')
        print(self.config)

    def get_server(self):           # FIXME: it seems that get_server will reset config.
        return list(self.get('servers', []))

    def add_server(self, ssr_addrs):
        if isinstance(ssr_addrs, str):
            self.add('servers', ssr_addrs)
        else:                               # if ssr_addrs is a container
            self.union('servers', ssr_addrs)

    def update_server_list(self, ssr_list):
        assert type(ssr_list) is list
        self.create('servers', ssr_list)

    def get_subscription(self):
        return list(self.get('subscriptions/list'))

    def add_subscription(self, addrs):
        if isinstance(addrs, str):
            self.add('subscriptions/list', addrs)
        else:
            self.union('subscriptions/list', addrs)
