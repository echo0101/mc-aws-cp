#!/usr/bin/python
import sys,os
import urllib,httplib
import json
from itsdangerous import JSONWebSignatureSerializer

STATS_LOCATION = "cloudcraft/stats"

# parms
# 1- api_key
# 2- target_url

def upload(api_key, target_url):
  player_stats = []
  s = JSONWebSignatureSerializer(api_key)
  stats_files = os.listdir(STATS_LOCATION)
  for fn in stats_files:
    if fn.split('.')[1] == "json":
      try:
        fd = open(STATS_LOCATION + '/' + fn)
        data = json.load(fd)
        player_stats.append({
          "uuid": fn.split('.')[0],
          "ticks_played": data["stat.playOneMinute"]
        })
      except ValueError:
        pass
  if len(player_stats) > 0:
    conn = httplib.HTTPConnection(target_url) 
    headers = {"Content-type": "application/json"}
    conn.request("POST", json.dumps({"data":player_stats}), None, headers)
    response = conn.getresponse()
    data = response.read()
    try:
      if json.loads(data)["status"] == "ok":
        print "Success"
    except ValueError:
      pass
    print "Failed"

def usage():
  print "upload_stats.py [api_key] [target_url]"

if len(sys.argv) != 3:
  usage()
else:
  upload(sys.argv[1], sys.argv[2])

