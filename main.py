import argparse
import os
import time

from scout.scout import ScoutsDaemon


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-z', '--zookeeper', default=os.environ['ZK_SERVER'],
                        help='zookeeper server address (defaults to ZK_SERVER)')
    parser.add_argument('-t', '--timeout', default=os.environ['ZK_TIMEOUT'], type=int,
                        help='timeout for zk connection in seconds (defaults to ZK_TIMEOUT)')
    # parser.add_argument('-s', '--services', nargs="+", type=str, required=True,
    #                     help='list of services to keep track of')
    args = vars(parser.parse_args())

    scouts = ScoutsDaemon(args['zookeeper'], args['timeout'])

    while True and not scouts.terminated:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    main()
