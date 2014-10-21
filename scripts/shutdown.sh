#!/bin/bash

cd vanilla-cloudcraft
ptyhon upload_stats.py $1 $2

sudo shutdown -h now
