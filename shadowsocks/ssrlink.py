#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Encode/decode SSR link.
"""

from shadowsocks import common
import base64


def decode_ssrlink(link):
    def adjust_padding(string):
        """Adjust to base64 format, i.e. len(string) % 4 == 0."""
        missing_padding = len(string) % 4
        if missing_padding:
            string += '=' * (4 - missing_padding)
        return string

    config_str = common.to_str(base64.urlsafe_b64decode(common.to_bytes(link[6:]))).split('/?')

    required_config = config_str[0].split(':')
    optional_config = config_str[1]

    config = {}
    config['server'] = required_config[0]
    config['server_port'] = required_config[1]
    config['protocol'] = required_config[2]
    config['method'] = required_config[3]
    config['obfs'] = required_config[4]
    config['password'] = common.to_str(base64.urlsafe_b64decode(common.to_bytes(adjust_padding(required_config[5]))))
    for param in optional_config.split('&'):
        if param:           # remvoe empty param
            k, v = param.split('=')
            missing_padding = len(v) % 4
            if missing_padding != 0:
                v +=  '=' * (4 - missing_padding)
            config[k] = common.to_str(base64.urlsafe_b64decode(common.to_bytes(adjust_padding(v))))
    print(config)
    return config
