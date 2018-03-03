import re


class StatusParser:
    ACTIVE = 'Active: '
    SINCE = ' since '

    def __init__(self):
        self._status = {
            'state': None,
            'since': None,
            'pid': None
        }

    def parse(self, string):
        self._status['state'] = re.search(r'Active: (.*?) since', string).group(1)
        self._status['since'] = re.search(r'; (.*?) ago', string).group(1)
        self._status['pid'] = re.search(r'Main PID: (.*?) ', string).group(1)
        return self._status
