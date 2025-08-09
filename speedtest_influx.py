#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import speedtest
import influxdb
import logging
import json
import os
import argparse
import time

__AUTHOR__ = 'David Hunter'
__VERSION__ = 'beta-2.0'
__TITLE__ = 'speedtest_influx.py'


class SpeedtestInfluxError(Exception):
    """Base exception."""
    pass


class ConfigError(SpeedtestInfluxError):
    """Exception for errors in the configuration file."""
    pass


class SpeedtestError(SpeedtestInfluxError):
    """Exception for errors during the speedtest."""
    pass


def parse_args():
    """Parse command-line arguments."""
    usage = (
        'Retrieves upload/download information from the speedtest '
        'application and logs into InfluxDB.'
    )
    parser = argparse.ArgumentParser(
        prog='speedtest-influx',
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'config_file',
        help='Name of the configuration file.',
        type=str,
        default='config.json'
    )
    parser.add_argument(
        '--log-level',
        dest='log_level',
        action='store',
        type=str,
        default='info',
        choices=['debug', 'info', 'warning', 'error'],
        help='Set the logging level (default: %(default)s)'
    )
    parser.add_argument(
        '-l', '--log-file',
        help='Set the logfile name. (default: %(default)s)',
        action='store',
        type=str,
        default='speedtest_influx.log'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory to store results files. (default: %(default)s)',
        action='store',
        type=str,
        default='./'
    )
    parser.add_argument(
        '-v', '--version',
        help='Prints the version',
        action='version',
        version=__VERSION__
    )
    parser.add_argument(
        '-i', '--interactive',
        help='Run program once.',
        action='store_true'
    )
    parser.add_argument(
        '-j', '--json',
        help='Save original JSON data files.',
        action='store_true'
    )

    return parser.parse_args()


def setup_logging(log_level, log_file):
    """Set up logging."""
    fmt = (
        "%(asctime)-15s %(levelname)-5s %(lineno)5d:%(module)s:"
        "%(funcName)-25s %(message)s"
    )
    level = getattr(logging, log_level.upper())
    logging.basicConfig(filename=log_file, format=fmt, level=level)
    logging.info('Starting %s %s', __TITLE__, __VERSION__)


def get_config(config_file):
    """Load configuration from a JSON file."""
    if not os.path.exists(config_file):
        raise ConfigError(f'Configuration file {config_file} does not exist.')
    with open(config_file) as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f'Error decoding JSON from {config_file}: {e}'
            ) from e
    return config


def validate_config(config):
    """Validate the configuration."""
    required_sections = ['database', 'speedtest', 'config']
    for section in required_sections:
        if section not in config:
            raise ConfigError(
                f'Missing required section "{section}" in config file.'
            )

    required_db_keys = ['server', 'port', 'user', 'pwd', 'name']
    for key in required_db_keys:
        if key not in config['database']:
            raise ConfigError(
                f'Missing required key "{key}" in database config.'
            )

    # Add more validation as needed
    logging.info('Configuration validated successfully.')


def get_wait_time(t):
    """Parse a time string like '12h' into seconds."""
    if not t or len(t) < 2:
        raise ValueError('Invalid time format')

    period = t[-1]
    try:
        duration = int(t[:-1])
    except ValueError:
        raise ValueError(f'Invalid time duration: {t[:-1]}') from None

    if period == 's':
        return duration
    if period == 'm':
        return duration * 60
    if period == 'h':
        return duration * 3600
    if period == 'd':
        return duration * 86400

    raise ValueError(f'Invalid time period: {period}')


def run_speedtest(st, down_threads, up_threads):
    """Run the download and upload speed tests."""
    try:
        logging.info('Starting download test with %s threads.', down_threads)
        st.download(threads=down_threads)
    except Exception as e:
        raise SpeedtestError('Download test failed.') from e

    try:
        logging.info('Starting upload test with %s threads.', up_threads)
        st.upload(threads=up_threads)
    except Exception as e:
        raise SpeedtestError('Upload test failed.') from e

    return st.results.dict()


def create_data_points(data):
    """Create a list of data points for InfluxDB."""
    return [
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


def write_to_db(db_config, data_points):
    """Write data points to InfluxDB."""
    try:
        client = influxdb.InfluxDBClient(
            db_config['server'],
            db_config['port'],
            db_config['user'],
            db_config['pwd'],
            db_config['name']
        )
        db_list = client.get_list_database()
        if db_config['name'] not in [db['name'] for db in db_list]:
            client.create_database(db_config['name'])

        client.write_points(data_points, time_precision='s', protocol='json')
        logging.info('Data written to database %s', db_config['name'])
    except Exception as e:
        raise SpeedtestError(f'Failed to write to InfluxDB: {e}') from e
    finally:
        if 'client' in locals() and client:
            client.close()


def perform_speedtest(config, args):
    """Perform a single speedtest and write results to the database."""
    try:
        st = speedtest.Speedtest()
        pref_servers = list(
            map(int, config['speedtest']['pref_servers'].split())
        )
        st.get_servers(pref_servers)
        st.get_best_server()
        server_url = st.results.dict()['server']['url']
        logging.info('Server url chosen %s', server_url)
    except speedtest.NoMatchedServers:
        logging.warning('Preferred servers not available. Trying any server.')
        if config['speedtest'].get('any_server', 'False').lower() == 'true':
            st.get_servers()
            st.get_best_server()
        else:
            raise SpeedtestError('No suitable servers found.')
    except Exception as e:
        raise SpeedtestError('Failed to connect to Speedtest servers.') from e

    results = run_speedtest(
        st,
        int(config['speedtest']['down_threads']),
        int(config['speedtest']['up_threads'])
    )

    if args.json:
        json_path = os.path.join(
            args.output_dir,
            f'speedtest_{time.strftime("%Y%m%d-%H%M%S")}.json'
        )
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=4)
        logging.info(f'Results saved to {json_path}')

    data_points = create_data_points(results)
    write_to_db(config['database'], data_points)


def main():
    """Main function."""
    args = parse_args()
    try:
        setup_logging(args.log_level, args.log_file)

        if not os.path.isdir(args.output_dir):
            raise ConfigError(
                f'The output directory {args.output_dir} does not exist.'
            )

        config = get_config(args.config_file)
        validate_config(config)

        wait_time = get_wait_time(
            config.get('config', {}).get('wait_time', '12h')
        )

        while True:
            try:
                perform_speedtest(config, args)
            except SpeedtestError as e:
                logging.error(f'Speedtest failed: {e}')

            if args.interactive:
                logging.info('Finished interactive run.')
                break

            wait_time_str = config.get('config', {}).get('wait_time', '12h')
            logging.info('Waiting for %s.', wait_time_str)
            time.sleep(wait_time)

    except (ConfigError, ValueError) as e:
        logging.error(f'Configuration error: {e}')
        sys.exit(1)
    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}', exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
