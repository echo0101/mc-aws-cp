#!/bin/bash
# ./shutdown.sh [api key] [stats api url]

#RCON_PASSWORD='password'

# stop the server
#python mcrcon_cli.py -H localhost -p 25575 -P $RCON_PASSWORD -c "stop"

sudo service cloudcraft stop

# send stats back
ptyhon upload_stats.py $1 $2

# shutdown
sudo shutdown -h now
