class Singleton:
    def __init__(self, decorated):
        self.__decoreate = decorated
        self.__instance = None

    def instance(self):
        if self.__instance is None:
            self.__instance = self.__decoreate()

        return self.__instance

    def __call__(self):
        raise SyntaxError("Singletons must be called throught `instance()`.")
