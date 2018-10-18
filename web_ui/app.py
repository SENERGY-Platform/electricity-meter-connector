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
    from flask import Flask, render_template, Response, request
    from serial_gateway.manager import SerialManager
    from web_ui.ws_console import WebsocketConsole
    from serial_gateway.logger import root_logger, connector_client_log_handler
    from connector_client.configuration import VERSION
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread, Event
import logging, time, functools, json


logger = root_logger.getChild(__name__)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(connector_client_log_handler)
werkzeug_logger.setLevel(logging.WARNING)


def read_sg_version():
    values = dict()
    with open('serial_gateway/__init__.py', 'r') as init_file:
        exec(init_file.read(), values)
    return values.get('__version__')

def read_ui_version():
    values = dict()
    with open('web_ui/__init__.py', 'r') as init_file:
        exec(init_file.read(), values)
    return values.get('__version__')


class DeviceEvent(Event):
    def __init__(self):
        super().__init__()
        self.status = None
        self.message = None

class WebUI(Thread):
    app = Flask(__name__)

    def __init__(self):
        super().__init__()
        self._host = '0.0.0.0'
        self._port = 8000
        self.start()

    def run(self):
        logger.info("starting on port {}".format(self._port))
        __class__.app.run(host=self._host, port=self._port, threaded=True, use_reloader=False)

    @staticmethod
    def callbk(event, status, msg=None):
        event.status = status
        event.message = msg
        event.set()

    @staticmethod
    @app.route('/', methods=['GET'])
    def index():
        devices = SerialManager.getDevices()
        devices.sort()
        return render_template('gui.html', sg_v=read_sg_version(), ui_v=read_ui_version(), cc_v=VERSION)

    @staticmethod
    @app.route('/devices', methods=['GET'])
    def devices():
        devices = SerialManager.getDevices()
        devices.sort()
        return Response(status=200, response=json.dumps(devices))

    @staticmethod
    @app.route('/devices/<d_id>', methods=['POST', 'GET'])
    def device(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                if request.method == 'POST':
                    sett = request.get_json()
                    controller.setSettings(sett['rpkwh'], sett['tkwh'], sett['name'])
                if request.method == 'GET':
                    sett = controller.getSettings()
                return Response(status=200, response=json.dumps(sett))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/co', methods=['POST'])
    def consoleOutput(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                WebsocketConsole.setSource(controller.log_file)
                time.sleep(0.5)
                return Response(status=200)
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/rs', methods=['POST'])
    def readSensor(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.readSensor(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/pr', methods=['POST'])
    def plotReadings(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.plotReadings(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/gp', methods=['GET'])
    def getPlot(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                data = controller.getPlotData()
                if data:
                    return Response(status=200, response=json.dumps({'res': data}))
                return Response(status=404)
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/dbg', methods=['POST'])
    def startDebug(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.startDebug(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/strt', methods=['POST'])
    def startDetection(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.startDetection(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/stp', methods=['POST'])
    def stopAction(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.stopAction(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/as', methods=['POST'])
    def setAutoStart(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                req = request.get_json()
                controller.setAutoStart(req['state'])
                return Response(status=200, response=json.dumps(req))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/res', methods=['POST'])
    def resetController(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.haltController(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/fb', methods=['POST'])
    def getBoundaries(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                controller.findBoundaries(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/hst', methods=['POST'])
    def getHistogram(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                conf = request.get_json()
                controller.buildHistogram(functools.partial(__class__.callbk, event), conf['lb'], conf['rb'], conf['res'])
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/conf', methods=['POST', 'GET'])
    def conf(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                if request.method == 'POST':
                    conf = request.get_json()
                    controller.setConf(functools.partial(__class__.callbk, event), conf['mode'], conf['conf_a'], conf['conf_b'], conf['dt'], conf['ndt'])
                if request.method == 'GET':
                    conf = controller.getConf()
                    event.set()
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(conf))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.after_request
    def noCacheHeaders(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @staticmethod
    @app.template_filter('autoversion')
    def autoversionFilter(filename):
        newfilename = "{0}?{1}".format(filename, time.time())
        return newfilename
