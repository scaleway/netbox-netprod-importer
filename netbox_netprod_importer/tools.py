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
    macaddr_simplified = macaddr.replace(":", "").replace(".", "")
    return int(macaddr_simplified, 16)
