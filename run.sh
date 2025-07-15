#!/bin/bash

# Start the TikZ HTTP server in the background
python3 tikz_http_server.py --port ${PUBLIC_PORT:-3000} --log-level INFO --json-response &
TIKZ_PID=$!

# Start the image cleaning script in the background
python3 clean_images.py &
CLEAN_PID=$!

# Wait for any process to exit
wait -n $TIKZ_PID $CLEAN_PID

# Exit with status of the exited process
exit $?