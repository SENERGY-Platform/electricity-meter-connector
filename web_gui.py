try:
    from modules.logger import root_logger
    from flask import Flask, render_template, Response, request
    from serial_manager import SerialManager
    from ws_console import WebsocketConsole
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread
import time

logger = root_logger.getChild(__name__)



class WebGUI(Thread):
    app = Flask(__name__)

    def __init__(self):
        super().__init__()
        self._host = 'localhost'
        self._port = 8000
        self.start()

    @staticmethod
    @app.route('/test')
    def test():
        def liDevices():
            for device in SerialManager.getDevices():
                yield '<a href="{}">{}</a></br>'.format(device, device)
        return Response(liDevices())

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
        controller = SerialManager.getController(d_id)
        if controller:
            WebsocketConsole.setSource(controller.log_file)
        return render_template('gui.html', devices=devices, d_id=d_id)

    @staticmethod
    @app.route('/<d_id>/<end_point>', methods=['POST'])
    def endpoint(d_id, end_point):
        devices = SerialManager.getDevices()
        controller = SerialManager.getController(d_id)
        if controller and d_id in devices:
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
        return Response(status=500)

    @staticmethod
    @app.route('/<d_id>/conf', methods=['POST'])
    def conf(d_id):
        devices = SerialManager.getDevices()
        controller = SerialManager.getController(d_id)
        nat, dt, lld = request.form['nat'], request.form['dt'], request.form['lld']
        if controller and d_id in devices:
            controller.configureDevice(nat, dt, lld)
            return Response(status=200)
        return Response(status=500)
