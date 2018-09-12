"""
   Copyright 2018 SEPL Team

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
    import websockets
    from serial_gateway.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

from threading import Thread
import asyncio, time
from asyncio.subprocess import PIPE, STDOUT

logger = root_logger.getChild(__name__)

class WebsocketConsole(Thread):
    _source = None

    def __init__(self, main_loop):
        super().__init__()
        self._main_loop = main_loop
        self.start()

    @staticmethod
    def setSource(src):
        __class__._source = src

    async def send(self, websocket, path):
        while True:
            if __class__._source:
                file_to_tail = __class__._source
                __class__._source = None
                tail_process = await asyncio.create_subprocess_exec('tail', '-F', file_to_tail, stdout=PIPE, stderr=STDOUT, loop=self._event_loop)
                while True:
                    try:
                        line = await asyncio.wait_for(tail_process.stdout.readline(), timeout=0.4, loop=self._event_loop)
                        if line and websocket.open:
                            try:
                                line = line.decode().replace('\n', '').replace('\r', '')
                                await websocket.send(line)
                            except Exception as ex:
                                logger.error("could not send data - {}".format(ex))
                                break
                    except (TimeoutError, asyncio.TimeoutError):
                        pass
                    except Exception as ex:
                        logger.error(ex)
                    try:
                        await websocket.ping()
                    except Exception as ex:
                        if not any(code in str(ex) for code in ["1000", "1001"]):
                            logger.error(ex)
                        break
                tail_process.kill()
                await tail_process.wait()
                break
            else:
                try:
                    await websocket.ping()
                    await asyncio.sleep(1)
                except Exception as ex:
                    if not any(code in str(ex) for code in ["1000", "1001"]):
                        logger.error(ex)
                    break

    def run(self):
        while not self._main_loop.is_running():
            time.sleep(1)
        try:
            self._event_loop = asyncio.get_event_loop()
        except (RuntimeError, AssertionError):
            logger.debug("no event loop found")
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            logger.debug("created new event loop")
        try:
            server = websockets.serve(self.send, '0.0.0.0', 5678)
            self._event_loop.run_until_complete(server)
            self._event_loop.run_forever()
        except Exception as ex:
            logger.error(ex)
        logger.error('websocket console exited')