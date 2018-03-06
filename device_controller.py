try:
    from modules.logger import root_logger
    from connector.client import Client
    from conf_manager import writeDeviceConf, readDeviceConf
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from serial import SerialException, SerialTimeoutException
from threading import Thread
from queue import Queue, Empty
import logging, functools, datetime, os, inspect


logger = root_logger.getChild(__name__)

OUT_QUEUE = Queue()


devices_path = '{}/devices'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
if not os.path.exists(devices_path):
    os.makedirs(devices_path)
    logger.debug("created 'devices' dictionary")

serial_logger = logging.getLogger()


class DeviceController(Thread):
    def __init__(self, serial_con, device_id, callbk):
        super().__init__()
        self._serial_con = serial_con
        self._device_id = device_id
        self._callbk = callbk
        self._commands = Queue()
        self._serial_logger = serial_logger.getChild(device_id)
        self._serial_logger.propagate = 0
        self.log_file = os.path.join(os.path.dirname(__file__), '{}/{}.log'.format(devices_path, device_id))
        log_handler = logging.FileHandler(self.log_file)
        log_handler.setFormatter(logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p'))
        self._serial_logger.addHandler(log_handler)
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
        conf = readDeviceConf(self._device_id)
        if not conf:
            logger.warning("no configuration found for device '{}' - using standard values".format(self._device_id))
            return self._configureDevice(4000, 100, 20, True)
        else:
            logger.info("loaded configuration for device '{}'".format(self._device_id))
            if int(conf[3]):
                self.startDetection()
            return self._configureDevice(conf[0], conf[1], conf[2], True)

    def _closeConnection(self):
        self._serial_con.close()
        self._writeToOutput('serial connection closed')
        self._callbk(self._serial_con.port)

    def configureDevice(self, nat, dt, lld):
        self._commands.put(functools.partial(self._configureDevice, nat, dt, lld))

    def _configureDevice(self, nat, dt, lld, init=False):
        writeDeviceConf(self._device_id, str(nat), str(dt), str(lld))
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

    def manualRead(self):
        self._commands.put(self._manualRead)

    def _manualRead(self):
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

    def startDetection(self):
        self._commands.put(self._startDetection)

    def _startDetection(self):
        try:
            self._serial_con.write(b'STRT\n')
            self._writeToOutput('STRT', 'C')
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
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        raise __class__.Interrupt

    def enableAutoStart(self):
        self._commands.put(self._enableAutoStart)

    def _enableAutoStart(self):
        writeDeviceConf(self._device_id, strt=1)

    def disableAutoStart(self):
        self._commands.put(self._disableAutoStart)

    def _disableAutoStart(self):
        writeDeviceConf(self._device_id, strt='0')

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
        logger.info("serial controller for device '{}' halted".format(self._device_id))

    class Interrupt(Exception):
        pass
