# /usr/bin/python3
# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2021 David Hunter
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# TODO(DPH) Add conf_validation() rotuine

import sys
import speedtest
import influxdb
import logging
import logging.handlers
import json
import os
import argparse
import time

__AUTHOR__ = 'David Hunter'
__VERSION__ = 'beta-1.5'
__LOG_NAME__ = ''
__TITLE__ = 'speedtest_influx.py'
__DEBUG__ = False
SUCCESS = True
FAILED = False


def set_command_options():
    usage = 'Retrieves upload/dowload information from the speedtest application and logs into InfluxDB.'
    parser = argparse.ArgumentParser(
        prog='speedtest-influx', description=usage, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'configfile', help='Name of the configuration file.', type=str, default='config.json')
    parser.add_argument('--log', '--log_level', dest='log_level',
                        action='store', type=str, default='info',
                        help='Set the logging level [debug info warning error] (default: %(default)s)')
    parser.add_argument('-l', '--log_file', help='Set the logfile name. (default: %(default)s)',
                        action='store', type=str, default='speedtest_influx.log')
    parser.add_argument('-o', '--output', help='Output directory to store results files. (default: %(default)s)',
                        action='store', type=str, dest='output_dir', default='./')
    parser.add_argument('-v', '--version', help='Prints the version',
                        action='version', version=__VERSION__)
    parser.add_argument('-i', '--interactive',
                        help='Run program once.', action='store_true')
    parser.add_argument(
        '-j', '--json', help='Save original JSON data files.', action='store_true')

    return (parser)


def set_logging_level(log_level, log_file):
    global __DEBUG__
    fmt = "%(asctime)-15s %(levelname)-5s %(lineno)5d:%(module)s:%(funcName)-25s %(message)s"
    msg = 'Starting ' + __TITLE__ + ' ' + __VERSION__

    if log_level:
        if 'debug' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.DEBUG)
            logging.debug(msg)
            __DEBUG__ = True

        elif 'warning' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.WARNING)
            logging.warning(msg)

        elif 'error' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.ERROR)
            logging.error(msg)

        elif 'info' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.INFO)
            logging.info(msg)

        else:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.INFO)
            logging.error(msg)
            logging.error('Invalid debug level.')
            return(FAILED)

    return(SUCCESS)


def get_command_options(parser):
    args = parser.parse_args()
    log_file = args.log_file
    options = {}
    options['log_file'] = log_file
    options['log_level'] = args.log_level

    if not set_logging_level(args.log_level, args.log_file):
        sys.exit('Unable to set logging level.  Unrecoverable error.')

    if args.configfile:
        if os.path.exists(args.configfile):
            options['config_file'] = args.configfile
        else:
            logging.error('Configuration file ' +
                          args.configfile + ' does not exist.')
            return(FAILED)

    if not os.path.isdir(args.output_dir):
        logging.error('The output directory ' +
                      str(args.output_dir) + ' does not exist.')
        return(FAILED)
    else:
        options['output_dir'] = args.output_dir

    if args.json:
        options['json'] = True
    else:
        options['json'] = False

    if args.interactive:
        options['interactive'] = True
    else:
        options['interactive'] = False

    for key in options:
        logging.info(str(key) + ' : [' + str(options[key]) + ']')
    return (options)


def get_config(conf_file):
    if os.path.exists(conf_file):
        with open(conf_file) as json_config_file:
            data = json.load(json_config_file)
            logging.info('server : [' + str(data['database']['server']) + ']')
            logging.info('port : [' + str(data['database']['port']) + ']')
            logging.info('name : [' + str(data['database']['name']) + ']')
            for key in data['speedtest']:
                logging.info(
                    str(key) + ' : [' + str(data['speedtest'][key] + ']'))

    else:
        logging.error(conf_file + ' does not exist')
        return(FAILED)
    return(data)


def get_wait_time(t):
    period = t[-1]
    s_duration = int(t[:-1])

    if period == 's':
        logging.info('Wait time is %d seconds.', (s_duration))
        return(s_duration)
    elif period == 'm':
        logging.info('Wait time %d minutes.', (s_duration))
        return(s_duration*60)
    elif period == 'h':
        logging.info('Wait time %d hours.', (s_duration))
        return(s_duration*360)
    elif period == 'd':
        logging.info('Wait time %d days.', (s_duration))
        return((s_duration*360)*24)
    else:
        logging.error('Invalid waiting period.  Value read was %s', (t))
        return(FAILED)


