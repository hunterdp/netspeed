# netspeed
Utilities for measuring network upload and download speed and storing the results in InfluxDB.

## Files

### `speedtest_metrics.sh` (Recommended)
A robust shell script that measures network speed and sends the data to an InfluxDB instance. This script is designed to be secure, configurable, and easy to use, making it ideal for running as a cron job. It replaces the older `speedtest.sh` and `run_speedtest.sh` scripts.

**Features:**
*   Securely loads credentials from a configuration file.
*   Parses `speedtest-cli`'s JSON output for reliable results.
*   Checks for dependencies (`speedtest-cli`, `jq`, `curl`).
*   Provides clear logging to a configurable log file.
*   Supports command-line arguments to override configuration.

**Dependencies:**
*   `speedtest-cli`: The command-line interface for testing internet bandwidth.
*   `jq`: A lightweight and flexible command-line JSON processor.
*   `curl`: A tool for transferring data with URLs.

**Configuration:**
Create a configuration file to store your InfluxDB connection details. You can copy the provided example file:
```bash
cp speedtest.conf.example /etc/speedtest.conf
```
Then, edit `/etc/speedtest.conf` with your database details. The script will automatically load this file. Alternatively, you can place the config file elsewhere and specify its path with the `-c` flag.

**Usage:**
```bash
# Basic usage (loads config from /etc/speedtest.conf)
./speedtest_metrics.sh

# Override config with command-line flags
./speedtest_metrics.sh -h my-influx-host.local -d my-database -u user -P pass

# Use a custom config file
./speedtest_metrics.sh -c /path/to/my/speedtest.conf
```

**Command-line Options:**
Run `./speedtest_metrics.sh --help` to see all available options.

---

### `speedtest_influx.py`
This is a more in-depth Python utility that uses the `speedtest-cli` package. It stores a larger variety of information in the InfluxDB database. The configuration information is stored in the `config.json` file.

**Usage:**
```bash
python3 speedtest_influx.py [options] <configfile>
```

**Arguments:**
*   `configfile`: Name of the configuration file (default: `config.json`).
*   `--log`, `--log_level`: Set the logging level [debug info warning error] (default: `info`).
*   `-l`, `--log_file`: Set the logfile name (default: `speedtest_influx.log`).
*   `-o`, `--output`: Output directory to store results files (default: `./`).
*   `-v`, `--version`: Prints the version.
*   `-i`, `--interactive`: Run program once.
*   `-j`, `--json`: Save original JSON data files.

---

### Configuration Files

*   **`speedtest.conf.example`**: An example configuration file for `speedtest_metrics.sh`.
*   **`config.json`**: The configuration file for `speedtest_influx.py`.

---

### Deprecated Scripts
The following scripts have been replaced by `speedtest_metrics.sh` and will be removed in a future version:
*   `speedtest.sh`
*   `run_speedtest.sh`