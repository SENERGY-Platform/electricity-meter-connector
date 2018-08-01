try:
    from connector_client.client import Client
    from connector_client.modules.device_pool import DevicePool
    from serial_gateway.manager import SerialManager
    from serial_gateway.logger import root_logger
    from web_ui.ws_console import WebsocketConsole
    from web_ui.app import WebUI
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread
import asyncio, time, json, datetime


logger = root_logger.getChild(__name__)

def pushReadings():
    while True:
        for controller in SerialManager.getControllers():
            try:
                Client.event(
                    controller._extended_id,
                    'detection',
                    json.dumps({
                        'value': float(controller._kwh),
                        'unit': 'kWh',
                        'time': '{}Z'.format(datetime.datetime.utcnow().isoformat())
                    }),
                    block=False
                )
                time.sleep(0.1)
            except Exception as ex:
                logger.error(ex)
        time.sleep(20)

readings_scraper = Thread(target=pushReadings, name="Scraper")

loop = asyncio.get_event_loop()
cw = asyncio.get_child_watcher()


if __name__ == '__main__':
    connector_client = Client(device_manager=DevicePool)
    WebsocketConsole(loop)
    WebUI()
    SerialManager()
    readings_scraper.start()
    loop.run_forever()
