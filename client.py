"""
   Copyright 2018 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

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
