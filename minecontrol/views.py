import datetime
import json

from flask.ext.login import current_user
from flask.ext.security import login_required, roles_accepted
from flask_security.utils import encrypt_password
from flask import request, redirect, url_for, render_template, flash, abort

from itsdangerous import JSONWebSignatureSerializer

from wtforms.ext.sqlalchemy.orm import model_form
from wtforms import Form

from minecontrol import app, db, user_datastore
from models import * 
from util import *
import mojang

import aws

s = None

@app.route('/')
@login_required
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
@login_required
@roles_accepted('member','admin')
def manage_instance(iid):
  action = request.form.get('action')
  instance = aws.get_instance(iid)
  if instance:
    if action in aws.STATE_TRANSITIONS[instance.state]:
      if aws.action(instance, action):
        db.session.add(CommandRecord(action=action,user=current_user))
        db.session.commit()
        return redirect(url_for('manage', result="Submitted command: " + action, update=True, iid=iid))
    else:
      return redirect(url_for('manage', result="State change not allowed.", update=True, iid=iid))
  return "Action failed."

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
  if request.method == 'POST':
    if 'confirm' in request.form and request.form['confirm']:
      password = random_pass()
      model.password = encrypt_password(password)
      db.session.add(model)
      db.session.commit()
      flash("Password reset for %s to %s" % (model.email, password))
      return redirect(url_for("manage_users"))
    else:
      flash("You must check the box")
  return render_template("confirm.html", prompt="You are about to reset the password for %s" % model.email)

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

@app.route('/manage/audit')
@login_required
@roles_accepted('audit','admin')
def audit_commands():
  return render_template("commands.html",commands=db.session.query(CommandRecord).all())

@app.route('/manage/usage')
@login_required
@roles_accepted('member','admin')
def audit_usage():
  pass

@app.route('/bills')
@login_required
@roles_accopted('audit','admin')
def bills():
  return render_template("bills.html", bills=db.session.query(BillRecord).all())

@app.route('/bills/create')
@login_required
@roles_accepted('admin')
def add_bill():
  pass

@app.route('/bills/<id>', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def edit_bill():
  pass

@app.route('/bills/<id>/delete', methods=['GET','POST'])
@login_required
@roles_accepted('admin')
def delete_bill():
  pass

@app.route('/api/v1/stats', methods=['POST'])
def api_stats():
  global s

  if s == None:
    s = JSONWebSignatureSerializer(app.config['API_KEY'])

  good = 0
  bad = 0
  records = s.loads(request.json['data'])

  for data in records:
    if not ('uuid' in data and 'ticks_played' in data):
      bad+=1
    else:
      record = UsageRecord( 
        minecraft_account_uuid=data['uuid'].replace("-",""), 
        ticks_played=data['ticks_played'])
      db.session.add(record)
      good+=1

  db.session.commit()

  app.logger.info("Stats api processed %d records. (Rejected %d bad records)" % (good, bad))

  return "{\"status\":\"ok\"}"

