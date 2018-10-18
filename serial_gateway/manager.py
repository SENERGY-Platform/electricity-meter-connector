"""
   Copyright 2018 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

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
            serial_con = serial.Serial(port, baudrate=4000000, timeout=5)
            logger.debug(serial_con)
            return serial_con
        except serial.SerialException as ex:
            logger.error(ex)
            logger.warning("device on '{}' busy or has errors".format(port))

    def _getGreeting(self, serial_con: serial.Serial) -> str:
        try:
            greeting_msg = serial_con.readline()
            if greeting_msg:
                greeting_msg = greeting_msg.decode().replace('\n', '').replace('\r', '')
                logger.debug("greeting from device on '{}': {}".format(serial_con.port, greeting_msg))
                if 'FERRARIS-SENSOR' in greeting_msg and greeting_msg.count(':') == 2:
                    return greeting_msg
                else:
                    logger.warning("malformed greeting from device on '{}'".format(serial_con.port))
            else:
                logger.warning("no greeting from device on '{}'".format(serial_con.port))
            serial_con.close()
        except serial.SerialException as ex:
            logger.error(ex)
            logger.error("error while waiting for greeting of device on '{}'".format(serial_con.port))

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
                    greeting = self._getGreeting(serial_con)
                    if greeting:
                        dip_id = greeting.split(':')[-1]
                        if not __class__.getController(dip_id):
                            logger.info("connected to device '{}' on '{}'".format(dip_id, port))
                            __class__.__port_controller_map[port] = DeviceController(serial_con, dip_id, greeting, __class__.delDevice)
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
    def getControllers() -> list:
        return list(__class__.__port_controller_map.values())

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
