#!/bin/bash

INFLUXDB_HOST="<your influx server host>"
INFLUXDB_PORT="8086"
DATABASE="speedtest"
USER="<username>"
PASS="<complicated_password>"


#[ ! -f "$L_FILE" ] && touch "$LOG_FILE"

timestamp=$(date +%s%N)
output=$(speedtest-cli --simple --single)
hostname=$(hostname)

line=$(echo -n "$output" | awk '/Ping/ {print "ping=" $2} /Download/ {print "download=" $2 * 1024 * 1024} /Upload/ {print "upload=" $2 * 1024 * 1024}' | tr '\n' ',' | head -c -1)
q="http://$INFLUXDB_HOST:$INFLUXDB_PORT/write?db=$DATABASE&u=$USER&p=$PASS"
curl -XPOST "$q" -d "speedtest,host=$hostname $line $timestamp" >> /dev/null
date=$(date '+%Y-%m-%d %H:%M:%S')

printf "%s %s %s %s %s\n" "$date" "$q" "$hostname" "$line" "$timestamp" >> /tmp/speedtest.log
