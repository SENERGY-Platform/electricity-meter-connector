try:
    from connector_client.client import Client
    from connector_client.modules.device_pool import DevicePool
    from serial_gateway.manager import SerialManager
    from web_ui.ws_console import WebsocketConsole
    from web_ui.app import WebUI
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from threading import Thread
import asyncio, time, json, datetime


########### temp fix

from serial_gateway.device_controller import ID_PREFIX, devices_db

dt=25
ndt=400
devices=['62345', '12345', '17890', '67845', '12340', '12890', '67345', '12390']

if ID_PREFIX == 'ee2e6f38-5efe-4818-a9bf-850490e964a9':
    for device in devices:
        if devices_db.getDevice(device):
            print('{} updated'.format(device, devices_db.updateDevice(device, dt=dt, ndt=ndt)))

###########


def pushReadings():
    while True:
        for controller in SerialManager.getControllers():
            try:
                if controller._kwh:
                    Client.event(
                        controller._extended_id,
                        'detection',
                        json.dumps({
                            'value': controller._kwh,
                            'unit': 'kWh',
                            'time': '{}Z'.format(datetime.datetime.utcnow().isoformat())
                        }),
                        block=False
                    )
                    time.sleep(0.1)
            except Exception:
                pass
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
