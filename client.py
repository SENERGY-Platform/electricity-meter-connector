import os, sys, inspect
import_path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"connector_client")))
if import_path not in sys.path:
    sys.path.insert(0, import_path)

try:
    from modules.logger import root_logger
    from connector.client import Client
    from serial_manager import SerialManager
    from modules.device_pool import DevicePool
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))


logger = root_logger.getChild(__name__)


test = SerialManager()
test.start()