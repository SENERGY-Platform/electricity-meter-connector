try:
    from connector_client.client import Client
    from connector_client.modules.device_pool import DevicePool
    from serial_manager import SerialManager
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
