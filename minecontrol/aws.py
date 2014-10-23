import itertools
from werkzeug.contrib.cache import SimpleCache
import boto.ec2
from paramiko.client import SSHClient
import datetime
import dateutil.parser

from minecontrol import app, celery

cache = SimpleCache()
conn = None

ACTION_START="Start"
ACTION_STOP="Stop"

STATE_TRANSITIONS = {
    "pending": [],
    "running": [ACTION_STOP],
    "shutting-down": [],
    "terminated": [],
    "stopping": [],
    "stopped": [ACTION_START]
    }

def _do_conn():
  global conn
  conn = boto.ec2.connect_to_region("us-west-2")

def get_instance(iid):
  global conn
  if "Instance:"+iid in map(str,get_instance_list()):
    if None == conn:
      _do_conn()

    instance = conn.get_only_instances(instance_ids=[iid])[0]

    return instance 

def get_instance_list(force_update=False): 
  global cache,conn

  # return if cache-hit
  if not force_update and cache.get('instances'):
    return cache.get('instances')

  retval = []

  if None == conn:
    _do_conn()

  # get all instances that are tagged with aws-mc-cp-enabled
  for i in conn.get_only_instances():
    if 'aws-mc-cp-enabled' in i.tags:
      retval.append(i)

  # cache the result
  cache.set('instances', retval, timeout=60)

  return retval

def stop_instance(instance):
  try:
    stop_script_location = instance.tags['stop_script']
  except KeyError:
    stop_script_location = '~/shutdown.sh' 
  client = SSHClient()
  client.load_system_host_keys()
  client.connect(instance.ip_address, username="ubuntu")
  stdin, stdout, stderr = client.exec_command(stop_script_location + 
      " " + app.config["API_KEY"] + " " + app.config["MY_URL"] + "/api/v1/stats")
  client.close()

def get_time_since_launch(instance):
  time_running = datetime.datetime.now - dateutil.parser.parse(instance.launch_time)
  _minutes, seconds = divmod(time_running.days * 86400 + c.seconds, 60)
  hours, minutes = divmod(_minutes, 60)
  return hours, minutes, seconds

# warning: action is not validated for valid state transition
def action(instance, action):
  iid = instance.id
  if "Instance:"+iid in map(str,get_instance_list()):
    if action == ACTION_START:
      conn.start_instances([iid])
      return True
    elif action == ACTION_STOP:
      #conn.stop_instances([iid])
      return True
  return False

@celery.task
def do_stop(instance):
  stop_instance(instance)
  
