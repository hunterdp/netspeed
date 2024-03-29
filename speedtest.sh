#!/bin/bash

while [[ $# > 0 ]]; do
 key="$1"

 case $key in
 -p|--port)
 INFLUXDB_PORT="$2"
 shift
 ;;
 -h|--host)
 INFLUXDB_HOST="$2"
 shift
 ;;
 --database)
 DATABASE="$2"
 shift
 ;;
 *)
 echo "Unknown option $key"
 ;;
 esac
 shift
done

timestamp=$(date +%s%N)
output=$(speedtest-cli --simple)
hostname=$(hostname)

line=$(echo -n "$output" | awk '/Ping/ {print "ping=" $2} /Download/ {print "download=" $2 * 1000 * 1000} /Upload/ {print "upload=" $2 * 1000 * 1000}' | tr '\n' ',' | head -c -1)
curl -XPOST "http://$INFLUXDB_HOST:$INFLUXDB_PORT/write?db=$DATABASE" -d "speedtest,host=$hostname $line $timestamp"

