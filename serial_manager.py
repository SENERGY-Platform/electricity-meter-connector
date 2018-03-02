try:
    from modules.logger import root_logger
    from connector.client import Client
    from device_controller import DeviceController
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

    def getSerialCon(self, port) -> serial.Serial:
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

    def getDeviceID(self, serial_con: serial.Serial) -> str:
        try:
            serial_con.write(b'ID\n')
            id = serial_con.readline()
            if id:
                return id.decode().replace('\n', '').replace('\r', '')
        except (serial.SerialException, serial.SerialTimeoutException) as ex:
            logger.error(ex)
            logger.error("could not get device ID on '{}'".format(serial_con.port))

    def getController(self, device_id) -> DeviceController:
        for d_id, controller in __class__.__port_controller_map.values():
            if device_id == d_id:
                return controller

    def getDevices(self) -> list:
        try:
            return [val[0] for val in __class__.__port_controller_map.values()]
        except IndexError:
            pass
        return list()

    def delDevice(self, port):
        if port in __class__.__port_controller_map:
            del __class__.__port_controller_map[port]

    def run(self):
        while True:
            for p_info in serial.tools.list_ports.grep("usb"):
                if p_info.device not in __class__.__port_controller_map:
                    serial_con = self.getSerialCon(p_info.device)
                    if serial_con:
                        device_id = self.getDeviceID(serial_con)
                        if device_id:
                            logger.info("found device '{}' on '{}'".format(device_id, p_info.device))
                            __class__.__port_controller_map[p_info.device] = (device_id, DeviceController(serial_con, device_id))
            sleep(5)
