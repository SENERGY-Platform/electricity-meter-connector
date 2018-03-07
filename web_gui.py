try:
    from modules.logger import root_logger
    from flask import Flask, render_template, Response, request
    from serial_manager import SerialManager
    from ws_console import WebsocketConsole
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread


logger = root_logger.getChild(__name__)


class WebGUI(Thread):
    app = Flask(__name__)

    def __init__(self):
        super().__init__()
        self._host = 'localhost'
        self._port = 8000
        self.start()

    def run(self):
        __class__.app.run(host=self._host, port=self._port)

    @staticmethod
    @app.route('/')
    def index():
        devices = SerialManager.getDevices()
        devices.sort()
        return render_template('gui.html', devices=devices)

    @staticmethod
    @app.route('/<d_id>')
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
                if end_point == "mr":
                    controller.manualRead()
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
                    nat, dt, lld, ws = request.form.get('nat'), request.form.get('dt'), request.form.get('lld'), request.form.get('ws')
                    controller.configureDevice(nat, dt, lld)
                    return Response(status=200)
        except Exception as ex:
            logger.error(ex)
        return Response(status=500)
