# /usr/bin/python3
# -*- coding: utf-8 -*-
# MIT License

# Copyright (c) 2021 David Hunter

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime
import speedtest
import influxdb 
import logging
import logging.handlers
import sys
import json
import os
import argparse

__AUTHOR__ = 'David Hunter'
__VERSION__ = 'beta-0.5'
__LOG_NAME__ = ''
__TITLE__ = 'speedtest_influx.py'
__DEBUG__ = False


def set_command_options():
    "Sets the command line arguments."
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

    parser.add_argument(
        '-j', '--json', help='Save original JSON data files.', action='store_true')

    return (parser)


def set_logging_level(log_level, log_file):
    global __DEBUG__
    line_sep = '--------------------------------------------------------------------------------'
    fmt = "%(asctime)-15s %(levelname)-5s %(lineno)5d:%(module)s:%(funcName)-25s %(message)s"
    msg = 'Starting ' + __TITLE__ + ' ' + __VERSION__

    if log_level:
        if 'debug' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.DEBUG)
            logging.debug(line_sep)
            logging.debug(msg)
            logging.debug(line_sep)
            __DEBUG__ = True

        elif 'warning' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.WARNING)
            logging.warning(line_sep)
            logging.warning(msg)
            logging.warning(line_sep)

        elif 'error' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.ERROR)
            logging.error(line_sep)
            logging.error(msg)
            logging.error(line_sep)

        elif 'info' in log_level:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.INFO)
            logging.info(line_sep)
            logging.info(msg)
            logging.info(line_sep)

        else:
            logging.basicConfig(filename=log_file,
                                format=fmt, level=logging.INFO)
            logging.error('Invalid debug level.  Exiting the program.')
            print('Invalid debug level.  Exiting the program.')
            sys.exit(1)


def get_command_options(parser):
    args = parser.parse_args()

    log_file = args.log_file
    options = {'log_file': log_file}
    options['log_level'] = args.log_level
    set_logging_level(args.log_level, log_file)

    if args.configfile:
        if os.path.exists(args.configfile):
            options['config_file'] = args.configfile
        else:
            logging.error('Configuration file ' +
                          args.configfile + ' does not exist.  Exiting.')
            print('Configuration file ' + args.configfile + ' does not exist.')
            sys.exit(1)

    if not os.path.isdir(args.output_dir):
        logging.error('The output directory ' +
                      str(args.output_dir) + ' does not exist.  Exiting.')
        print('The output directory ' + str(args.output_dir) + ' does not exist.')
        sys.exit(1)
    else:
        options['output_dir'] = args.output_dir

    if args.json:
        options['json'] = True
    else:
        options['json'] = False

    logging.info(json.dumps(options))
    return (options)

def create_data_points(data):
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
    return(json_data)

def get_config(conf_file):
    if os.path.exists(conf_file):
        with open(conf_file) as json_config_file:
            data = json.load(json_config_file)
    else:
        print(conf_file, "does not exist.")
        exit()
    return(data)


def get_servers(s, pref_servers, any_server):
  try:
    servers = s.get_servers(pref_servers)

  except speedtest.NoMatchedServers:
    print('Servers not found, trying to get all servers.') 
    try:
      if any_server == 'True':
        servers = s.get_servers()

      else:
        print('Servers requested not available, exiting.')
        sys.exit()

    except Exception as err:
      msg = __TITLE__ + ' ' + __VERSION__ + ' failed at ' + str(timestamp())
      logging.error('speedtest failure')
      logging.exception(err)
      sys.exit(msg)

  except Exception as err:
    msg = __TITLE__ + ' ' + __VERSION__ + ' failed at ' + str(timestamp())
    logging.error('speedtest failure')
    logging.exception(err)
    sys.exit(msg)
  return(s)

def conn_speedtest():
  try:
    s = speedtest.Speedtest()
  except Exception as err:
      msg = __TITLE__ + ' ' + __VERSION__ + ' failed at ' + str(timestamp)
      logging.error('speedtest failure')
      logging.exception('Exception caught')
      sys.exit(msg)
  return(s)

def write_to_db(server, port, user, password, dbname, data):
    db = influxdb.InfluxDBClient(server, port, user, password)
    db_list = db.get_list_database()
    if dbname not in [str(x['name']) for x in db_list]:
        db.create_database(dbname)
    db.switch_database(dbname)
    db.write_points(data)
    db.close()
    return(True)

def main():
  parser = set_command_options()
  options = get_command_options(parser)
  CONFIG_FILE = options['config_file']
  __LOG_NAME__ = options['log_file']
  data = get_config(CONFIG_FILE)
  pref_servers = list(map(int,data['speedtest']['pref_servers'].split()))

  s = conn_speedtest()
  get_servers(s, pref_servers, data['speedtest']['any_server'])
  s.get_best_server()
  s.download()
  s.upload()
  data_points = create_data_points(s.results.dict())
  print(json.dumps(data_points))

  write_to_db(data['database']['server'], data['database']['port'], data['database']['user'], 
              data['database']['pwd'], data['database']['name'], data_points)

if __name__ == "__main__":
    main()
