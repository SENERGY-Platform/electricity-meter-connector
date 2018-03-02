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


def writeDeviceConf(d_id, nat, dt, lld):
    if not config.has_section(d_id):
        config[d_id] = {
            'nat': nat,
            'dt': dt,
            'lld': lld
        }
    else:
        config.set(section=d_id, option='nat', value=nat)
        config.set(section=d_id, option='dt', value=dt)
        config.set(section=d_id, option='lld', value=lld)
    try:
        with open(conf_file_path, 'w') as conf_file:
            config.write(conf_file)
    except Exception as ex:
        print(ex)


def readDeviceConf(d_id):
    if config.has_section(d_id):
        return (config[d_id]['nat'], config[d_id]['dt'], config[d_id]['lld'])
    return None



ID_PREFIX = config['SERIAL_MANAGER']['id_prefix']
if not ID_PREFIX:
    exit('Please enter a device ID prefix in devices.conf')
