#!/bin/sh

set -e

SERVER_DIR=$(dirname $0)/../src/dashboard/server/
cd $SERVER_DIR && ../../../bin/python server.py &
PID=$!
echo "Server running with PID $PID"

trap "echo 'Killing server...'; pkill -P $PID" INT TERM EXIT
while true; do
    sleep 60
done
