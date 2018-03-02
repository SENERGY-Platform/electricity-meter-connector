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
    __port_controller_map = dict()

    def __init__(self):
        super().__init__()

    def getSerialCon(self, port):
        try:
            serial_con = serial.Serial(port, timeout=15)
            msg = serial_con.readline()
            if 'RDY' in msg.decode():
                return serial_con
            else:
                logger.debug("no greeting from device on '{}'".format(port))
        except serial.SerialException:
            logger.debug("device on '{}' busy or has errors".format(port))
        return None

    def getDeviceID(self, serial_con: serial.Serial):
        try:
            serial_con.write(b'ID\n')
            id = serial_con.readline()
            if id:
                return id.decode().replace('\n', '').replace('\r', '')
        except (serial.SerialException, serial.SerialTimeoutException) as ex:
            logger.error(ex)
            logger.error("could not get device ID on '{}'".format(serial_con.port))
        return None

    def delController(self, port):
        pass

    def run(self):
        while True:
            for serial_port in sorted(serial.tools.list_ports.grep("usb")):
                serial_con = self.getSerialCon(serial_port.device)
                if serial_con:
                    id = self.getDeviceID(serial_con)
                    if id:
                        if id not in __class__.__port_controller_map:
                            __class__.__port_controller_map[id] = SerialController(serial_con)
                            logger.info("found device '{}'".format(id))
            sleep(5)


class SerialController(Thread):
    def __init__(self, serial_con: serial.Serial):
        super().__init__()
        self.serial_con = serial_con

    def run(self):
        pass



test = SerialManager()
test.start()