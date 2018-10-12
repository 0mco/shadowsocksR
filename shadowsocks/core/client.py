from shadowsocks.core import network
from shadowsocks.lib import shell
import socket
import sys
import threading
import time

# TODO: move config to config/global.py
HOST = '127.0.0.1'
PORT = 6113


class Client:
    def __init__(self, host=HOST, port=PORT):
        self.sock = None
        self.host = host
        self.port = port

    def connect_to_service(self):
        # FIXME: catch error when connecting
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.setblocking(False)
        # self.sock.settimeout(5)
        print('connected to %s:%d' % (self.host, self.port))
        threading.Thread(target=self.retrive_output, args=(self.sock,), daemon=True).start()

    def retrive_output(self, sock):
        sock.settimeout(1)
        while True:
            try:
                while True:
                    time.sleep(0.2)
                    packet = sock.recv(4096)
                    print(packet.decode('utf-8'), end='')
            except socket.error as e:       # when no data can be received
                # FIXME: carefully handle error
                print('network error')
            except Exception as e:
                print("**[4]**", file=sys.stderr)
                print(e)

    def start(self):
        self.connect_to_service()
        # FIXME: clear exception (SystemExit) when using ctrl-c to exit
        args, extra_args = shell.parse_args()
        if args.command:
            cmd = ' '.join(s for s in sys.argv[1:])
            self.execute(cmd)
            if not args.i:
                time.sleep(1)       # waiting for result to show
                return
            while True:
                time.sleep(0.5)
                cmd = input(">>> ")
                if cmd == '':
                    continue
                if cmd == 'quit' or cmd == 'exit':
                    break
                self.execute(cmd)

        else:  # backward compatibility
            config = shell.parse_config(True)
            self.network = network.ClientNetwork(config)
            self.network.start()

    def execute(self, req, timeout=20):
        self.sock.setblocking(True)
        # FIXME: in Windows we should add '\r'?
        self.sock.send((req + '\n').encode('utf-8'))
        return
