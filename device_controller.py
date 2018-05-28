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
from enum import Enum
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

class Mode(Enum):
    interval = 'I'
    average = 'A'

class DeviceController(Thread):
    def __init__(self, serial_con, dip_id, callbk):
        super().__init__()
        self._serial_con = serial_con
        self._id = dip_id
        self._callbk = callbk
        self._commands = Queue()
        self._serial_logger = serial_logger.getChild(self._id)
        self.log_file = os.path.join(os.path.dirname(__file__), '{}/{}.log'.format(devices_path, self._id))
        if not self._serial_logger.hasHandlers():
            log_handler = logging.FileHandler(self.log_file)
            log_handler.setFormatter(logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p'))
            self._serial_logger.addHandler(log_handler)
        if self._loadDeviceInfo():
            if not self._meter_name:
                self._meter_name = "Ferraris Sensor ({})".format(self._id)
            self._device = Device("{}-{}".format(self._id, ID_PREFIX), "iot#fd0e1327-d713-41da-adfb-e3853a71db3b", self._meter_name)
            self._device.addTag("type1", "Ferraris Meter")
            self._device.addTag("type2", "Optical Sensor")
            self.start()
        else:
            self._callbk(self._serial_con.port)

    def _loadDeviceInfo(self):
        conf = devices_db.getDeviceConf(self._id)
        if not conf:
            logger.warning("no configuration found for device '{}'".format(self._id))
            if devices_db.addDevice(self._id):
                logger.info("created configuration for device '{}'".format(self._id))
                conf = devices_db.getDeviceConf(self._id)
            else:
                logger.error("could not create configuration for device '{}'".format(self._id))
        if conf:
            self._mode = Mode(conf['mode'])
            if self._mode == Mode.interval:
                self._conf_a = conf['lb']
                self._conf_b = conf['rb']
            elif self._mode == Mode.average:
                self._conf_a = conf['nat']
                self._conf_b = conf['lld']
            self._dt = conf['dt']
            self._ndt = conf['ndt']
            self._strt = conf['strt']
            self._rpkwh = conf['rpkwh']
            self._kwh = float(conf['kwh'])
            self._meter_name = conf['name']
            logger.info("loaded configuration for device '{}'".format(self._id))
            return True
        logger.error("could not load configuration for device '{}'".format(self._id))
        return False

    def _writeSerialLog(self, data, src=None):
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

    def _closeConnection(self):
        self._serial_con.close()
        self._writeSerialLog('serial connection closed')
        self._callbk(self._serial_con.port)

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self._id))
        self._writeSerialLog('serial connection open')
        if self._waitFor('RDY'):
            self._writeSerialLog('RDY', 'D')
            logger.info("started serial controller for device '{}'".format(self._id))
            if self._configureDevice(init=True):
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
                try:
                    Client.disconnect(self._device)
                except AttributeError:
                    DevicePool.remove(self._device)
        else:
            logger.error("device '{}' not ready".format(self._id))
        self._closeConnection()
        logger.info("serial controller for device '{}' exited".format(self._id))

    class Interrupt(Exception):
        pass


    #---------- getters and setters ----------#

    def getConf(self):
        return {
            'conf_a': self._conf_a,
            'conf_b': self._conf_b,
            'dt': self._dt,
            'ndt': self._ndt,
            'rpkwh': self._rpkwh
        }

    def getSettings(self):
        return {
            'strt': self._strt,
            'tkwh': self._kwh,
            'name': self._meter_name,
            'mode': self._mode.value
        }

    def setRotPerKwh(self, rpkwh):
        self._commands.put(functools.partial(self._setRotPerKwh, rpkwh))

    def _setRotPerKwh(self, rpkwh):
        self._rpkwh = rpkwh
        devices_db.updateDeviceConf(self._id, rpkwh=self._rpkwh)

    def setKwh(self, kwh):
        if type(kwh) is str:
            kwh = kwh.replace(',', '.')
        self._kwh = float(kwh)
        devices_db.updateDeviceConf(self._id, kwh=self._kwh)

    def _calcAndWriteTotal(self, kwh):
        self._kwh = self._kwh + kwh
        devices_db.updateDeviceConf(self._id, kwh=str(self._kwh))

    def setName(self, name):
        if not self._meter_name == str(name):
            self._meter_name = str(name)
            self._device.name = self._meter_name
            devices_db.updateDeviceConf(self._id, name=self._meter_name)
            Client.update(self._device)

    def setMode(self, mode):
        self._mode = Mode(str(mode))
        devices_db.updateDeviceConf(self._id, mode=self._mode.value)

    def setAutoStart(self, option):
        if devices_db.updateDeviceConf(self._id, strt=option):
            self._strt = option

    def setDeviceConf(self, conf_a, conf_b, dt, ndt):
        self._commands.put(functools.partial(self._configureDevice, conf_a, conf_b, dt, ndt))


    #---------- commands ----------#

    def _configureDevice(self, conf_a=None, conf_b=None, dt=None, ndt=None, init=False):
        #LB:RB:DT:NDT
        #NAT:LLD:DT:NDT
        if not init:
            self._conf_a = conf_a
            self._conf_b = conf_b
            self._dt = dt
            self._ndt = ndt
            if self._mode == Mode.interval:
                devices_db.updateDeviceConf(self._id, lb=self._conf_a, rb=self._conf_b, dt=self._dt, ndt=self._ndt)
            elif self._mode == Mode.average:
                devices_db.updateDeviceConf(self._id, nat=self._conf_a, lld=self._conf_b, dt=self._dt, ndt=self._ndt)
        try:
            self._serial_con.write('CONF\n'.encode())
            self._writeSerialLog('CONF', 'C')
            msg = self._waitFor(':')
            if msg:
                self._writeSerialLog(msg, 'D')
                conf = '{}:{}:{}:{}:{}\n'.format(self._mode.value, self._conf_a, self._conf_b, self._dt, self._ndt)
                self._serial_con.write(conf.encode())
                self._writeSerialLog(conf, 'C')
                resp = self._waitFor(':')
                self._writeSerialLog(resp, 'D')
                if self._waitFor('RDY'):
                    self._writeSerialLog('RDY', 'D')
                    logger.info("configured device {}".format(self._id))
                    return True
                else:
                    logger.error("device '{}' not ready".format(self._id))
            else:
                logger.error("device '{}' did not enter configuration mode".format(self._id))
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        if init:
            return False
        else:
            raise __class__.Interrupt

    def readSensor(self):
        self._commands.put(self._readSensor)

    def _readSensor(self):
        try:
            self._serial_con.write(b'MR\n')
            self._writeSerialLog('MR', 'C')
            while True:
                msg = self._serial_con.readline()
                if msg:
                    self._writeSerialLog(msg, 'D')
                try:
                    command = self._commands.get_nowait()
                    if command == self._stopAction:
                        if self._stopAction():
                            return True
                        else:
                            break
                    else:
                        self._writeSerialLog('busy - operation not possible')
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        raise __class__.Interrupt

    def findEdges(self):
        self._commands.put(self._findEdges)

    def _findEdges(self):
        try:
            self._serial_con.write(b'FE\n')
            self._writeSerialLog('FE', 'C')
            while True:
                msg = self._serial_con.readline()
                if msg:
                    self._writeSerialLog(msg, 'D')
                try:
                    command = self._commands.get_nowait()
                    if command == self._stopAction:
                        if self._stopAction():
                            return True
                        else:
                            break
                    else:
                        self._writeSerialLog('busy - operation not possible')
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
            self._writeSerialLog('STP', 'C')
            if self._waitFor('RDY'):
                self._writeSerialLog('RDY', 'D')
                return True
        except SerialTimeoutException:
            return False

    def startDetection(self):
        self._commands.put(self._startDetection)

    def _startDetection(self):
        if int(self._rpkwh) > 0:
            ws = int(3600000 / int(self._rpkwh))
            kWh = ws / 3600000
            try:
                self._serial_con.write(b'STRT\n')
                self._writeSerialLog('STRT', 'C')
                while True:
                    msg = self._serial_con.readline()
                    if 'DET' in msg.decode():
                        self._calcAndWriteTotal(kWh)
                        Client.event(
                            "{}-{}".format(self._id, ID_PREFIX),
                            'detection',
                            json.dumps({
                                'value': self._kwh,
                                'unit': 'kWh',
                                'time': datetime.datetime.now().isoformat()
                            }),
                            block=False
                        )
                    elif 'CAL' in msg.decode():
                        self._writeSerialLog('CAL', 'D')
                    try:
                        command = self._commands.get_nowait()
                        if command == self._stopAction:
                            if self._stopAction():
                                return True
                            else:
                                break
                        else:
                            self._writeSerialLog('busy - operation not possible')
                    except Empty:
                        pass
            except (SerialException, SerialTimeoutException) as ex:
                logger.error(ex)
            raise __class__.Interrupt
        else:
            logger.warning("detection for device '{}' failed - rounds/kWh not set".format(self._id))
            self._writeSerialLog('rotations/kWh not set')

    def startDebug(self):
        self._commands.put(self._startDebug)

    def _startDebug(self):
        if int(self._rpkwh) > 0:
            try:
                self._serial_con.write(b'STRT\n')
                self._writeSerialLog('STRT', 'C')
                while True:
                    msg = self._serial_con.readline()
                    if msg.decode() != '':
                        self._writeSerialLog(msg, 'D')
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
            logger.warning("debug for device '{}' failed - rounds/kWh not set".format(self._id))
            self._writeSerialLog('rotations/kWh not set')

    def haltController(self):
        self._commands.put(self._haltController)

    def _haltController(self):
        raise __class__.Interrupt
