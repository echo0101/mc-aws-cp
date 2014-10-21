import datetime
import json

from flask.ext.security import login_required, roles_accepted
from flask import request, redirect, url_for, render_template

from minecontrol import app, db
from models import UsageRecord
import aws

@app.route('/')
@login_required
def index():
  return 'Hello World!'

@app.route('/manage')
@roles_accepted('member','admin')
def manage():
  force_update = request.args.get('update') is True
  instances = aws.get_instance_list(force_update)
  inst_summary = [] 
  for i in instances:
    inst_summary.append({
        "iid": i.id,
        "label": i.tags['Name'],
        "state": i.state,
        "ip": i.ip_address,
        "highlight": i.id == request.args.get('iid'),
        "actions": aws.STATE_TRANSITIONS[i.state]
        })

  return render_template("manage.html", instances=inst_summary) 

@app.route('/manage/<iid>', methods=['POST'])
@roles_accepted('member','admin')
def manage_instance(iid):
  action = request.form.get('action')
  instance = aws.get_instance(iid)
  if instance:
    if action in aws.STATE_TRANSITIONS[instance.state]:
      if aws.action(iid, action):
        return redirect(url_for('manage', result="Submitted command: " + action, update=True, iid=iid))
    else:
      return redirect(url_for('manage', result="State change not allowed.", update=True, iid=iid))
  return "Action failed."

@app.route('/api/v1/stats', methods=['POST'])
def api_stats():
  app.logger.info("adding stat record: " + str(request.json))
  record = UsageRecord( \
    timestamp=datetime.datetime.now(), \
    minecraft_account_uuid=request.json['uuid'].replace("-",""), \
    ticks_played=request.json['ticks_played'])
  db.session.add(record)
  db.session.commit()
  return "{\"status\":\"ok\"}"


