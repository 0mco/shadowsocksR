#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Support for subscribtion.
{'subscribe_addrs': {},
        'groups': {},
        'servers': {}}
"""

from shadowsocks.lib import ssrlink
import requests
import pickle
import logging


def retrive_ssrlink(url):
    """Retrive ssr links form url, return a list."""
    # TODO: sometimes we need to try to get via a proxy.
    base64_ssr = requests.get(url).text
    ssrlinks = ssrlink.base64_decode(base64_ssr).split('\n')
    # The last one should be empty string.
    # Of course we can handle more correctly.
    # But as for now, it just works.
    return ssrlinks[:-1]


def load_servers():
    with open('ssr.pickle') as f:
        ssrlinks = pickle.load(f)
    return ssrlinks


def update_servers(url):
    try:
        ssrlinks = retrive_ssrlink(url)
        with open('ssr.pickle', 'w') as f:
            pickle.dump(ssrlinks, f)
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        print(retrive_ssrlink(sys.argv[1]))
