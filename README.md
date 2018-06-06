ShadowsocksR
===========

[![Build Status]][Travis CI]

A fast tunnel proxy that helps you bypass firewalls.

UPDATE
------

### Support for SSR link

    python3 local.py -L "ssr://your-ssr-link"

Server
------

### Install

    git clone https://github.com/shadowsocksr/shadowsocksr.git

### Usage for single user on linux platform

Run:
    bash initcfg.sh

move to "~/shadowsocksr/shadowsocks", then run:

    python server.py -p 443 -k password -m aes-128-cfb -O auth_aes128_md5 -o tls1.2_ticket_auth_compatible

Check all the options via `-h`.

You can also use a configuration file instead (recommend), move to "~/shadowsocksr" and edit the file "user-config.json", then move to "~/shadowsocksr/shadowsocks" again, just run:

    python server.py

To run in the background:

    ./logrun.sh

To stop:

    ./stop.sh

To monitor the log:

    ./tail.sh


Client
------

* [Windows] / [macOS]
* [Android] / [iOS]
* [OpenWRT]

Use GUI clients on your local PC/phones. Check the README of your client
for more information.

Documentation
-------------

You can find all the documentation in the [Wiki].
