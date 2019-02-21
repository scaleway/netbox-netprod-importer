from requests.exceptions import HTTPError

from netbox_netprod_importer.exceptions import GenericNetboxError


def is_macaddr(macaddr):
    macaddr_simplified = macaddr.replace(":", "").replace(".", "")
    if len(macaddr_simplified) != 12:
        return False

    try:
        hex(int(macaddr_simplified, 16))
    except ValueError:
        return False

    return True


def macaddr_to_int(macaddr):
    if not macaddr:
        return 0
    macaddr_simplified = macaddr.replace(":", "").replace(".", "")
    return int(macaddr_simplified, 16)


def generic_netbox_error(func):
    """
    Convert an HTTP error to a more explicit exception
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            raise GenericNetboxError(e)
    return wrapper
