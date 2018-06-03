try:
    from flask import Flask, render_template, Response, request
    from serial_manager import SerialManager
    from ws_console import WebsocketConsole
    from logger import root_logger, connector_client_log_handler
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread, Event
import logging, time, functools, json


logger = root_logger.getChild(__name__)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(connector_client_log_handler)
werkzeug_logger.setLevel(logging.WARNING)

class DeviceEvent(Event):
    def __init__(self):
        super().__init__()
        self.status = None
        self.message = None

class WebGUI(Thread):
    app = Flask(__name__)

    def __init__(self):
        super().__init__()
        self._host = '0.0.0.0'
        self._port = 8000
        self.start()

    def run(self):
        logger.info("starting on port {}".format(self._port))
        __class__.app.run(host=self._host, port=self._port)

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
        return render_template('gui.html')

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
    @app.route('/devices/<d_id>/fb', methods=['POST', 'GET'])
    def getBoundaries(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                if request.method == 'POST':
                    controller.findBoundaries(functools.partial(__class__.callbk, event))
                if request.method == 'GET':
                    controller.stopAction(functools.partial(__class__.callbk, event))
                event.wait(timeout=15)
                return Response(status=event.status, response=json.dumps(event.message))
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/devices/<d_id>/hst', methods=['POST', 'GET'])
    def getHistogram(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                event = DeviceEvent()
                if request.method == 'POST':
                    conf = request.get_json()
                    controller.buildHistogram(functools.partial(__class__.callbk, event), conf['lb'], conf['rb'], conf['res'])
                if request.method == 'GET':
                    controller.stopAction(functools.partial(__class__.callbk, event))
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