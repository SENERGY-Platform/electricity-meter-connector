import os, sys, inspect
import_path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"connector_client")))
if import_path not in sys.path:
    sys.path.insert(0, import_path)

try:
    from connector.client import Client
    from serial_manager import SerialManager
    from modules.device_pool import DevicePool
    from ws_console import WebsocketConsole
    from web_gui import WebGUI
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import asyncio


loop = asyncio.get_event_loop()
cw = asyncio.get_child_watcher()


if __name__ == '__main__':
    connector_client = Client(device_manager=DevicePool)
    WebsocketConsole(loop)
    WebGUI()
    SerialManager()
    loop.run_forever()
