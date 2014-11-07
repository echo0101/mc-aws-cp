import datetime
import json

from flask.ext.login import current_user
from flask.ext.security import login_required, roles_accepted
from flask_security.utils import encrypt_password
from flask import request, redirect, url_for, render_template, flash, abort

from itsdangerous import JSONWebSignatureSerializer

from wtforms.ext.sqlalchemy.orm import model_form
from wtforms import Form

from minecontrol import app, db, user_datastore, csrf
from forms import ConfirmForm
from models import * 
from util import *
import mojang

import aws

# more views
import tweet

s = None

@app.route('/')
def index():
  return render_template("welcome.html")

@app.route('/manage')
@login_required
@roles_accepted('member','admin')
def manage():
  if request.args.get('result'):
    flash(request.args.get('result'))
  force_update = request.args.get('update') == "True"
  instances = aws.get_instance_list(force_update)
  inst_summary = [] 
  for i in instances:
    state = i.state
    allowed_actions = aws.STATE_TRANSITIONS[i.state]
    if aws.EC2_TAG_SHUTDOWN_JOB in i.tags:
      allowed_actions = [aws.ACTION_STOP_CANCEL]
      state += " (stop scheduled)"
    inst_summary.append({
        "iid": i.id,
        "label": i.tags['Name'],
        "state": state,
        "ip": i.ip_address,
        "uptime": aws.get_time_since_launch(i) if i.state != "stopped" else None,
        "highlight": i.id == request.args.get('iid'),
        "actions": allowed_actions 
        })

  return render_template("manage.html", instances=inst_summary, 
      twitter_user=tweet.get_screen_name()) 

@app.route('/foo')
def make_error():
  foo=foo

@app.route('/manage/<iid>', methods=['POST'])
@login_required
@roles_accepted('member','admin')
def manage_instance(iid):
  action = request.form.get('action')
  instance = aws.get_instance(iid)
  if instance:
    if action in aws.STATE_TRANSITIONS[instance.state] or \
        (aws.EC2_TAG_SHUTDOWN_JOB in instance.tags and aws.ACTION_STOP_CANCEL == action):
      if aws.action(instance, action):
        db.session.add(CommandRecord(action=action,user=current_user))
        db.session.commit()
        return redirect(url_for('manage', result="Submitted command: " + action, update=True, iid=iid))
    else:
      return redirect(url_for('manage', result="State change not allowed.", update=True, iid=iid))
  return "Action failed."

@app.route('/usage')
@login_required
@roles_accepted('member','admin')
def my_usage():
  return render_template("my_usage.html", current_user=current_user)

@app.route('/users')
@login_required
@roles_accepted('admin')
def manage_users():
  users = db.session.query(User).all()
  return render_template("users.html", users=users)

