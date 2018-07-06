try:
    from connector_client.client import Client
    from connector_client.modules.device_pool import DevicePool
    from serial_gateway.manager import SerialManager
    from web_ui.ws_console import WebsocketConsole
    from web_ui.app import WebUI
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import asyncio


loop = asyncio.get_event_loop()
cw = asyncio.get_child_watcher()


if __name__ == '__main__':
    connector_client = Client(device_manager=DevicePool)
    WebsocketConsole(loop)
    WebUI()
    SerialManager()
    loop.run_forever()
