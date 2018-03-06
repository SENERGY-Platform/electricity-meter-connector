import os, sys, inspect
import_path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"connector_client")))
if import_path not in sys.path:
    sys.path.insert(0, import_path)

try:
    from modules.logger import root_logger
    from connector.client import Client
    from serial_manager import SerialManager
    from modules.device_pool import DevicePool
    from ws_console import WebsocketConsole
    from web_gui import WebGUI
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import asyncio


logger = root_logger.getChild(__name__)


loop = asyncio.get_event_loop()
cw = asyncio.get_child_watcher()

SerialManager()
WebsocketConsole(loop)
WebGUI()
loop.run_forever()


"""
import time
time.sleep(10)
device = SerialManager.getController("ABCH")
device.manualRead()
time.sleep(30)
device.stopAction()
"""



"""import websockets
import asyncio
from asyncio.subprocess import PIPE, STDOUT

class WebsocketConsole():
    _source = None

    def __init__(self):
        super().__init__()
        self.start()

    @staticmethod
    def setSource(src):
        __class__._source = src

    async def send(self, websocket, path):
        while True:
            logger.info("outer w")
            if True:
                tail_process = await asyncio.create_subprocess_exec('tail', '-F', '/Users/yann/DEV/PROJECTS/ferraris-arduino-serial-gateway/devices/ABCH.log', stdout=PIPE, stderr=STDOUT, loop=self._event_loop)
                while True:
                    logger.info("inner w")
                    try:
                        line = await asyncio.wait_for(tail_process.stdout.readline(), timeout=5, loop=self._event_loop)
                        logger.info(line)
                    except asyncio.TimeoutError:
                        logger.info("readline timeout")
                        line = None
                    if line:
                        try:
                            line = line.decode().replace('\n', '').replace('\r', '')
                            await websocket.send(line)
                        except Exception as ex:
                            logger.warning("could not send data - {}".format(ex))
                    else:
                        try:
                            await websocket.ping()
                        except Exception as ex:
                            logger.warning(ex)
                            break
                tail_process.kill()
                await tail_process.wait()
                break
            else:
                try:
                    await websocket.ping()
                    await asyncio.sleep(1)
                except Exception as ex:
                    logger.warning(ex)
                    break
        __class__._source = None
        logger.info('#################')

    def start(self):
        try:
            self._event_loop = asyncio.get_event_loop()
        except (RuntimeError, AssertionError):
            logger.debug("no event loop found")
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            logger.debug("created new event loop")
        server = websockets.serve(self.send, '127.0.0.1', 5678)
        self._event_loop.run_until_complete(server)
        self._event_loop.run_forever()

WebsocketConsole()"""
