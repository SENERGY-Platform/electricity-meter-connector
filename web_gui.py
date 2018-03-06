try:
    from modules.logger import root_logger
    from flask import Flask, render_template, Response, redirect, url_for
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
        return render_template('gui.html', devices=devices)

    @staticmethod
    @app.route('/<d_id>')
    def device(d_id):
        devices = SerialManager.getDevices()
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
            if end_point == "conf":
                controller.configureDevice(0,0,0)
                return Response(status=200)
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
        return Response(status=500)



"""
import time
import subprocess
import select

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    def liDevices():
        for device in SerialManager.getDevices():
            yield '<a href="{}">{}</a></br>'.format(device, device)
    return Response(liDevices())


@app.route('/<d_id>', methods=['GET'])
def device(d_id):
    functions = '' \
                '<a href="{0}/conf">configure</a></br>' \
                '<a href="{0}/mr">manual read</a></br>' \
                '<a href="{0}/strt">start detection</a></br>' \
                '<a href="{0}/stp">stop action</a></br>'.format(d_id)
    return Response(functions)


@app.route('/<d_id>/<func>', methods=['GET'])
def function(d_id, func):
    controller = SerialManager.getController(d_id)
    if controller:
        if func == "mr":
            controller.manualRead()
            return Response(status=200)
        if func == "stp":
            controller.stopAction()
            return Response(status=200)
    else:
        return Response(status=404)

@app.route('/monitor/ABCH')
def monitor():
    def test():
        controller = SerialManager.getController('ABCH')
        f = subprocess.Popen(['tail', '-F', controller.log_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p = select.poll()
        p.register(f.stdout)
        while True:
            print("in while")
            if p.poll(1):
                yield "data: {}\n\n".format(f.stdout.readline())
            time.sleep(0.1)
    return Response(test(), mimetype="text/event-stream")

@app.route('/test')
def test():
    return redirect(url_for('static', filename='index.html'))

app.run(host='localhost', port=23423)

"""