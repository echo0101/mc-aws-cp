import itertools
from werkzeug.contrib.cache import SimpleCache
import boto.ec2
import paramiko
from paramiko.client import SSHClient
import datetime
import dateutil.parser

from minecontrol import app
from mycelery import celery

cache = SimpleCache()
conn = None

EC2_TAG_SHUTDOWN_JOB="shutdownJob"

ACTION_START="Start"
ACTION_STOP="Stop"
ACTION_STOP_CANCEL="CancelShutdown"

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
  conn = boto.ec2.connect_to_region(app.config['AWS_REGION'])

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
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  client.load_system_host_keys()
  client.connect(instance.ip_address, username="ubuntu")
  stdin, stdout, stderr = client.exec_command('%s "%s" "%s"' % (stop_script_location, app.config["API_KEY"], app.config["MY_URL"] + "/api/v1/stats"))
  try:
    for s in [stdin, stdout, stderr]:
      app.logger.info(s.read())
  except IOError:
    pass
  client.close()

def get_time_since_launch(instance):
  time_running = datetime.datetime.utcnow() - dateutil.parser.parse(instance.launch_time).replace(tzinfo=None)
  _minutes, seconds = divmod(time_running.days * 86400 + time_running.seconds, 60)
  hours, minutes = divmod(_minutes, 60)
  return hours, minutes, seconds

# warning: action is not validated for valid state transition
def action(instance, action):
  from tweet import tweet_msg
  iid = instance.id
  if "Instance:"+iid in map(str,get_instance_list()):
    if action == ACTION_START:
      conn.start_instances([iid])
      tweet_msg("Server %s has been started. Join now!" % iid)
      return True
    elif action == ACTION_STOP:
      hours, minutes, seconds = get_time_since_launch(instance)
      time_to_shutdown = 50 - minutes # shutdown 10 minutes before the hours is up
      if time_to_shutdown < 0:
        time_to_shutdown = 0
      app.logger.info("Sched shutdown of inst %s in %d minutes" % (iid, time_to_shutdown))
      res = do_stop.apply_async((iid,),countdown=time_to_shutdown*60) # minutes to seconds
      tweet_msg("Server %s is scheduled for shutdown in %d minutes" % (iid, time_to_shutdown))
      instance.add_tag(EC2_TAG_SHUTDOWN_JOB, res.id)
      return True
    elif action == ACTION_STOP_CANCEL: 
      try:
        task_id = instance.tags[EC2_TAG_SHUTDOWN_JOB]
      except KeyError:
        return False
      celery.control.revoke(task_id, terminate=True)
      instance.remove_tag(EC2_TAG_SHUTDOWN_JOB)
      return True

  return False
  
@celery.task
def do_stop(iid):
  app.logger.info("Shutting down: %s" % iid)
  instance = get_instance(iid)
  stop_instance(instance)
  instance.remove_tag(EC2_TAG_SHUTDOWN_JOB)
