try:
    from modules.logger import root_logger
    from connector.client import Client
    from conf_manager import writeDeviceConf, readDeviceConf
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from serial import SerialException, SerialTimeoutException
from threading import Thread
from queue import Queue, Empty
import functools, os, inspect


logger = root_logger.getChild(__name__)


devices_path = '{}/devices'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
if not os.path.exists(devices_path):
    os.makedirs(devices_path)
    logger.debug("created 'devices' dictionary")


class DeviceController(Thread):
    def __init__(self, serial_con, device_id, callbk):
        super().__init__()
        self.serial_con = serial_con
        self.device_id = device_id
        self.callbk = callbk
        self.commands = Queue()
        self.halt = False
        self.log_handler = None
        self.log_file = "{}/{}".format(devices_path, self.device_id)
        self.start()

    def writeLog(self, data):
        if type(data) is bytes:
            self.log_handler.write(data)
        else:
            self.log_handler.write(data.encode())

    def _waitFor(self, char, retries=5):
        try:
            for retry in range(retries):
                msg = self.serial_con.readline()
                if char in msg.decode():
                    return msg.decode()
        except SerialException as ex:
            logger.error(ex)
        return None

    def loadConf(self):
        conf = readDeviceConf(self.device_id)
        if not conf:
            logger.warning("no configuration found for device '{}' - using standard values".format(self.device_id))
            return self._configureDevice(4000, 100, 20, True)
        else:
            logger.info("loaded configuration for device '{}'".format(self.device_id))
            return self._configureDevice(conf[0], conf[1], conf[2], True)

    def closeConnection(self):
        self.serial_con.close()
        self.callbk(self.serial_con.port)

    def configureDevice(self, nat, dt, lld):
        self.commands.put(functools.partial(self._configureDevice, nat, dt, lld))

    def _configureDevice(self, nat, dt, lld, init=False):
        writeDeviceConf(self.device_id, nat, dt, lld)
        try:
            self.serial_con.write(b'CONF\n')
            if self._waitFor('NAT:DT:LLD'):
                conf = '{}:{}:{}\n'.format(nat, dt, lld)
                self.serial_con.write(conf.encode())
                resp = self._waitFor(':')
                if self._waitFor('RDY'):
                    logger.info("configured device {} - {}".format(self.device_id, resp.replace('\n', '').replace('\r', '')))
                    return True
                else:
                    logger.error("device '{}' not ready".format(self.device_id))
            else:
                logger.error("device '{}' did not enter configuration mode".format(self.device_id))
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
        if init:
            return False
        else:
            raise __class__.Interrupt

    def manualRead(self):
        self.commands.put(self._manualRead)

    def _manualRead(self):
        try:
            self.serial_con.write(b'MR\n')
            while True:
                msg = self.serial_con.readline()
                self.writeLog(msg)
                try:
                    command = self.commands.get_nowait()
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
        self.commands.put(self._stopAction)

    def _stopAction(self):
        try:
            self.serial_con.write(b'STP\n')
            if self._waitFor('RDY'):
                return True
        except SerialTimeoutException:
            return False

    def startDetection(self):
        self.commands.put(self._startDetection)

    def _startDetection(self):
        try:
            self.serial_con.write(b'STRT\n')
            while True:
                msg = self.serial_con.readline()
                try:
                    command = self.commands.get_nowait()
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

    def haltController(self):
        self.commands.put(self._haltController)

    def _haltController(self):
        raise __class__.Interrupt

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self.device_id))
        if os.path.isfile(self.log_file):
            os.remove(self.log_file)
        self.log_handler = open(self.log_file, "ab", buffering=0)
        if self._waitFor('RDY'):
            logger.info("started serial controller for device '{}'".format(self.device_id))
            if self.loadConf():
                while True:
                    try:
                        command = self.commands.get(timeout=1)
                        command()
                    except Empty:
                        pass
                    except __class__.Interrupt:
                        break
        else:
            logger.error("device '{}' not ready".format(self.device_id))
        self.closeConnection()
        self.log_handler.close()
        os.remove(self.log_file)
        logger.info("serial controller for device '{}' halted".format(self.device_id))

    class Interrupt(Exception):
        pass
