#!/bin/bash
# ./shutdown.sh [api key] [stats api url]

# stop the server
sudo service cloudcraft stop

# send stats back
cd vanilla-cloudcraft
ptyhon upload_stats.py $1 $2

# shutdown
sudo shutdown -h now
