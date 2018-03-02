import os, sys, inspect
import_path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"connector_client")))
if import_path not in sys.path:
    sys.path.insert(0, import_path)

try:
    from modules.logger import root_logger
    from connector.client import Client
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import serial
import serial.tools.list_ports
from time import sleep
from threading import Thread


logger = root_logger.getChild(__name__)


class SerialManager(Thread):
    device_scontroller_map = dict()

    def __init__(self):
        super().__init__()

    def getSerialCon(self, port):
        try:
            serial_con = serial.Serial(port, timeout=10)
            id = self.getDeviceID(serial_con)
            if id:
                return (serial_con, id)
        except serial.SerialException:
            return False

    def getDeviceID(self, serial_con: serial.Serial):
        msg = serial_con.readline()
        if 'RDY' in msg.decode():
            serial_con.write(b'ID\n')
            id = serial_con.readline()
            if id:
                return id.decode().replace('\n', '').replace('\r', '')
        return False

    def run(self):
        while True:
            for serial_port in sorted(serial.tools.list_ports.grep("usb")):

                if id not in __class__.device_scontroller_map:
                    __class__.device_scontroller_map[id] = SerialController(serial_port)
            sleep(5)


class SerialController(Thread):
    def __init__(self, port):
        super().__init__()
        self.serial_con = serial.Serial()
        self.serial_con.port = port
        self.serial_con.baudrate = 9600
        self.serial_con.timeout = 1
        logger.debug(self.serial_con)

    def run(self):
        pass



test = SerialManager()