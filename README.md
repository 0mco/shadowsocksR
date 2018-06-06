ShadowsocksR
===========

[![Build Status]][Travis CI]

A fast tunnel proxy that helps you bypass firewalls.


### Install

    git clone https://github.com/0mco/shadowsocksR.git
    cd shadowsocksR && python setup.py install


### Usage

####for client

    ssclient -L "your ssr-link"         // connect to ssr server via ssr link
    ssclient feed add --source "your subscription address"      // add subscription source
    ssclient feed list          // show subscription list
    ssclient feed fetch         // update server list
    ssclient server list
    ssclient server add --link "ssr link"
    ssclient server remove          // remove a ssr server
    ssclient server start -d        // connect to ssr server in daemon mode
    ssclient serve rswitch
    ssclient server remove
    ssclient config autoswitch          // auto-switch when current connection to ssr server is poor

you can also run

    ssclient -s 172.17.1.101 -p 4043 -k password -m aes-128-cfb -O auth_aes128_md5 -o tls1.2_ticket_auth_compatible

#### for server

    ssserver -p 443 -k password -m aes-128-cfb -O auth_aes128_md5 -o tls1.2_ticket_auth_compatible

Check all the options via `-h`.

    ssclient -h
    ssclient server -h


### New features
    * SSR link support        (ssclient -L "your ssr-link")
    * subscription support
    * autoswitch support


### TODO
    * autostart support
    * windows support
    * package
    * system-wide proxy
    * python 2.7 supoort
    * improve documentation
    * code cleaning
