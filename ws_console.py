try:
    import websockets
    from modules.logger import root_logger
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
                tail_process = await asyncio.create_subprocess_exec('tail', '-F', __class__._source, stdout=PIPE, stderr=STDOUT, loop=self._event_loop)
                while True:
                    try:
                        line = await asyncio.wait_for(tail_process.stdout.readline(), timeout=5, loop=self._event_loop)
                        if line:
                            try:
                                line = line.decode().replace('\n', '').replace('\r', '')
                                await websocket.send(line)
                            except Exception as ex:
                                logger.warning("could not send data - {}".format(ex))
                                break
                    except asyncio.TimeoutError:
                        pass
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
        server = websockets.serve(self.send, '127.0.0.1', 5678)
        self._event_loop.run_until_complete(server)
        self._event_loop.run_forever()