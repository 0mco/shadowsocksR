#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Support for subscribtion.
{'subscribe_addrs': {},
        'groups': {},
        'servers': {}}
"""

if __name__ == '__main__':
    import os, sys
    file_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.join(file_path, '../../'))
    sys.path.insert(0, os.path.join(file_path, '../'))

from shadowsocks.lib import ssrlink
import requests
import pickle
import logging


def feed_ssr(url):
    """Retrive ssr links form url, return a list."""
    # TODO: sometimes we need to try to get via a proxy.
    base64_ssr = requests.get(url).text
    ssrlinks = ssrlink.base64_decode(base64_ssr).split('\n')
    # The last one should be empty string.
    # Of course we can handle more correctly.
    # But as for now, it just works.
    return [link for link in ssrlinks if ssrlink.is_valide_ssrlink(link)]


def load_servers():
    with open('ssr.pickle') as f:
        ssrlinks = pickle.load(f)
    return ssrlinks


def update_servers(url):
    try:
        ssrlinks = feed_ssr(url)
        with open('ssr.pickle', 'w') as f:
            pickle.dump(ssrlinks, f)
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        print(feed_ssr(sys.argv[1]))
