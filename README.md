# netspeed
Three utilities for measuring the network upload and download speed.  The package *speedtest-cli* needs to be installed. 

## Files

### `speedtest.sh`
A script that help keep track of network speed. Used for testing the upload and download speeds of your connection.
It stores the data into an InfluxDB for further processing.  The script can be used as a cron job.

**Usage:**
```bash
./speedtest.sh -p <influxdb host port> -h <influxdb host> --database <database name>
```

**Arguments:**
* `-p`, `--port`: The port number of the InfluxDB host.
* `-h`, `--host`: The hostname or IP address of the InfluxDB host.
* `--database`: The name of the InfluxDB database.

### `speedtest_influx.py`
This is a more in-depth usage of the speedtest-cli package.  It stores a larger variety of information
in the Influx database.  It can be run interactively or as a crontab job or as a container job.  The 
configuration information is stored in the `config.json` file.

**Usage:**
```bash
python3 speedtest_influx.py [options] <configfile>
```

**Arguments:**
* `configfile`: Name of the configuration file (default: `config.json`).
* `--log`, `--log_level`: Set the logging level [debug info warning error] (default: `info`).
* `-l`, `--log_file`: Set the logfile name (default: `speedtest_influx.log`).
* `-o`, `--output`: Output directory to store results files (default: `./`).
* `-v`, `--version`: Prints the version.
* `-i`, `--interactive`: Run program once.
* `-j`, `--json`: Save original JSON data files.

### `run_speedtest.sh`
Another simple shell script that uses the speedtest-cli package. To use, add your specific influx server and 
other configuration information at the top of the script.

**Note:** This script has no error checking and will store the username and password in the logfile.  Use at your own risk.

**Configuration:**
The following variables must be set at the top of the script:
* `INFLUXDB_HOST`: The hostname or IP address of your InfluxDB server.
* `INFLUXDB_PORT`: The port of your InfluxDB server (default: `8086`).
* `DATABASE`: The name of the InfluxDB database.
* `USER`: The username for InfluxDB authentication.
* `PASS`: The password for InfluxDB authentication.

### `config.json`
This file contains the configuration for `speedtest_influx.py`.

**Structure:**
```json
{
   "database":{
      "server":"example.yourdomain.com",
      "port":"8086",
      "user":"username",
      "pwd":"strongpassword",
      "name":"speedtest"
   },
   "speedtest":{
      "pref_servers": "12345",
      "any_server": "True",
      "language": "en",
      "up_threads": "2",
      "down_threads": "8",
      "keep_json": "False"
   },
   "config": {
      "wait_time": "12h"
   }
}
```

**`database` section:**
* `server`: The hostname or IP address of your InfluxDB server.
* `port`: The port of your InfluxDB server.
* `user`: The username for InfluxDB authentication.
* `pwd`: The password for InfluxDB authentication.
* `name`: The name of the InfluxDB database.

**`speedtest` section:**
* `pref_servers`: A space-separated list of preferred speedtest server IDs.
* `any_server`: If `True`, a random server will be chosen if the preferred servers are not available.
* `language`: The language for the speedtest results.
* `up_threads`: The number of threads to use for the upload test.
* `down_threads`: The number of threads to use for the download test.
* `keep_json`: If `True`, the raw JSON output from speedtest-cli will be saved.

**`config` section:**
* `wait_time`: The time to wait between tests (e.g., `12h`, `30m`, `60s`).