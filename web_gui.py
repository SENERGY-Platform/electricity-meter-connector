try:
    from modules.logger import root_logger
    from flask import Flask, render_template, Response, redirect, url_for
    from serial_manager import SerialManager
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
        return render_template('index.html')

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