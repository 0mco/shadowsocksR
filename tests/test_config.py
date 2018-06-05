from utils import *
add_path_if_main()


from shadowsocks.lib.config import *


def test_load():
    config = ClientConfigManager().load('test_config.json')
    # config.create('servers', {})
    print('after instancing:', config.config)
    servers = config.get('servers')
    config.add('servers', 'ssr://www.baidu.com/')
    servers = config.get('servers')


# def test_clear():
#     print('before clear')
#     config = ClientConfigManager().load('test_config.json')
#     servers = config.get('servers')
#     print('servers:', servers)
#     config.clear()
#     print('after clear')
#     servers = config.get('servers')
#     print('servers:', servers)


def test_recursive_key():
    config = ClientConfigManager().load('test_config.json')
    servers = config.get('servers')
    config.add('servers', 'ssr://www.google.com/')
    print('creating ks')
    config.create('ks', {})
    print('creating ks/ww')
    config.create('ks/ww', {})
    print('*' * 40)
    print(config.config)
    print('removing ks/ww')
    config.remove('ks/ww')
    print(config.config)
    print('removing ks')
    config.remove('ks')
    print(config.config)


@output_formatter
def test_subscription():
    config = ClientConfigManager('test_config.pickle')
    singleton_test = ClientConfigManager('test_config.pickle')
    assert config is singleton_test
    print('before:')
    servers = config.get_server()
    sub = config.get_subscription()
    print('server:', servers)
    print('subscription:', sub)
    # config.clear()
    config.add_subscription(['sub1', 'sub2'])
    config.add_server(['server1', 'server2'])
    servers = config.get_server()
    sub = config.get_subscription()
    print('server:', servers)
    print('subscription:', sub)
    config.add_subscription('sub3')
    config.add_server('server3')
    servers = config.get_server()
    sub = config.get_subscription()
    print('server:', servers)
    print('subscription:', sub)
    print(config.config)


if __name__ == "__main__":
    # config = ClientConfigManager('test_config.json')
    # config.clear()
    # test_recursive_key()
    test_subscription()
