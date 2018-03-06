import json
import logging
import subprocess
import socket
import signal
import threading
import time

from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeException

from scout.exceptions import ConnectException
from scout.parsers import parse_status

CONFS_PATH = '/confs'

logging.basicConfig(level=logging.ERROR)
base_logger = logging.getLogger(__name__)
base_logger.setLevel(logging.INFO)


class ScoutsDaemon(threading.Thread):
    def __init__(self, server, timeout):
        super(ScoutsDaemon, self).__init__()
        self.logger = base_logger.getChild(self.__class__.__name__)

        self._server = server
        self._timeout = timeout
        self._zk = None
        self._scouts = {}
        self.terminated = False

        self._event = threading.Event()
        self.setDaemon(True)
        signal.signal(signal.SIGTERM, self._terminate)

        self._connect()
        self.start()

    def _connect(self):
        if self._zk and self._zk.connected:
            self.logger.info('[Connection] Kazoo client is already running')
            return
        else:
            self.logger.info('[Connection] Starting Kazoo client (server="%s")' % self._server)
            self._zk = KazooClient(hosts=self._server, timeout=self._timeout)
            self._zk.add_listener(self._conn_listener)
            event = self._zk.start_async()
            event.wait(timeout=self._timeout)

        if self._zk.connected:
            self.logger.info('[Connection] Kazoo client successfully connected')
        else:
            self._zk.stop()
            self._event.set()
            raise ConnectException('Failed connecting to Zookeeper')

    def _conn_listener(self, state):
        self.logger.info('[Connection] New state: %s' % state)

    def _terminate(self, signum, frame):
        if signum == signal.SIGTERM:
            self.logger.info('[General] Received SIGTERM, stopping...')
            self._event.set()

    def run(self):
        self._zk.ensure_path(CONFS_PATH)
        self._setup_scouts()

        while not self._event.is_set():
            self._event.wait(1)

        for scout in self._scouts.values():
            scout.stop()
        self.terminated = True
        self.logger.info('[General] Shutting down...')

    def _setup_scouts(self, event=None):
        services = self._zk.get_children(CONFS_PATH, watch=self._setup_scouts)
        self.logger.info('[Scouts] Found confs for: %s' % services)

        for scouted_service in self._scouts:
            if scouted_service not in services:
                self.logger.info('[Scouts] Service "%s" not in confs, removing its scout')
                self._scouts[scouted_service].stop()
                self._scouts.pop(scouted_service)

        for service in services:
            self._setup_scout(service)

    def _setup_scout(self, service, event=None):
        data, stat = self._zk.get("%s/%s" % (CONFS_PATH, service), watch=lambda ev: self._setup_scout(service, ev))
        conf = json.loads(data)

        if service in self._scouts:
            self.logger.info('[Scouts] New conf for %s' % service)
            self._scouts[service].set_conf(conf)
        else:
            self.logger.info('[Scouts] Creating a scout for %s' % service)
            scout = ServiceScout(
                zk=self._zk,
                service=service,
                cmd=conf['cmd'],
                zk_path=conf['zk_path'],
                refresh=conf['refresh']
            )
            self._scouts[service] = scout


class ServiceScout(threading.Thread):
    def __init__(self, zk, service, cmd, zk_path, refresh=5):
        super(ServiceScout, self).__init__()
        self.logger = base_logger.getChild(self.__class__.__name__)

        self._zk = zk
        self._service = service
        self._cmd = cmd
        self._zk_path = zk_path
        self._refresh = refresh
        self._full_path = None
        self._cached_status = None

        self._set_full_path()

        self._event = threading.Event()
        self.setDaemon(True)
        self.start()

    def run(self):
        last_check = 0
        while not self._event.is_set():
            if time.time() - last_check > self._refresh:
                result = subprocess.run(self._cmd.split(' '), stdout=subprocess.PIPE)

                output = result.stdout.decode('utf-8')
                status = parse_status(output)
                self._update(status)

                last_check = time.time()

            self._event.wait(1)

        self.logger.info('[Scouts] Scout for "%s" exiting...' % self._full_path)
        self._zk.delete(self._full_path)
        self._zk = None

    def _update(self, status):
        if self._cached_status == status:
            return

        status_json = json.dumps(status).encode(encoding='utf-8')
        self._zk.ensure_path(self._zk_path)
        try:
            self._zk.set(self._full_path, status_json)
            self.logger.info('[Scout] Updated status for "%s"' % self._full_path)
            self._cached_status = status
        except NoNodeException:
            self._zk.create(self._full_path, status_json, ephemeral=True)
            self.logger.info('[Scout] Node not present, created "%s"' % self._full_path)
            self._cached_status = status

    def stop(self):
        self._event.set()
        while self._zk is not None:
            self._event.wait(1)

    def set_conf(self, conf):
        self._cmd = conf['cmd']
        self._refresh = conf['refresh']
        self._zk_path = conf['zk_path']
        self._set_full_path()

    def _set_full_path(self):
        self._full_path = '%s/%s' % (self._zk_path, socket.gethostname())
