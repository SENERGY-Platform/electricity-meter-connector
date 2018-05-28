try:
    from logger import root_logger
    from modules.singleton import Singleton
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import inspect, os, sqlite3
from uuid import uuid4

logger = root_logger.getChild(__name__)


class DevicesDatabase(metaclass=Singleton):
    _db_path = '{}/devices.sqlite'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
    _devices_table = 'devices'
    _devices_col = [
        ('id', 'TEXT PRIMARY KEY'),
        ('nat', 'INTEGER DEFAULT 0'),
        ('lld', 'INTEGER DEFAULT 0'),
        ('lb', 'INTEGER DEFAULT 0'),
        ('rb', 'INTEGER DEFAULT 0'),
        ('dt', 'INTEGER DEFAULT 0'),
        ('ndt', 'INTEGER DEFAULT 0'),
        ('strt', 'INTEGER DEFAULT 0'),
        ('rpkwh', 'INTEGER DEFAULT 0'),
        ('kwh', 'TEXT DEFAULT "0.0"'),
        ('name', 'TEXT'),
        ('mode', 'TEXT DEFAULT "I"')
    ]
    _sm_conf_table = 'sm_conf'
    _sm_conf_col = [
        ('id_prefix', 'TEXT')
    ]

    def __init__(self):
        if not os.path.isfile(__class__._db_path):
            logger.debug('no database found')
            flatten = lambda li: [' '.join(map(str, sublist)) for sublist in li]
            columns = ', '.join(map(str, flatten(__class__._devices_col)))
            query = 'CREATE TABLE {} ({})'.format(__class__._devices_table, columns)
            self._executeQuery(query)
            columns = ', '.join(map(str, flatten(__class__._sm_conf_col)))
            query = 'CREATE TABLE {} ({})'.format(__class__._sm_conf_table, columns)
            self._executeQuery(query)
            query = 'INSERT INTO {table} ({id_prefix}) VALUES ("{id_prefix_v}")'.format(
                table=__class__._sm_conf_table,
                id_prefix=__class__._sm_conf_col[0][0],
                id_prefix_v=str(uuid4())
            )
            self._executeQuery(query)
            logger.debug('created new database')
        else:
            logger.debug("found database at '{}'".format(__class__._db_path))

    def _executeQuery(self, query) -> sqlite3.Row:
        try:
            db_conn = sqlite3.connect(__class__._db_path)
            db_conn.row_factory = sqlite3.Row
            cursor = db_conn.cursor()
            cursor.execute(query)
            if any(statement in query for statement in ('CREATE', 'INSERT', 'DELETE', 'UPDATE')):
                db_conn.commit()
                result = True
            else:
                result = cursor.fetchone()
            db_conn.close()
            return result
        except Exception as ex:
            logger.error(ex)
            return False

    def addDevice(self, device_id):
        query = 'INSERT INTO {table} ({id}) VALUES ("{id_v}")'.format(
            table=__class__._devices_table,
            id=__class__._devices_col[0][0],
            id_v=device_id,
        )
        return self._executeQuery(query)

    def getDeviceConf(self, device_id):
        query = 'SELECT * FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            id=__class__._devices_col[0][0],
            id_v=device_id
        )
        result = self._executeQuery(query)
        if result:
            r_dict = dict()
            for key in result.keys():
                r_dict[key] = result[key]
            return r_dict
        return None

    def updateDeviceConf(self, device_id, **kwargs):
        firstElement = lambda li: [sublist[0] for sublist in li]
        columns = firstElement(__class__._devices_col)
        values = list()
        for arg, val in kwargs.items():
            if arg in columns:
                if type(val) in (str, float):
                    values.append('{}="{}"'.format(arg, val))
                else:
                    values.append('{}={}'.format(arg, val))
        values = ', '.join(map(str, values))
        if values:
            query = 'UPDATE {table} SET {values} WHERE {id}="{id_v}"'.format(
                table=__class__._devices_table,
                values=values,
                id=__class__._devices_col[0][0],
                id_v=device_id
            )
            return self._executeQuery(query)
        return False

    def getIdPrefix(self):
        query = 'SELECT {id_prefix} FROM {table} WHERE _rowid_="1"'.format(
            table=__class__._sm_conf_table,
            id_prefix=__class__._sm_conf_col[0][0]
        )
        result = self._executeQuery(query)
        if result:
            return result[__class__._sm_conf_col[0][0]]
        return None
