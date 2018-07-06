try:
    from connector_client.modules.singleton import SimpleSingleton
    from serial_gateway.device_controller import DeviceController
    from serial_gateway.devices_db import DevicesDatabase
    from serial_gateway.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import serial
import serial.tools.list_ports
from time import sleep
from threading import Thread


logger = root_logger.getChild(__name__)


class SerialManager(SimpleSingleton, Thread):
    __port_controller_map = dict()

    def __init__(self):
        super().__init__()
        logger.debug("starting initial device scan")
        self._monitorPorts()
        self.start()

    def _getSerialCon(self, port) -> serial.Serial:
        try:
            logger.debug("trying to open '{}'".format(port))
            serial_con = serial.Serial(port, timeout=15)
            rdy_msg = serial_con.readline()
            if 'RDY' in rdy_msg.decode():
                logger.debug("device on '{}' ready".format(port))
                serial_con.timeout = 4
                return serial_con
            else:
                serial_con.close()
                logger.warning("no greeting from device on '{}'".format(port))
        except serial.SerialException:
            logger.warning("device on '{}' busy or has errors".format(port))

    def _getDipID(self, serial_con: serial.Serial) -> str:
        try:
            serial_con.write(b'ID\n')
            id = serial_con.readline()
            if id:
                return id.decode().replace('\n', '').replace('\r', '')
        except (serial.SerialException, serial.SerialTimeoutException) as ex:
            logger.error(ex)
            logger.error("could not get ID for device on '{}'".format(serial_con.port))

    def _diff(self, known, unknown):
        known_set = set(known)
        unknown_set = set(unknown)
        missing = known_set - unknown_set
        new = unknown_set - known_set
        return new, missing

    def _monitorPorts(self):
        ports = [val.device for val in serial.tools.list_ports.grep("usb")]
        new_p, missing_p = self._diff(__class__.__port_controller_map, ports)
        #flatten = lambda li: [item for sublist in li for item in sublist]
        if new_p:
            for port in new_p:
                serial_con = self._getSerialCon(port)
                if serial_con:
                    dip_id = self._getDipID(serial_con)
                    if dip_id:
                        if not __class__.getController(dip_id):
                            logger.info("connected to device '{}' on '{}'".format(dip_id, port))
                            __class__.__port_controller_map[port] = DeviceController(serial_con, dip_id, __class__.delDevice)
                        else:
                            logger.warning("device '{}' already exists".format(dip_id))
                            serial_con.close()
        if missing_p:
            for port in missing_p:
                logger.info("device on '{}' disconnected".format(port))
                self.delDevice(port)

    @staticmethod
    def getController(dip_id) -> DeviceController:
        for controller in __class__.__port_controller_map.values():
            if dip_id == controller._id:
                return controller

    @staticmethod
    def getDevices() -> list:
        try:
            return [val._id for val in __class__.__port_controller_map.values()]
        except IndexError:
            pass
        return list()

    @staticmethod
    def delDevice(port):
        if port in __class__.__port_controller_map:
            controller = __class__.__port_controller_map.get(port)
            del __class__.__port_controller_map[port]
            controller.haltController()

    def run(self):
        logger.debug("starting monitor routine")
        while True:
            self._monitorPorts()
            sleep(2)
