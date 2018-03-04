import re


def parse_status(status_string):
    res = re.search(r' is (not )?(running)', status_string)
    if res is None:
        return 'unrecognized'
    elif res.group(1) is not None:
        return 'inactive'
    else:
        return 'active'
