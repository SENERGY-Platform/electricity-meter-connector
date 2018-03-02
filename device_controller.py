try:
    from modules.logger import root_logger
    from connector.client import Client
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from serial import SerialException, SerialTimeoutException
from threading import Thread


logger = root_logger.getChild(__name__)


class DeviceController(Thread):
    def __init__(self, serial_con, device_id, callbk):
        super().__init__()
        self.serial_con = serial_con
        self.device_id = device_id
        self.callbk = callbk
        self.new_avg_threshold = 0
        self.detection_threshold = 0
        self.lower_limit_distance = 0
        self.start()

    def _waitForRDY(self, retries=5):
        try:
            for retry in range(retries):
                msg = self.serial_con.readline()
                if 'RDY' in msg.decode():
                    logger.debug("device '{}' ready".format(self.device_id))
                    return True
        except SerialException as ex:
            logger.error(ex)
        return False

    def readConf(self):
        pass

    def writeConf(self):
        pass

    def configure(self, nat, dt, lld):
        pass

    def manualRead(self):
        pass

    def stopAction(self):
        pass

    def startDetection(self):
        pass

    def closeConnection(self):
        self.serial_con.close()
        self.callbk(self.serial_con.port)

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self.device_id))
        if self._waitForRDY():
            logger.info("started serial controller for device '{}'".format(self.device_id))
        else:
            logger.error("device '{}' not ready".format(self.device_id))
            self.closeConnection()
