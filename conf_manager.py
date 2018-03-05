import os, inspect, configparser


config = configparser.ConfigParser()

conf_file_path = '{}/devices.conf'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))


if not os.path.isfile(conf_file_path):
    print('No devices config file found')
    config['SERIAL_MANAGER'] = {
        'id_prefix': ''
    }
    with open(conf_file_path, 'w') as conf_file:
        config.write(conf_file)
    exit('Created blank config file for devices')


try:
    config.read(conf_file_path)
except Exception as ex:
    exit(ex)


def updateConf(section, option, value):
    if config.has_section(section):
        config.set(section=section, option=option, value=value)
        try:
            with open(conf_file_path, 'w') as conf_file:
                config.write(conf_file)
        except Exception as ex:
            print(ex)


def writeDeviceConf(d_id, nat=None, dt=None, lld=None, strt=None):
    if not config.has_section(d_id):
        config[d_id] = {
            'nat': nat,
            'dt': dt,
            'lld': lld,
            'strt': 0
        }
    else:
        if nat:
            config.set(section=d_id, option='nat', value=nat)
        if dt:
            config.set(section=d_id, option='dt', value=dt)
        if lld:
            config.set(section=d_id, option='lld', value=lld)
        if strt:
            config.set(section=d_id, option='strt', value=strt)
    try:
        with open(conf_file_path, 'w') as conf_file:
            config.write(conf_file)
    except Exception as ex:
        print(ex)


def readDeviceConf(d_id):
    if config.has_section(d_id):
        return (config[d_id]['nat'], config[d_id]['dt'], config[d_id]['lld'], config[d_id]['strt'])
    return None



ID_PREFIX = config['SERIAL_MANAGER']['id_prefix']
if not ID_PREFIX:
    exit('Please enter a device ID prefix in devices.conf')
