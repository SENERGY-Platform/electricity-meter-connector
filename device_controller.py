try:
    from modules.logger import root_logger
    from connector.client import Client
    from conf_manager import writeDeviceConf, readDeviceConf
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from serial import SerialException, SerialTimeoutException
from threading import Thread
from queue import Queue, Empty


logger = root_logger.getChild(__name__)


class DeviceController(Thread):
    def __init__(self, serial_con, device_id, callbk):
        super().__init__()
        self.serial_con = serial_con
        self.device_id = device_id
        self.callbk = callbk
        self.commands = Queue()
        self.halt = False
        self.start()

    def _waitFor(self, char, retries=5):
        try:
            for retry in range(retries):
                msg = self.serial_con.readline()
                if char in msg.decode():
                    return msg.decode()
        except SerialException as ex:
            logger.error(ex)
        return None

    def configureDevice(self, nat, dt, lld):
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
        return False

    def loadConf(self):
        conf = readDeviceConf(self.device_id)
        if not conf:
            logger.warning("no configuration found for device '{}' - using standard values".format(self.device_id))
            return self.configureDevice(4000, 100, 20)
        else:
            logger.info("loaded configuration for device '{}'".format(self.device_id))
            return self.configureDevice(conf[0], conf[1], conf[2])

    def manualRead(self):
        pass

    def stopAction(self):
        pass

    def startDetection(self):
        pass

    def closeConnection(self):
        self.serial_con.close()
        self.callbk(self.serial_con.port)

    def haltController(self):
        self.halt = True

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self.device_id))
        if self._waitFor('RDY'):
            logger.info("started serial controller for device '{}'".format(self.device_id))
            if self.loadConf():
                while not self.halt:
                    try:
                        command = self.commands.get(timeout=1)
                    except Empty:
                        pass
        else:
            logger.error("device '{}' not ready".format(self.device_id))
        self.closeConnection()
        logger.info("serial controller for device '{}' halted".format(self.device_id))
