try:
    import websockets
    from modules.logger import root_logger
    from device_controller import OUT_QUEUE
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

from queue import Empty
from threading import Thread
import concurrent.futures, functools, asyncio

logger = root_logger.getChild(__name__)

class WebsocketConsole(Thread):
    def __init__(self):
        super().__init__()
        self.start()

    async def send(self, websocket, path):
        OUT_QUEUE.queue.clear()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                try:
                    payload = await self._event_loop.run_in_executor(
                        executor,
                        functools.partial(OUT_QUEUE.get, timeout=1)
                    )
                    try:
                        await websocket.send(payload)
                    except Exception as ex:
                        logger.warning("could not send data - {}".format(ex))
                        break
                except Empty:
                    pass

    def run(self):
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
