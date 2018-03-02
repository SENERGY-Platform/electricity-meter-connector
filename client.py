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
            logger.debug("trying to open '{}'".format(port))
            serial_con = serial.Serial(port, timeout=15)
            rdy_msg = serial_con.readline()
            if 'RDY' in rdy_msg.decode():
                logger.debug("device on '{}' ready".format(port))
                return serial_con
            else:
                serial_con.close()
                logger.warning("no greeting from device on '{}'".format(port))
        except serial.SerialException:
            logger.warning("device on '{}' busy or has errors".format(port))
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

    def getController(self, device_id):
        for d_id, controller in __class__.__port_controller_map.values():
            if device_id == d_id:
                return controller
        return None

    def getDevices(self):
        try:
            return [val[0] for val in __class__.__port_controller_map.values()]
        except IndexError:
            pass
        return list()


    def delController(self, port):
        pass

    def run(self):
        while True:
            for p_info in serial.tools.list_ports.grep("usb"):
                if p_info.device not in __class__.__port_controller_map:
                    serial_con = self.getSerialCon(p_info.device)
                    if serial_con:
                        device_id = self.getDeviceID(serial_con)
                        if device_id:
                            logger.info("found device '{}' on '{}'".format(device_id, p_info.device))
                            __class__.__port_controller_map[p_info.device] = (device_id, SerialController(serial_con, device_id))
            sleep(5)


class SerialController(Thread):
    def __init__(self, serial_con: serial.Serial, device_id):
        super().__init__()
        self.serial_con = serial_con
        self.device_id = device_id
        self.start()

    def run(self):
        logger.debug("started serial controller for '{}'".format(self.device_id))



test = SerialManager()
test.start()
sleep(20)
logger.info(test.getController("AFGH"))
logger.info(test.getDevices())