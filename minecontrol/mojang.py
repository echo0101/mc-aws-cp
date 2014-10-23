import urllib
import urllib2
import json

def get_uuid(username):
  url = 'https://api.mojang.com/profiles/minecraft'
  user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
  data = json.dumps([username])
  headers = { 
      'User-Agent' : user_agent ,
      'Content-Type' : 'application/json'
      }
  req = urllib2.Request(url, data, headers)
  response = urllib2.urlopen(req)

  users = json.load(response)

  if len(users) > 0:
    return users[0]["id"]

  return None


