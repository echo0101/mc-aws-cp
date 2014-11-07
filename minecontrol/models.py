from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin
from minecontrol import db
from aws import ACTION_START, ACTION_STOP, ACTION_STOP_CANCEL
import datetime

SERVICE_TWITTER="twitter"
MEMBER_ROLE="member"
ADMIN_ROLE="admin"

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
  id = db.Column(db.Integer(), primary_key=True)
  name = db.Column(db.String(80), unique=True)
  description = db.Column(db.String(255))
  def __str__(self):
    return self.name

  @classmethod
  def getAdminRole(cls):
    return db.session.query(Role).filter(Role.name==ADMIN_ROLE).first()
#if not hasattr(cls,'admin_role'):
#    cls.admin_role = db.session.query(Role).filter(Role.name==ADMIN_ROLE).first()
#  return cls.admin_role

  @classmethod
  def getMemberRole(cls):
    return db.session.query(Role).filter(Role.name==MEMBER_ROLE).first()
#if not hasattr(cls,'member_role'):
#    cls.member_role = db.session.query(Role).filter(Role.name==MEMBER_ROLE).first()
#  return cls.member_role

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
  bills = db.relationship('UserBill', backref='user')

  def __str__(self):
    return self.email

  def timePlayedSinceLast(self):
    usage, ticks = self.sinceLastBill()
    return datetime.timedelta(seconds=ticks)

  def partSinceLast(self):
    members=db.session.query(User).filter(User.roles.contains(Role.getMemberRole())).all()
    return float(self.sinceLastBill()[1])/float(sum(member.sinceLastBill()[1] for member in members))

  # get current usage record, ticks played
  def sinceLastBill(self):
    baseline_ticks = 0
    ticks_played = 0

    # get the last usage that has been billed (if any)
    last_billed_usage = db.session.query(UsageRecord).filter( \
        UsageRecord.minecraft_account_uuid==self.minecraft_account_uuid, \
        UsageRecord.billrecord_id != None).order_by(UsageRecord.timestamp.desc()).first()

    # build query for current usage record
    q = db.session.query(UsageRecord).filter(UsageRecord.minecraft_account_uuid== \
        self.minecraft_account_uuid)

    # if a bill exists, make sure this usage occurs after the bill
    if last_billed_usage:
      baseline_ticks = last_billed_usage.ticks_played
      q.filter(UsageRecord.timestamp > last_billed_usage.timestamp)

    # execute query
    last_usage = q.order_by(UsageRecord.timestamp.desc()).first()

    if last_usage:
      ticks_played = last_usage.ticks_played - baseline_ticks

    return last_usage, ticks_played

class CommandRecord(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  action = db.Column(db.Enum(ACTION_START, ACTION_STOP, ACTION_STOP_CANCEL))

  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class UsageRecord(db.Model):
  __tablename__ = 'usagerecord'
  id = db.Column(db.Integer, primary_key=True)
  timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  minecraft_account_uuid = db.Column(db.String(32))
  ticks_played = db.Column(db.Integer)
  billrecord_id = db.Column(db.Integer, db.ForeignKey('bill.id'))
  server = db.Column(db.String(255))

  def __str__(self):
    return "Usage: %s - %d" % (self.minecraft_account_uuid, self.ticks_played)

class UserBill(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'))
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  ticks_played_period = db.Column(db.Integer)
  paid = db.Column(db.Boolean())

  def getCost(self):
    return self.bill.costCents * self.getPart() 

  def getCostDollars(self):
    return float(self.getCost())/100

  def getPart(self):
    return float(self.ticks_played_period) / float(self.bill.getTotalUsage())

  def timePlayed(self):
    return datetime.timedelta(seconds=self.ticks_played_period/20)

  def __str__(self):
    return "Bill: %s - %d" % (self.user, self.ticks_played_period)

class BillRecord(db.Model):
  __tablename__ = 'bill'
  id = db.Column(db.Integer, primary_key=True)
  endDate = db.Column(db.DateTime, default=datetime.datetime.utcnow)
  costCents = db.Column(db.Integer)
  lastRecords = db.relationship('UsageRecord', backref='bill')
  billsGenerated = db.relationship('UserBill', backref='bill')
  notes = db.Column(db.Text)

  def getTotalUsage(self):
    return sum(bill.ticks_played_period for bill in self.billsGenerated)

  def getCostDollars(self):
    return float(self.costCents)/100

class OAuthToken(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  service = db.Column(db.Enum(SERVICE_TWITTER),unique=True)
  key = db.Column(db.String(255))
  secret = db.Column(db.String(255))

