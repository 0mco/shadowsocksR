def output_formatter(f):
    def decorated(*args, **kwargs):
        # print('\n')
        print('*' * 20, f, '*' * 20)
        return_value = f(*args, **kwargs)
        print('\n')
        return return_value

    return decorated
