try:
    from flask import Flask, render_template, Response, request, jsonify
    from serial_manager import SerialManager
    from ws_console import WebsocketConsole
    from logger import root_logger, connector_client_log_handler
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread
import logging, time, os


logger = root_logger.getChild(__name__)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(connector_client_log_handler)
werkzeug_logger.setLevel(logging.WARNING)


class WebGUI(Thread):
    app = Flask(__name__)

    def __init__(self):
        super().__init__()
        self._host = '0.0.0.0'
        self._port = 8000
        self.start()

    def run(self):
        __class__.app.run(host=self._host, port=self._port)

    @staticmethod
    @app.route('/', methods=['GET'])
    def index():
        devices = SerialManager.getDevices()
        devices.sort()
        return render_template('gui.html', devices=devices)

    @staticmethod
    @app.route('/<d_id>', methods=['GET'])
    def device(d_id):
        devices = SerialManager.getDevices()
        devices.sort()
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                WebsocketConsole.setSource(controller.log_file)
                return render_template('gui.html', devices=devices, d_id=d_id)
        except Exception as ex:
            logger.error(ex)
        return render_template('gui.html', devices=devices)

    @staticmethod
    @app.route('/<d_id>/<end_point>', methods=['POST'])
    def endpoint(d_id, end_point):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                if end_point == "rs":
                    controller.readSensor()
                    return Response(status=200)
                if end_point == "fe":
                    controller.findExtrema()
                    return Response(status=200)
                if end_point == "dbg":
                    controller.startDebug()
                    return Response(status=200)
                if end_point == "strt":
                    controller.startDetection()
                    return Response(status=200)
                if end_point == "stp":
                    controller.stopAction()
                    return Response(status=200)
                if end_point == "eas":
                    controller.enableAutoStart()
                    return Response(status=200)
                if end_point == "das":
                    controller.disableAutoStart()
                    return Response(status=200)
                if end_point == "res":
                    controller.haltController()
                    return Response(status=200)
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)

    @staticmethod
    @app.route('/<d_id>/conf', methods=['POST', 'GET'])
    def conf(d_id):
        try:
            controller = SerialManager.getController(d_id)
            if controller:
                if request.method == 'POST':
                    conf = request.get_json()
                    controller.setRotPerKwh(conf['rpkwh'])
                    controller.setKwh(conf['tkwh'])
                    controller.setName(conf['name'])
                    controller.configureDevice(conf['nat'], conf['dt'], conf['ndt'], conf['lld'])
                    return Response(status=200)
                if request.method == 'GET':
                    conf = controller.getConf()
                    if conf:
                        return jsonify(conf)
                    else:
                        return Response(status=404)
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