@app.route('/users/<uid>/reset', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def reset_password(uid):
  model = user_datastore.get_user(uid) or abort(404)
  form = ConfirmForm(request.form)
  if request.method == 'POST' and form.validate():
    password = random_pass()
    model.password = encrypt_password(password)
    db.session.add(model)
    db.session.commit()
    flash("Password reset for %s to %s" % (model.email, password))
    return redirect(url_for("manage_users"))
  return render_template("confirm.html", form=form, back="manage_users", 
      prompt="You are about to reset the password for %s" % model.email)

@app.route('/users/<uid>', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def manage_user(uid):
  userForm = model_form(User, base_class=Form, db_session=db.session)
  model = user_datastore.get_user(uid) or abort(404)
  form = userForm(request.form, model)

  if request.method == 'POST' and form.validate():
    valid = True

    # only attempt to update uuid if username has changed and is not empty
    if model.minecraft_username != form.data['minecraft_username'] and \
      form.data['minecraft_username'] != "":
        uuid = mojang.get_uuid(form.data['minecraft_username'])
        if uuid == None:
          flash("Minecraft user not found.")
          valid = False
        else:
          model.minecraft_account_uuid = uuid 

    # continue if form is still valid
    if valid:
      model.email = form.data['email']
      model.active = form.data['active']
      model.roles = form.data['roles']
      model.minecraft_username = form.data['minecraft_username']

      flash("Updated user.")
      db.session.add(model)
      db.session.commit()

      return redirect(url_for("manage_users"))
  return render_template("user.html", form=form, action="Edit")

@app.route('/users/add', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def add_user():
  userForm = model_form(User, base_class=Form, db_session=db.session)
  model = User()
  form = userForm(request.form, model)

  if request.method == 'POST' and form.validate():
    valid = True
    uuid = None 

    # if username was provided, make sure it is valid
    if form.data['minecraft_username'] != "":
      uuid = mojang.get_uuid(form.data['minecraft_username'])
      if uuid == None:
        flash("Minecraft user not found.")
        valid = False

    # only continue if form is still valid
    if valid:
      password = random_pass()
      user_datastore.create_user(
          email=form.data['email'],
          password=password,
          active=form.data['active'],
          minecraft_account_uuid=uuid,
          minecraft_username=form.data['minecraft_username'],
          roles=form.data['roles'])
      db.session.commit()
      flash("Created user. Temporary password is %s"%password)
      return redirect(url_for("manage_users"))

  return render_template("user.html", form=form, action="Add") 

# TODO: remove this
@app.route('/manage/audit')
@login_required
@roles_accepted('audit','admin')
def audit_commands():
  return render_template("commands.html",commands=db.session.query(CommandRecord).all())

@app.route('/manage/usage')
@login_required
@roles_accepted('member','admin')
def audit_usage():
  return render_template("usage.html",records=db.session.query(UsageRecord).all())

@app.route('/bills')
@login_required
@roles_accepted('audit','admin')
def bills():
  return render_template("bills.html", bills=db.session.query(BillRecord).all())

def _process_bill(bid=None):
  bill = BillRecord() if not bid else db.session.query(BillRecord).get(bid) or abort(404)

  billForm = model_form(BillRecord, base_class=Form, db_session=db.session)
  form = billForm(request.form, bill)

  if request.method == 'POST' and form.validate():
    bill.endDate = form.data['endDate']
    bill.costCents = form.data['costCents']
    bill.notes = form.data['notes']

    # if adding generate related records

    # cases: 
    # 1. user has not been billed before, and has not played (current=Null, last=Null)
    # 2. user has not been billed before, played since last (current=Record, last=Null)
    # 3. user has been billed before, played sicne last (current=Record, last=Record)
    # 4. user has been billed before but has not played since last (current=Null, last=Record)
    if None==bid:
      usage_records = []
      user_bills = []
      members=db.session.query(User).filter(User.roles.contains(Role.getMemberRole())).all()
      for member in members:
        app.logger.info("member: %s", member)
        last_usage, ticks_played = member.sinceLastBill()

        # create record if there has been account activity
        if last_usage:
          app.logger.info("appending usage record")
          user_bills.append(UserBill(ticks_played_period=ticks_played,user=member))
          usage_records.append(last_usage)
      bill.lastRecords = usage_records
      bill.billsGenerated = user_bills

      app.logger.info("done.")

    flash("Bill added." if not bid else "Bill updated.")
    db.session.add(bill)
    db.session.commit()

    return redirect(url_for("bills"))
  return render_template("bill.html", form=form, action="Add" if not bid else "Edit", bid=bid)

@app.route('/bills/create', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def add_bill():
  return _process_bill()

@app.route('/bills/<bid>')
@login_required
@roles_accepted('admin', 'member')
def view_bill(bid):
  return render_template("view_bill.html", bill=db.session.query(BillRecord).get(bid))

@app.route('/bills/<bid>/edit', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def edit_bill(bid):
  return _process_bill(bid)

@app.route('/bills/<bid>/delete', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def delete_bill(bid):
  bill = db.session.query(BillRecord).get(bid) or abort(404)
  form = ConfirmForm(request.form)
  if request.method == 'POST' and form.validate():
    db.session.delete(bill)
    db.session.commit()
    flash("Bill record #%s has been deleted." % bid)
    return redirect(url_for("bills"))
  return render_template("confirm.html", form=form, back="bills",
      prompt="You are about to remove a bill record for %s." % str(bill.endDate)) 

@csrf.exempt
@app.route('/api/v1/stats', methods=['POST'])
def api_stats():
  global s

  if request.json['version'] != 2:
    return "{\"status\":\"error\",\"message\":\"incompatible version\"}"

  if s == None:
    s = JSONWebSignatureSerializer(app.config['API_KEY'])

  good = 0
  bad = 0
  d = s.loads(request.json['data'])

  for data in d['stats']:
    if not ('uuid' in data and 'ticks_played' in data):
      bad+=1
    else:
      record = UsageRecord( 
        minecraft_account_uuid=data['uuid'].replace("-",""), 
        ticks_played=data['ticks_played'],
        server=d['server'])
      db.session.add(record)
      good+=1

  db.session.commit()

  if bad > 0:
    app.logger.error("Stats api rejected %d of % records." % (bad, bad+good))
  app.logger.info("Stats api processed %d records. (Rejected %d bad records)" % (good, bad))

  return "{\"status\":\"ok\"}"

