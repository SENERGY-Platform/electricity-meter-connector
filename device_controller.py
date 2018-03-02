try:
    from modules.logger import root_logger
    from connector.client import Client
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import serial
from threading import Thread


logger = root_logger.getChild(__name__)


class DeviceController(Thread):
    def __init__(self, serial_con: serial.Serial, device_id):
        super().__init__()
        self.serial_con = serial_con
        self.device_id = device_id
        self.start()

    def run(self):
        logger.debug("started serial controller for '{}'".format(self.device_id))