def get_servers(s, pref_servers, any_server):
    try:
        s.get_servers(pref_servers)

    except speedtest.NoMatchedServers:
        logging.info('Preferred servers not available.')
        try:
            if any_server == 'True':
                logging.info('Getting list of available servers.')
                s.get_servers()

            else:
                logging.info('No servers available.')
                return(FAILED)

        except Exception as err:
            logging.error('Failed to get server list.')
            logging.exception(err)
            return(FAILED)

    except Exception as err:
        logging.exception(err)
        return(FAILED)

    try:
        s.get_best_server()
        logging.info('Server url chosen %s',
                     (s.results.dict()['server']['url']))
        return(True)

    except speedtest.SpeedtestBestServerFailure as err:
        logging.exception(err)
        return(FAILED)

    except Exception as err:
        logging.exception(err)
        return(FAILED)


def conn_speedtest():
    try:
        s = speedtest.Speedtest()
    except Exception as err:
        logging.error('speedtest failure')
        logging.exception(err)
        return(FAILED)
    return(s)


def create_data_points(data, json_data):
    json_data = [
        {
            "measurement": "speedtest",
            "tags": {
                "client_ip": data['client']['ip'],
                "client_isp": data['client']['isp']
            },

            "time": data['timestamp'],

            "fields": {
                "download": data["download"],
                "upload": data["upload"],
                "ping": data["ping"],
                "url_host": data["server"]["host"],
                "server_lat": data["server"]["lat"],
                "server_lon": data["server"]["lon"],
                "name": data["server"]["name"],
                "server_country": data["server"]["country"],
                "server_cc": data["server"]["cc"],
                "id": data["server"]["id"],
                "server_d": data["server"]["d"],
                "server_latency": data["server"]["latency"],
                "client_ip": data['client']['ip'],
                "client_lat": data['client']['lat'],
                "client_lon": data['client']['lon'],
                "client_isp": data['client']['isp'],
                "client_isprating": data['client']['isprating'],
                "client_rating": data['client']['rating'],
                "client_ispdlavg": data['client']['ispdlavg'],
                "client_ispulavg": data['client']['ispulavg'],
                "client_loggedin": data['client']['loggedin'],
                "client_country": data['client']['country'],
                "timestamp": data['timestamp'],
                "bytes_sent": data['bytes_sent'],
                "bytes_received": data['bytes_received'],
                "share": data['share']
            }
        }
    ]
    return(SUCCESS)


def write_to_db(server, port, user, password, dbname, data):
    db = influxdb.InfluxDBClient(server, port, user, password)
    db_list = db.get_list_database()
    if dbname not in [str(x['name']) for x in db_list]:
        db.create_database(dbname)
    db.switch_database(dbname)
    if not db.write_points(data, time_precision='s', protocol='json'):
        logging.info('Error writing data to the influx.')
        return(FAILED)
    else:
        logging.info('Data written to database %s', (dbname))
        db.close()
        return(SUCCESS)


def main():

    parser = set_command_options()
    options = get_command_options(parser)
    if not options:
        logging.error('Error getting command options.')
        sys.exit('Unable to get command options.  See the log for specifics.')

    conf_file = options['config_file']
    __LOG_NAME__ = options['log_file']

    # TODO(dph) To dynamically change configuration, put this section in the main loop.
    conf = get_config(conf_file)
    if not conf:
        logging.error('Unable to read configuration file: ' + conf_file)
        sys.exit('Unable to read configuration file: ' + conf_file)

    pref_servers = list(map(int, conf['speedtest']['pref_servers'].split()))

    if conf['config']['wait_time'] == "":
        conf['config']['wait_time'] = '12h'
    wait_time = get_wait_time(conf['config']['wait_time'])
    if not wait_time:
        logging.error('Invalid wait time %s', (conf['config']['wait_time']))

    while True:
        s = conn_speedtest()
        if not get_servers(s, pref_servers, conf['speedtest']['any_server']):
            logging.info('Failed to get a server connection to speedtest.')
            logging.info('No data collected or written.')
        else:
            data_points = []
            try:
                logging.info('Starting download test with %s threads.',
                             (conf['speedtest']['down_threads']))
                s.download(threads=int(conf['speedtest']['down_threads']))
            except Exception as err:
                logging.exception(err)

            try:
                logging.info('Starting upload test with %s threads.',
                             (conf['speedtest']['up_threads']))
                s.upload(threads=int(conf['speedtest']['up_threads']))
            except Exception as err:
                logging.exception(err)

            if not create_data_points(s.results.dict(), data_points):
                logging.info(
                    'Failed to create data points from speedtest results.')
            else:
                if not write_to_db(conf['database']['server'], conf['database']['port'], conf['database']['user'],
                                   conf['database']['pwd'], conf['database']['name'], data_points):
                    logging.error('Failed to write datapoints to database.')

        if options['interactive']:
            logging.info('Finished interactive run.')
            break

        logging.info('Waiting %s.', (conf['config']['wait_time']))
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
