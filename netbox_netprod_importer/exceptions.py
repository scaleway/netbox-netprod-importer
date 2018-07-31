class MissingGraphError(Exception):
    pass


class NoReverseFoundError(Exception):
    def __init__(self, host):
        super().__init__("No reverse found for host {}".format(host))


class TypeCouldNotBeParsedError(Exception):
    pass
