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
    _id_field = ('id', 'TEXT')
    _nat_field = ('nat', 'INTEGER')
    _dt_field = ('dt', 'INTEGER')
    _strt_field = ('strt', 'INTEGER')
    _rpkwh_field = ('rpkwh', 'INTEGER')
    _lld_field = ('lld', 'INTEGER')
    _kWh_field = ('kWh', 'TEXT')
    _sm_conf_table = 'sm_conf'
    _id_prefix_field = ('id_prefix', 'TEXT')

    def __init__(self):
        if not os.path.isfile(__class__._db_path):
            logger.debug('no database found')
            query = 'CREATE TABLE {table} ({id} {id_t} PRIMARY KEY, {nat} {nat_t} DEFAULT 0, {dt} {dt_t} DEFAULT 0, {strt} {strt_t} DEFAULT 0, {rpkwh} {rpkwh_t} DEFAULT 0, {lld} {lld_t} DEFAULT 0, {kWh} {kWh_t} DEFAULT 0.0)'.format(
                table=__class__._devices_table,
                id=__class__._id_field[0],
                id_t=__class__._id_field[1],
                nat=__class__._nat_field[0],
                nat_t=__class__._nat_field[1],
                dt=__class__._dt_field[0],
                dt_t=__class__._dt_field[1],
                strt=__class__._strt_field[0],
                strt_t=__class__._strt_field[1],
                rpkwh=__class__._rpkwh_field[0],
                rpkwh_t=__class__._rpkwh_field[1],
                lld=__class__._lld_field[0],
                lld_t=__class__._lld_field[1],
                kWh=__class__._kWh_field[0],
                kWh_t=__class__._kWh_field[1]
            )
            self._executeQuery(query)
            query = 'CREATE TABLE {table} ({id_prefix} {id_prefix_t})'.format(
                table=__class__._sm_conf_table,
                id_prefix=__class__._id_prefix_field[0],
                id_prefix_t=__class__._id_prefix_field[1]
            )
            self._executeQuery(query)
            query = 'INSERT INTO {table} ({id_prefix}) VALUES ("{id_prefix_v}")'.format(
                table=__class__._sm_conf_table,
                id_prefix=__class__._id_prefix_field[0],
                id_prefix_v=str(uuid4())
            )
            self._executeQuery(query)
            logger.debug('created new database')
        else:
            logger.debug("found database at '{}'".format(__class__._db_path))

    def _executeQuery(self, query):
        try:
            db_conn = sqlite3.connect(__class__._db_path)
            cursor = db_conn.cursor()
            cursor.execute(query)
            if any(statement in query for statement in ('CREATE', 'INSERT', 'DELETE', 'UPDATE')):
                db_conn.commit()
                result = True
            else:
                result = cursor.fetchall()
            db_conn.close()
            return result
        except Exception as ex:
            logger.error(ex)
            return False

    def addDevice(self, device_id):
        query = 'INSERT INTO {table} ({id}) VALUES ("{id_v}")'.format(
            table=__class__._devices_table,
            id=__class__._id_field[0],
            id_v=device_id,
        )
        return self._executeQuery(query)

    def getDeviceConf(self, device_id):
        query = 'SELECT {nat}, {dt}, {strt}, {rpkwh}, {lld}, {kWh} FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            nat=__class__._nat_field[0],
            dt=__class__._dt_field[0],
            strt=__class__._strt_field[0],
            rpkwh=__class__._rpkwh_field[0],
            lld=__class__._lld_field[0],
            kWh=__class__._kWh_field[0],
            id=__class__._id_field[0],
            id_v=device_id
        )
        result = self._executeQuery(query)
        if result:
            return {
                'nat': result[0][0],
                'dt': result[0][1],
                'strt': result[0][2],
                'rpkwh': result[0][3],
                'lld': result[0][4],
                'kWh': result[0][5],
            }
        return None

    def updateDeviceConf(self, device_id, nat=None, dt=None, strt=None, rpkwh=None, lld=None, kWh=None):
        values = list()
        if nat:
            values.append('{}={}'.format(__class__._nat_field[0], nat))
        if dt:
            values.append('{}={}'.format(__class__._dt_field[0], dt))
        if strt:
            values.append('{}={}'.format(__class__._strt_field[0], strt))
        if rpkwh:
            values.append('{}={}'.format(__class__._rpkwh_field[0], rpkwh))
        if lld:
            values.append('{}={}'.format(__class__._lld_field[0], lld))
        if kWh:
            values.append('{}="{}"'.format(__class__._kWh_field[0], str(kWh)))
        values = ', '.join(map(str, values))
        if values:
            query = 'UPDATE {table} SET {values} WHERE {id}="{id_v}"'.format(
                table=__class__._devices_table,
                values=values,
                id=__class__._id_field[0],
                id_v=device_id
            )
            return self._executeQuery(query)
        return False

    def getIdPrefix(self):
        query = 'SELECT {id_prefix} FROM {table} WHERE _rowid_="1"'.format(
            table=__class__._sm_conf_table,
            id_prefix=__class__._id_prefix_field[0]
        )
        result = self._executeQuery(query)
        if result:
            return result[0][0]
        return None
