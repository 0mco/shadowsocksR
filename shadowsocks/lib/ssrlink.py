#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Encode/decode SSR link.
"""
if __name__ == '__main__':
    import os, sys
    file_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.join(file_path, '../../'))


from shadowsocks.core import common
import base64
# from urllib import urlencode


def base64_decode(string):
    def adjust_padding(string):
        """Adjust to base64 format, i.e. len(string) % 4 == 0."""
        missing_padding = len(string) % 4
        if missing_padding:
            string += '=' * (4 - missing_padding)
        return string

    string = adjust_padding(string.strip())
    return common.to_str(base64.urlsafe_b64decode(common.to_bytes(string)))


def base64_encode(string):
    return common.to_str(base64.urlsafe_b64encode(common.to_bytes(string))).replace('=', '')


def decode_ssrlink(link):
    if not is_valide_ssrlink(link):
        raise Exception(link + 'is not a valid ssr link')
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
        if param:  # remove empty param
            k, v = param.split('=')
            try:
                config[k] = base64_decode(v)
            except Exception:  # in case that this is not a base64encoded string, use the original string instead.
                config[k] = v
    return config


def encode_to_link(server):
    required = ':'.join([server['server'], server['server_port'], server['protocol'], server['method'], server['obfs'], base64_encode(server['password'])])
    optional = []
    for k, v in server.items():
        if k not in ['server', 'server_port', 'protocol', 'method', 'obfs', 'password']:
            if k == 'uot':              # somehow this value is not base64-encoded.
                optional.append('{}={}'.format(k, v))
            else:
                # optional[k] = base64_encode(v)
                optional.append('{}={}'.format(k, base64_encode(v)))
    optional = '&'.join(optional)
    link = 'ssr://' + base64_encode('/?'.join((required, optional)))
    return link


def is_valide_ssrlink(ssrlink):
    return ssrlink[:6] == 'ssr://'


def is_duplicated(link1, link2):
    ssr1 = decode_ssrlink(link1)
    ssr2 = decode_ssrlink(link2)
    # for config in ['server', 'server_port', 'password', 'protocol', 'method', 'obfs']:
    for config in ['server', 'server_port']:            # the simple, the better
        if ssr1[config] != ssr2[config]:
            return False
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        # s = common.to_str(base64.urlsafe_b64decode(common.to_bytes(adjust_padding(sys.argv[1]))))
        # s = base64_decode(sys.argv[1])
        # a = s.split('\n')
        # print(a)
        # print(decode_ssrlink(sys.argv[1]))
        print(decode_ssrlink('ssr://' + sys.argv[1]))
        print(base64_decode(sys.argv[1]))
        server = decode_ssrlink('ssr://' + sys.argv[1])
        print(encode_to_link(server))

