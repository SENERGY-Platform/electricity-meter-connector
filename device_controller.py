try:
    from connector.client import Client
    from devices_db import DevicesDatabase
    from logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from serial import SerialException, SerialTimeoutException
from threading import Thread
from queue import Queue, Empty
import logging, functools, os, inspect, json, datetime


logger = root_logger.getChild(__name__)


devices_path = '{}/devices'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
if not os.path.exists(devices_path):
    os.makedirs(devices_path)
    logger.debug("created 'devices' dictionary")


serial_logger = logging.getLogger("serial_logger")
serial_logger.setLevel(logging.DEBUG)

devices_db = DevicesDatabase()
ID_PREFIX = devices_db.getIdPrefix()


class DeviceController(Thread):
    def __init__(self, serial_con, device_id, callbk):
        super().__init__()
        self._serial_con = serial_con
        self._device_id = device_id
        self._callbk = callbk
        self._commands = Queue()
        self._serial_logger = serial_logger.getChild(device_id)
        self.log_file = os.path.join(os.path.dirname(__file__), '{}/{}.log'.format(devices_path, device_id))
        if not self._serial_logger.hasHandlers():
            log_handler = logging.FileHandler(self.log_file)
            log_handler.setFormatter(logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p'))
            self._serial_logger.addHandler(log_handler)
        self._nat = 0
        self._dt = 0
        self._lld = 0
        self._strt = 0
        self._rpkwh = 0
        self._kWh = 0.0
        self.start()

    def _writeToOutput(self, data, src=None):
        if type(data) is not str:
            data = data.decode()
        data = data.replace('\n', '').replace('\r', '')
        if src == 'D':
            self._serial_logger.info('> {}'.format(data))
        elif src == 'C':
            self._serial_logger.info('< {}'.format(data))
        else:
            self._serial_logger.info('# {}'.format(data))

    def _waitFor(self, char, retries=5):
        try:
            for retry in range(retries):
                msg = self._serial_con.readline()
                if char in msg.decode():
                    return msg.decode()
        except SerialException as ex:
            logger.error(ex)
        return None

    def _loadConf(self):
        conf = devices_db.getDeviceConf(self._device_id)
        if not conf:
            logger.warning("no configuration found for device '{}'".format(self._device_id))
            return devices_db.addDevice(self._device_id)
        else:
            logger.info("loaded configuration for device '{}'".format(self._device_id))
            self._nat = conf['nat']
            self._dt = conf['dt']
            self._lld = conf['lld']
            self._rpkwh = conf['rpkwh']
            self._strt = conf['strt']
            self._kWh = float(conf['kWh'])
            if self._strt:
                self.startDetection()
            return self._configureDevice(self._nat, self._dt, self._lld, True)

    def _closeConnection(self):
        self._serial_con.close()
        self._writeToOutput('serial connection closed')
        self._callbk(self._serial_con.port)

    def getConf(self):
        return {
            'nat': self._nat,
            'dt': self._dt,
            'lld': self._lld,
            'strt': self._strt,
            'rpkwh': self._rpkwh,
            'tkwh': self._kWh
        }

    def configureDevice(self, nat, dt, lld):
        self._commands.put(functools.partial(self._configureDevice, nat, dt, lld))

    def _configureDevice(self, nat, dt, lld, init=False):
        devices_db.updateDeviceConf(self._device_id, nat=nat, dt=dt, lld=lld)
        self._nat = nat
        self._dt = dt
        self._lld = lld
        try:
            self._serial_con.write(b'CONF\n')
            self._writeToOutput('CONF', 'C')
            if self._waitFor('NAT:DT:LLD'):
                self._writeToOutput('NAT:DT:LLD', 'D')
                conf = '{}:{}:{}\n'.format(nat, dt, lld)
                self._serial_con.write(conf.encode())
                self._writeToOutput(conf, 'C')
                resp = self._waitFor(':')
                self._writeToOutput(resp, 'D')
                if self._waitFor('RDY'):
                    self._writeToOutput('RDY', 'D')
                    logger.info("configured device {}".format(self._device_id))
                    return True
                else:
                    logger.error("device '{}' not ready".format(self._device_id))
            else:
                logger.error("device '{}' did not enter configuration mode".format(self._device_id))
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        if init:
            return False
        else:
            raise __class__.Interrupt

    def setRotPerKwh(self, rpkwh):
        self._commands.put(functools.partial(self._setRotPerKwh, rpkwh))

    def _setRotPerKwh(self, rpkwh):
        devices_db.updateDeviceConf(self._device_id, rpkwh=rpkwh)
        self._rpkwh = rpkwh

    def setKwh(self, kwh):
        self._commands.put(functools.partial(self._setKwh, kwh))

    def _setKwh(self, kwh):
        if type(kwh) is str:
            kwh = kwh.replace(',', '.')
        devices_db.updateDeviceConf(self._device_id, kWh=str(kwh))
        self._kWh = float(kwh)

    def readSensor(self):
        self._commands.put(self._readSensor)

    def _readSensor(self):
        try:
            self._serial_con.write(b'MR\n')
            self._writeToOutput('MR', 'C')
            while True:
                msg = self._serial_con.readline()
                self._writeToOutput(msg, 'D')
                try:
                    command = self._commands.get_nowait()
                    if command == self._stopAction:
                        if self._stopAction():
                            return True
                        else:
                            break
                    else:
                        self._writeToOutput('busy - operation not possible')
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        raise __class__.Interrupt

    def stopAction(self):
        self._commands.put(self._stopAction)

    def _stopAction(self):
        try:
            self._serial_con.write(b'STP\n')
            self._writeToOutput('STP', 'C')
            if self._waitFor('RDY'):
                self._writeToOutput('RDY', 'D')
                return True
        except SerialTimeoutException:
            return False

    def _calcAndWriteTotal(self, kwh):
        self._kWh = self._kWh + kwh
        devices_db.updateDeviceConf(self._device_id, kWh=str(self._kWh))

    def startDetection(self):
        self._commands.put(self._startDetection)

    def _startDetection(self):
        if int(self._rpkwh) > 0:
            ws = int(3600000 / int(self._rpkwh))
            kWh = ws / 3600000
            try:
                self._serial_con.write(b'STRT\n')
                self._writeToOutput('STRT', 'C')
                while True:
                    msg = self._serial_con.readline()
                    if 'DET' in msg.decode():
                        self._calcAndWriteTotal(kWh)
                        Client.event(
                            "{}-{}".format(self._device_id, ID_PREFIX),
                            'detection',
                            json.dumps({
                                'value': self._kWh,
                                'unit': 'kWh',
                                'time': datetime.datetime.now().isoformat()
                            }),
                            block=False
                        )
                    try:
                        command = self._commands.get_nowait()
                        if command == self._stopAction:
                            if self._stopAction():
                                return True
                            else:
                                break
                        else:
                            self._writeToOutput('busy - operation not possible')
                    except Empty:
                        pass
            except (SerialException, SerialTimeoutException) as ex:
                logger.error(ex)
            raise __class__.Interrupt
        else:
            logger.warning("detection for device '{}' failed - rounds/kWh not set".format(self._device_id))

    def startDebug(self):
        self._commands.put(self._startDebug)

    def _startDebug(self):
        if int(self._rpkwh) > 0:
            try:
                self._serial_con.write(b'STRT\n')
                self._writeToOutput('STRT', 'C')
                while True:
                    msg = self._serial_con.readline()
                    if msg.decode() != '':
                        self._writeToOutput(msg, 'D')
                    try:
                        command = self._commands.get_nowait()
                        if command == self._stopAction:
                            if self._stopAction():
                                return True
                            else:
                                break
                    except Empty:
                        pass
            except (SerialException, SerialTimeoutException) as ex:
                logger.error(ex)
            raise __class__.Interrupt
        else:
            self._writeToOutput("please configure device first")

    def enableAutoStart(self):
        devices_db.updateDeviceConf(self._device_id, strt='1')
        self._strt = '1'

    def disableAutoStart(self):
        devices_db.updateDeviceConf(self._device_id, strt='0')
        self._strt = '0'

    def haltController(self):
        self._commands.put(self._haltController)

    def _haltController(self):
        raise __class__.Interrupt

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self._device_id))
        self._writeToOutput('serial connection open')
        if self._waitFor('RDY'):
            self._writeToOutput('RDY', 'D')
            logger.info("started serial controller for device '{}'".format(self._device_id))
            if self._loadConf():
                while True:
                    try:
                        command = self._commands.get(timeout=1)
                        if command != self._stopAction:
                            command()
                    except Empty:
                        pass
                    except __class__.Interrupt:
                        break
        else:
            logger.error("device '{}' not ready".format(self._device_id))
        self._closeConnection()
        logger.info("serial controller for device '{}' exited".format(self._device_id))

    class Interrupt(Exception):
        pass
