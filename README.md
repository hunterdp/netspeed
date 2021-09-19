# netspeed
Two utilities for measuring the network upload and download speed.  The package *speedtest-cli* needs to be installed. 

## speedtest.sh 
A script that help keep track of network speed. Used for testing the upload and download speeds of your connection.
It stores the data into an InfluxDB for further processing.  The script can be used as a cron job.  To use:

    ./speedtest.sh -p <influxdb host port> -h <influxdb host> --database <database name>

## speedtest_influx.py
This is a more in-depth usage of the speedtest-cli package.  It stores a larger variety of information
in the Influx database.  It can be run interactively or as a crontab job or as a container job.  The 
configuration information is stored in the config.json file.  