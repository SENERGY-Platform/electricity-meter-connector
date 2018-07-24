try:
    from connector_client.modules.logger import connector_client_log_handler
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import logging


root_logger = logging.getLogger("serial-gateway")
root_logger.setLevel(logging.INFO)
root_logger.addHandler(connector_client_log_handler)