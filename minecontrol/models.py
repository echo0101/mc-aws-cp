from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin
from minecontrol import db
from aws import ACTION_START, ACTION_STOP
import datetime

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
  id = db.Column(db.Integer(), primary_key=True)
  name = db.Column(db.String(80), unique=True)
  description = db.Column(db.String(255))
  def __str__(self):
    return self.name

class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(255), unique=True)
  password = db.Column(db.String(255))
  active = db.Column(db.Boolean())
  minecraft_account_uuid = db.Column(db.String(32))
  minecraft_username = db.Column(db.String(255))
  roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
  commands = db.relationship('CommandRecord', backref='user')

  def __str__(self):
    return self.email

class CommandRecord(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  action = db.Column(db.Enum(ACTION_START, ACTION_STOP))
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class UsageRecord(db.Model):
  __tablename__ = 'usagerecord'
  id = db.Column(db.Integer, primary_key=True)
  timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  minecraft_account_uuid = db.Column(db.String(32))
  ticks_played = db.Column(db.Integer)
  billrecord_id = db.Column(db.Integer, db.ForeignKey('bill.id'))

class BillRecord(db.Model):
  __tablename__ = 'bill'
  id = db.Column(db.Integer, primary_key=True)
  endDate = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  costCents = db.Column(db.Integer)
  lastRecords = db.relationship('UsageRecord', backref='bill')
  notes = db.Column(db.Text)

