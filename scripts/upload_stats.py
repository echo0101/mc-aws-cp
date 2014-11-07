#!/usr/bin/python
import sys,os
import urllib,urllib2
import json
from itsdangerous import JSONWebSignatureSerializer

STATS_LOCATION = "/srv/cloudcraft/cloudcraft/stats"

# parms
# 1- api_key
# 2- target_url

def upload(server, api_key, target_url):
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
    d = {"server": server,"stats":player_stats}
    data = json.dumps({"version":2,"data":s.dumps(d)})
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Content-type': 'application/json',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}
    request = urllib2.Request(target_url, data, headers=headers)
    try:
      response = urllib2.urlopen(request)
      data = response.read()
      try:
        if json.loads(data)["status"] == "ok":
          print "Success"
      except ValueError:
        pass
    except urllib2.HTTPError as e:
      print e.fp.read()

def usage():
  print "upload_stats.py [api_key] [target_url] [server]"

if len(sys.argv) != 4:
  usage()
else:
  upload(sys.argv[1], sys.argv[2], sys.argv[3])
