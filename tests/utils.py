def add_path_if_main():
    # if __name__ == '__main__':
    import os, sys
    file_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.join(file_path, '../'))


def output_formatter(f):
    def decorated(*args, **kwargs):
        # print('\n')
        print('*' * 20, f, '*' * 20)
        return_value = f(*args, **kwargs)
        print('\n')
        return return_value

    return decorated
