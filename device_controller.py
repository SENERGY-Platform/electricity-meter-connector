try:
    from connector.client import Client
    from connector.device import Device
    from modules.device_pool import DevicePool
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
    def __init__(self, serial_con, dip_id, callbk):
        super().__init__()
        self._serial_con = serial_con
        self._dip_id = dip_id
        self._callbk = callbk
        self._commands = Queue()
        self._serial_logger = serial_logger.getChild(self._dip_id)
        self.log_file = os.path.join(os.path.dirname(__file__), '{}/{}.log'.format(devices_path, self._dip_id))
        if not self._serial_logger.hasHandlers():
            log_handler = logging.FileHandler(self.log_file)
            log_handler.setFormatter(logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p'))
            self._serial_logger.addHandler(log_handler)
        self._nat = 0
        self._dt = 0
        self._ndt = 0
        self._lld = 0
        self._strt = 0
        self._rpkwh = 0
        self._kWh = 0.0
        self._sensor_name = str()
        if self._loadDeviceInfo():
            if not self._sensor_name:
                self._sensor_name = "Ferraris Sensor ({})".format(self._dip_id)
            self._device = Device("{}-{}".format(self._dip_id, ID_PREFIX), "iot#fd0e1327-d713-41da-adfb-e3853a71db3b", self._sensor_name)
            self._device.addTag("type1", "Ferraris Meter")
            self._device.addTag("type2", "Optical Sensor")
            self.start()
        else:
            self._callbk(self._serial_con.port)

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

    def _loadDeviceInfo(self):
        conf = devices_db.getDeviceConf(self._dip_id)
        if not conf:
            logger.warning("no configuration found for device '{}'".format(self._dip_id))
            if devices_db.addDevice(self._dip_id):
                logger.info("created configuration for device '{}'".format(self._dip_id))
                conf = devices_db.getDeviceConf(self._dip_id)
            else:
                logger.error("could not create configuration for device '{}'".format(self._dip_id))
        if conf:
            self._setDeviceInfo(conf)
            logger.info("loaded configuration for device '{}'".format(self._dip_id))
            return True
        logger.error("could not load configuration for device '{}'".format(self._dip_id))
        return False

    def _setDeviceInfo(self, conf):
        self._nat = conf['nat']
        self._dt = conf['dt']
        self._ndt = conf['ndt']
        self._lld = conf['lld']
        self._rpkwh = conf['rpkwh']
        self._strt = conf['strt']
        self._kWh = float(conf['kWh'])
        self._sensor_name = conf['name']

    def getConf(self):
        return {
            'nat': self._nat,
            'dt': self._dt,
            'ndt': self._ndt,
            'lld': self._lld,
            'rpkwh': self._rpkwh,
        }

    def configureDevice(self, nat, dt, ndt, lld):
        self._commands.put(functools.partial(self._configureDevice, nat, dt, ndt, lld))

    def _configureDevice(self, nat, dt, ndt, lld, init=False):
        devices_db.updateDeviceConf(self._dip_id, nat=nat, dt=dt, lld=lld)
        self._nat = nat
        self._dt = dt
        self._ndt = ndt
        self._lld = lld
        try:
            self._serial_con.write(b'CONF\n')
            self._writeToOutput('CONF', 'C')
            if self._waitFor('NAT:DT:NDT:LLD'):
                self._writeToOutput('NAT:DT:NDT:LLD', 'D')
                conf = '{}:{}:{}:{}\n'.format(nat, dt, ndt, lld)
                self._serial_con.write(conf.encode())
                self._writeToOutput(conf, 'C')
                resp = self._waitFor(':')
                self._writeToOutput(resp, 'D')
                if self._waitFor('RDY'):
                    self._writeToOutput('RDY', 'D')
                    logger.info("configured device {}".format(self._dip_id))
                    return True
                else:
                    logger.error("device '{}' not ready".format(self._dip_id))
            else:
                logger.error("device '{}' did not enter configuration mode".format(self._dip_id))
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        if init:
            return False
        else:
            raise __class__.Interrupt

    def setRotPerKwh(self, rpkwh):
        self._commands.put(functools.partial(self._setRotPerKwh, rpkwh))

    def _setRotPerKwh(self, rpkwh):
        devices_db.updateDeviceConf(self._dip_id, rpkwh=rpkwh)
        self._rpkwh = rpkwh

    def setKwh(self, kwh):
        if type(kwh) is str:
            kwh = kwh.replace(',', '.')
        devices_db.updateDeviceConf(self._dip_id, kWh=str(kwh))
        self._kWh = float(kwh)

    def setName(self, name):
        if not self._sensor_name == str(name):
            self._sensor_name = str(name)
            devices_db.updateDeviceConf(self._dip_id, name=self._sensor_name)
            self._device.name = self._sensor_name
            Client.update(self._device)

    def getSettings(self):
        return {
            'strt': self._strt,
            'tkwh': self._kWh,
            'name': self._sensor_name
        }

    def readSensor(self):
        self._commands.put(self._readSensor)

    def _readSensor(self):
        try:
            self._serial_con.write(b'MR\n')
            self._writeToOutput('MR', 'C')
            while True:
                msg = self._serial_con.readline()
                if msg:
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

    def findExtrema(self):
        self._commands.put(self._findExtrema)

    def _findExtrema(self):
        try:
            self._serial_con.write(b'FE\n')
            self._writeToOutput('FE', 'C')
            while True:
                msg = self._serial_con.readline()
                if msg:
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
        devices_db.updateDeviceConf(self._dip_id, kWh=str(self._kWh))

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
                            "{}-{}".format(self._dip_id, ID_PREFIX),
                            'detection',
                            json.dumps({
                                'value': self._kWh,
                                'unit': 'kWh',
                                'time': datetime.datetime.now().isoformat()
                            }),
                            block=False
                        )
                    elif 'CAL' in msg.decode():
                        self._writeToOutput('CAL', 'D')
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
            logger.warning("detection for device '{}' failed - rounds/kWh not set".format(self._dip_id))
            self._writeToOutput('rotations/kWh not set')

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
            logger.warning("debug for device '{}' failed - rounds/kWh not set".format(self._dip_id))
            self._writeToOutput('rotations/kWh not set')

    def enableAutoStart(self):
        devices_db.updateDeviceConf(self._dip_id, strt=1)
        self._strt = 1

    def disableAutoStart(self):
        devices_db.updateDeviceConf(self._dip_id, strt=0)
        self._strt = 0

    def haltController(self):
        self._commands.put(self._haltController)

    def _haltController(self):
        raise __class__.Interrupt

    def _closeConnection(self):
        self._serial_con.close()
        self._writeToOutput('serial connection closed')
        self._callbk(self._serial_con.port)

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self._dip_id))
        self._writeToOutput('serial connection open')
        if self._waitFor('RDY'):
            self._writeToOutput('RDY', 'D')
            logger.info("started serial controller for device '{}'".format(self._dip_id))
            if self._configureDevice(self._nat, self._dt, self._ndt, self._lld, True):
                try:
                    Client.add(self._device)
                except AttributeError:
                    DevicePool.add(self._device)
                if self._strt:
                    self.startDetection()
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
            logger.error("device '{}' not ready".format(self._dip_id))
        self._closeConnection()
        try:
            Client.disconnect(self._device)
        except AttributeError:
            DevicePool.remove(self._device)
        logger.info("serial controller for device '{}' exited".format(self._dip_id))

    class Interrupt(Exception):
        pass
