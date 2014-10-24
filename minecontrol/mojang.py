import urllib
import urllib2
import json

def get_uuid(username):
  url = 'https://api.mojang.com/profiles/minecraft'
  user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
  headers = { 
      'User-Agent' : user_agent ,
      'Content-Type' : 'application/json'
      }
  req = urllib2.Request(url, json.dumps([username]), headers)
  response = urllib2.urlopen(req)

  users = json.load(response)

  return users[0]["id"] if len(users) > 0 else None


