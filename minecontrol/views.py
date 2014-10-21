from minecontrol import app, db
from flask.ext.security import login_required
from flask import request
from models import UsageRecord
import datetime
import json

@app.route('/')
@login_required
def index():
  return 'Hello World!'


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


