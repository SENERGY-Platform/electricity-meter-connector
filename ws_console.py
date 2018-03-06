try:
    import websockets
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

from queue import Empty
from threading import Thread
import concurrent.futures, functools, asyncio, subprocess, select

logger = root_logger.getChild(__name__)

class WebsocketConsole(Thread):
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
            if __class__._source:
                tail_process = subprocess.Popen(['tail', '-F', __class__._source], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                poll_obj = select.poll()
                poll_obj.register(tail_process.stdout)
                def readTail():
                    logger.info(poll_obj.poll(0))
                    if poll_obj.poll(1):
                        line = tail_process.stdout.readline().decode()
                        return line.replace('\n', '').replace('\r', '')
                    else:
                        tail_process.kill()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    while True:
                        logger.info("inner w")
                        payload = await self._event_loop.run_in_executor(
                            executor,
                            readTail
                        )
                        logger.info(payload)
                        if payload:
                            try:
                                await websocket.send(payload)
                            except Exception as ex:
                                logger.warning("could not send data - {}".format(ex))
                                break
                        else:
                            break
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
