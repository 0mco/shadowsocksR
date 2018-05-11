#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Encode/decode SSR link.
"""

from shadowsocks import common
import base64


def base64_decode(string):
    def adjust_padding(string):
        """Adjust to base64 format, i.e. len(string) % 4 == 0."""
        missing_padding = len(string) % 4
        if missing_padding:
            string += '=' * (4 - missing_padding)
        return string

    string = string.strip()
    return common.to_str(base64.urlsafe_b64decode(common.to_bytes(adjust_padding(string))))


def decode_ssrlink(link):
    # link[6:] to strip the first 6 characters, i.e. 'ssr://'
    config_str = base64_decode(link[6:]).split('/?')

    required_config = config_str[0].split(':')
    optional_config = config_str[1]

    config = {}
    config['server'] = required_config[0]
    config['server_port'] = required_config[1]
    config['protocol'] = required_config[2]
    config['method'] = required_config[3]
    config['obfs'] = required_config[4]
    config['password'] = base64_decode(required_config[5])
    for param in optional_config.split('&'):
        if param:           # remove empty param
            k, v = param.split('=')
            missing_padding = len(v) % 4
            if missing_padding != 0:
                v += '=' * (4 - missing_padding)
            config[k] = base64_decode(v)
    return config


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        # s = common.to_str(base64.urlsafe_b64decode(common.to_bytes(adjust_padding(sys.argv[1]))))
        s = base64_decode(sys.argv[1])
        a = s.split('\n')
        print(a)
