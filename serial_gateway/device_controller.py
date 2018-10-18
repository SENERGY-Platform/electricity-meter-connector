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
    from connector_client.client import Client
    from connector_client.device import Device
    from connector_client.modules.device_pool import DevicePool
    from serial_gateway.devices_db import DevicesDatabase
    from serial_gateway.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from serial import SerialException, SerialTimeoutException
from threading import Thread
from queue import Queue, Empty
from enum import Enum
import logging, os, inspect, json


logger = root_logger.getChild(__name__)


devices_path = '{}/devices'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
if not os.path.exists(devices_path):
    os.makedirs(devices_path)
    logger.debug("created 'devices' dictionary")


serial_logger = logging.getLogger("serial_logger")
serial_logger.setLevel(logging.DEBUG)

devices_db = DevicesDatabase()
ID_PREFIX = devices_db.getIdPrefix()

class Mode(Enum):
    interval = 'I'
    average = 'A'

class DeviceController(Thread):
    def __init__(self, serial_con, dip_id, greeting, callbk):
        super().__init__()
        self._serial_con = serial_con
        self._id = dip_id
        self._extended_id = "{}-{}".format(self._id, ID_PREFIX)
        self._greeting = greeting
        self._callbk = callbk
        self._commands = Queue()
        self._serial_logger = serial_logger.getChild(self._id)
        self.log_file = os.path.join(os.path.dirname(__file__), '{}/{}.log'.format(devices_path, self._id))
        if not self._serial_logger.hasHandlers():
            log_handler = logging.FileHandler(self.log_file)
            log_handler.setFormatter(logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p'))
            self._serial_logger.addHandler(log_handler)
        if self._loadDeviceInfo():
            self._device = Device(self._extended_id, "iot#fd0e1327-d713-41da-adfb-e3853a71db3b", self._meter_name)
            self._device.addTag("type1", "Ferraris Meter")
            self._device.addTag("type2", "Optical Sensor")
            self.start()
        else:
            self._callbk(self._serial_con.port)

    def _loadDeviceInfo(self):
        conf = devices_db.getDevice(self._id)
        if not conf:
            logger.warning("no configuration found for device '{}'".format(self._id))
            if devices_db.addDevice(self._id):
                logger.info("created configuration for device '{}'".format(self._id))
                conf = devices_db.getDevice(self._id)
            else:
                logger.error("could not create configuration for device '{}'".format(self._id))
        if conf:
            self._mode = Mode(conf['mode'])
            self._conf = {
                Mode.interval: {'conf_a': conf['lb'], 'conf_b': conf['rb']},
                Mode.average: {'conf_a': conf['nat'], 'conf_b': conf['lld']}
            }
            self._dt = conf['dt']
            self._ndt = conf['ndt']
            self._strt = conf['strt']
            self._rpkwh = conf['rpkwh']
            self._kwh = float(conf['kwh'])
            self._meter_name = conf['name']
            if not self._meter_name:
                self._meter_name = "Ferraris Sensor ({})".format(self._id)
            logger.info("loaded configuration for device '{}'".format(self._id))
            return True
        logger.error("could not load configuration for device '{}'".format(self._id))
        return False

    def _writeSerialLog(self, data, src=None):
        if type(data) is not str:
            data = data.decode()
        data = data.replace('\n', '').replace('\r', '')
        if src == 'D':
            self._serial_logger.info('> {}'.format(data))
        elif src == 'C':
            self._serial_logger.info('< {}'.format(data))
        else:
            self._serial_logger.info('# {}'.format(data))

    def _waitFor(self, char, retries=5):
        try:
            for retry in range(retries):
                msg = self._serial_con.readline()
                logger.debug(msg)
                if char in msg.decode():
                    return msg.decode()
        except Exception as ex:
            logger.error(ex)
        return None

    def _closeConnection(self):
        self._serial_con.close()
        self._writeSerialLog('serial connection closed')
        self._callbk(self._serial_con.port)

    def run(self):
        logger.debug("starting serial controller for device '{}'".format(self._id))
        self._writeSerialLog('serial connection open')
        self._writeSerialLog(self._greeting, 'D')
        if self._waitFor('RDY'):
            self._writeSerialLog('RDY', 'D')
            logger.info("started serial controller for device '{}'".format(self._id))
            logger.debug(self._serial_con)
            if self._configureDevice(init=True):
                try:
                    Client.add(self._device)
                except AttributeError:
                    DevicePool.add(self._device)
                if self._strt:
                    self.startDetection()
                while True:
                    try:
                        command, callbk, kwargs = self._commands.get(timeout=1)
                        if command != self._stopAction:
                            if kwargs:
                                command(callbk, **kwargs)
                            else:
                                command(callbk)
                        else:
                            callbk(409)
                    except Empty:
                        pass
                    except __class__.Interrupt:
                        break
                try:
                    Client.disconnect(self._device)
                except AttributeError:
                    DevicePool.remove(self._device)
        else:
            logger.error("device '{}' not ready".format(self._id))
        self._closeConnection()
        logger.info("serial controller for device '{}' exited".format(self._id))

    class Interrupt(Exception):
        pass


    #---------- getters and setters ----------#

    def getConf(self):
        return {
            'mode': self._mode.value,
            'conf': {
                Mode.interval.value: self._conf[Mode.interval],
                Mode.average.value: self._conf[Mode.average]
            },
            'dt': self._dt,
            'ndt': self._ndt
        }

    def getSettings(self):
        return {
            'strt': self._strt,
            'rpkwh': self._rpkwh,
            'tkwh': self._kwh,
            'name': self._meter_name
        }

    def setConf(self, callbk, mode, conf_a, conf_b, dt, ndt):
        success = False
        if Mode(mode) == Mode.interval:
            success = devices_db.updateDevice(
                self._id,
                mode=Mode(mode).value,
                lb=int(conf_a),
                rb=int(conf_b),
                dt=int(dt),
                ndt=int(ndt)
            )
        elif Mode(mode) == Mode.average:
            success = devices_db.updateDevice(
                self._id,
                mode=Mode(mode).value,
                nat=int(conf_a),
                lld=int(conf_b),
                dt=int(dt),
                ndt=int(ndt)
            )
        if success:
            self._mode = Mode(mode)
            self._conf[self._mode]['conf_a'] = int(conf_a)
            self._conf[self._mode]['conf_b'] = int(conf_b)
            self._dt = int(dt)
            self._ndt = int(ndt)
            self._commands.put((self._configureDevice, callbk, None))

    def setSettings(self, rpkwh, kwh, name):
        if type(kwh) is str:
            kwh = kwh.replace(',', '.')
        if devices_db.updateDevice(self._id, rpkwh=int(rpkwh), kwh=float(kwh), name=str(name)):
            self._rpkwh = int(rpkwh)
            self._kwh = float(kwh)
            self._meter_name = str(name)
            if not self._device.name == self._meter_name:
                self._device.name = self._meter_name
                try:
                    Client.update(self._device)
                except AttributeError:
                    DevicePool.update(self._device)

    def setAutoStart(self, state):
        if devices_db.updateDevice(self._id, strt=int(state)):
            self._strt = int(state)

    def _calcAndWriteTotal(self, kwh):
        kwh = kwh + self._kwh
        devices_db.updateDevice(self._id, kwh=str(kwh))
        self._kwh = kwh

    def _savePlotData(self, data):
        try:
            with open(os.path.join(os.path.dirname(__file__), '{}/{}.plot'.format(devices_path, self._id)), 'w') as file:
                file.write(json.dumps(data))
        except Exception as ex:
            logger.error("storing plot data for '{}' failed - {}".format(self._id, ex))

    def getPlotData(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), '{}/{}.plot'.format(devices_path, self._id)), 'r') as file:
                return json.loads(file.read())
        except Exception as ex:
            logger.error("loading plot data for '{}' failed - {}".format(self._id, ex))

    #---------- commands ----------#

    def _configureDevice(self, callbk=None, init=False):
        try:
            self._serial_con.write(b'CONF\n')
            self._writeSerialLog('CONF', 'C')
            msg = self._waitFor(':')
            if msg:
                self._writeSerialLog(msg, 'D')
                conf = '{}:{}:{}:{}:{}\n'.format(self._mode.value, self._conf[self._mode]['conf_a'], self._conf[self._mode]['conf_b'], self._dt, self._ndt)
                self._serial_con.write(conf.encode())
                self._writeSerialLog(conf, 'C')
                if self._waitFor(conf.replace('\n', '')):
                    self._writeSerialLog(conf, 'D')
                    if self._waitFor('RDY'):
                        self._writeSerialLog('RDY', 'D')
                        logger.info("configured device {}".format(self._id))
                        if callbk:
                            callbk(200)
                        return True
                    else:
                        logger.error("device '{}' not ready".format(self._id))
                else:
                    logger.error("device '{}' could not be configured".format(self._id))
            else:
                logger.error("device '{}' did not enter configuration mode".format(self._id))
        except (SerialException, SerialTimeoutException, ValueError) as ex:
            logger.error(ex)
            if callbk:
                callbk(500)
        if init:
            return False
        raise __class__.Interrupt

    def readSensor(self, callbk):
        self._commands.put((self._readSensor, callbk, None))

    def _readSensor(self, callbk):
        try:
            self._serial_con.write(b'MR\n')
            self._writeSerialLog('MR', 'C')
            callbk(200)
            while True:
                msg = self._serial_con.readline()
                if msg:
                    self._writeSerialLog(msg, 'D')
                try:
                    command, callbk, kwargs = self._commands.get_nowait()
                    if command == self._stopAction:
                        if self._stopAction(callbk):
                            return True
                        else:
                            break
                    else:
                        callbk(409)
                        self._writeSerialLog('busy - operation not possible')
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
            callbk(500)
        raise __class__.Interrupt

    def plotReadings(self, callbk):
        self._commands.put((self._plotReadings, callbk, None))

    def _plotReadings(self, callbk):
        try:
            self._serial_con.write(b'NDMR\n')
            self._writeSerialLog('NDMR', 'C')
            callbk(200)
            self._writeSerialLog('device output suppressed during operation')
            data = list()
            count = 0
            while True:
                msg = self._serial_con.readline()
                if msg:
                    data.append([count, msg])
                    count += 1
                try:
                    command, callbk, kwargs = self._commands.get_nowait()
                    if command == self._stopAction:
                        self._serial_con.write(b'STP\n')
                        self._writeSerialLog('STP', 'C')
                        if self._waitFor('RDY'):
                            self._writeSerialLog('RDY', 'D')
                            for x in range(len(data)):
                                data[x][1] = int(data[x][1].decode().replace('\n', '').replace('\r', ''))
                            self._savePlotData(data)
                            callbk(200, {'res': data})
                            return True
                        else:
                            callbk(500)
                            break
                    else:
                        callbk(409)
                        self._writeSerialLog('busy - operation not possible')
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
            callbk(500)
        raise __class__.Interrupt

    def findBoundaries(self, callbk):
        self._commands.put((self._findBoundaries, callbk, None))

    def _findBoundaries(self, callbk):
        try:
            self._serial_con.write(b'FB\n')
            self._writeSerialLog('FB', 'C')
            callbk(200)
            self._writeSerialLog('device output suppressed during operation')
            while True:
                try:
                    command, callbk, kwargs = self._commands.get(timeout=1)
                    if command == self._stopAction:
                        self._serial_con.write(b'STP\n')
                        self._writeSerialLog('STP', 'C')
                        result = self._waitFor(':')
                        if self._waitFor('RDY'):
                            self._writeSerialLog('RDY', 'D')
                            callbk(200, {'res': result.replace('\n', '').replace('\r', '')})
                            return True
                        else:
                            callbk(500)
                            break
                    else:
                        self._writeSerialLog('busy - operation not possible')
                        callbk(409)
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
            callbk(500)
        raise __class__.Interrupt

    def buildHistogram(self, callbk, lb, rb, res):
        self._commands.put((self._buildHistogram, callbk, {'lb':lb, 'rb':rb, 'res':res}))

    def _buildHistogram(self, callbk, lb, rb, res):
        try:
            self._serial_con.write(b'HST\n')
            self._writeSerialLog('HST', 'C')
            msg = self._waitFor(':')
            if msg:
                self._writeSerialLog(msg, 'D')
                conf = '{}:{}:{}\n'.format(lb, rb, res)
                self._serial_con.write(conf.encode())
                self._writeSerialLog(conf, 'C')
                resp = self._waitFor(':')
                self._writeSerialLog(resp, 'D')
                if 'NaN' not in resp:
                    callbk(200)
                    self._writeSerialLog('device output suppressed during operation')
                    while True:
                        try:
                            command, callbk, kwargs = self._commands.get(timeout=1)
                            if command == self._stopAction:
                                self._serial_con.write(b'STP\n')
                                self._writeSerialLog('STP', 'C')
                                result = self._waitFor(':')
                                if self._waitFor('RDY'):
                                    self._writeSerialLog('RDY', 'D')
                                    callbk(200, {'res': result.replace('\n', '').replace('\r', '')})
                                    return True
                                else:
                                    callbk(500)
                                    break
                            else:
                                self._writeSerialLog('busy - operation not possible')
                                callbk(409)
                        except Empty:
                            pass
                else:
                    logger.error("could not set histogram settings for device '{}'".format(self._id))
                    callbk(500)
            else:
                logger.error("device '{}' did not enter histogram settings mode".format(self._id))
                callbk(500)
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
            callbk(500)
        raise __class__.Interrupt

    def stopAction(self, callbk):
        self._commands.put((self._stopAction, callbk, None))

    def _stopAction(self, callbk):
        try:
            self._serial_con.write(b'STP\n')
            self._writeSerialLog('STP', 'C')
            if self._waitFor('RDY'):
                self._writeSerialLog('RDY', 'D')
                callbk(200)
                return True
        except SerialTimeoutException:
            callbk(500)
            return False

    def startDetection(self, callbk=None):
        self._commands.put((self._startDetection, callbk, None))

    def _startDetection(self, callbk=None):
        if int(self._rpkwh) > 0:
            #ws = int(3600000 / int(self._rpkwh))
            #kWh = ws / 3600000
            try:
                self._serial_con.write(b'STRT\n')
                self._writeSerialLog('STRT', 'C')
                if callbk:
                    callbk(200)
                while True:
                    msg = self._serial_con.readline()
                    if 'DET' in msg.decode():
                        self._calcAndWriteTotal(1 / int(self._rpkwh))
                        """
                        Client.event(
                            self._extended_id,
                            'detection',
                            json.dumps({
                                'value': self._kwh,
                                'unit': 'kWh',
                                'time': '{}Z'.format(datetime.datetime.utcnow().isoformat())
                            }),
                            block=False
                        )
                        """
                    elif 'CAL' in msg.decode():
                        self._writeSerialLog('CAL', 'D')
                    try:
                        command, callbk, kwargs = self._commands.get_nowait()
                        if command == self._stopAction:
                            if self._stopAction(callbk):
                                return True
                            else:
                                break
                        else:
                            self._writeSerialLog('busy - operation not possible')
                            callbk(409)
                    except Empty:
                        pass
            except (SerialException, SerialTimeoutException) as ex:
                logger.error(ex)
                if callbk:
                    callbk(500)
            raise __class__.Interrupt
        else:
            logger.warning("detection for device '{}' failed - rounds/kWh not set".format(self._id))
            self._writeSerialLog('rotations/kWh not set')
            if callbk:
                callbk(500)

    def startDebug(self, callbk):
        self._commands.put((self._startDebug, callbk, None))

    def _startDebug(self, callbk):
        try:
            self._serial_con.write(b'STRT\n')
            self._writeSerialLog('STRT', 'C')
            callbk(200)
            while True:
                msg = self._serial_con.readline()
                if msg.decode() != '':
                    self._writeSerialLog(msg, 'D')
                try:
                    command, callbk, kwargs = self._commands.get_nowait()
                    if command == self._stopAction:
                        if command(callbk):
                            return True
                        else:
                            break
                    else:
                        self._writeSerialLog('busy - operation not possible')
                        callbk(409)
                except Empty:
                    pass
        except (SerialException, SerialTimeoutException) as ex:
            logger.error(ex)
            callbk(500)
        raise __class__.Interrupt

    def haltController(self, callbk=None):
        self._commands.put((self._haltController, callbk, None))

    def _haltController(self, callbk=None):
        if callbk:
            callbk(200)
        raise __class__.Interrupt
