from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin
from minecontrol import db, app

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
  id = db.Column(db.Integer(), primary_key=True)
  name = db.Column(db.String(80), unique=True)
  description = db.Column(db.String(255))

class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(255), unique=True)
  password = db.Column(db.String(255))
  active = db.Column(db.Boolean())
  confirmed_at = db.Column(db.DateTime())
  minecraft_account_uuid = db.Column(db.String(32))
  minecraft_username = db.Column(db.String(255))
  roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

class UsageRecord(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  timestamp = db.Column(db.DateTime)
  minecraft_account_uuid = db.Column(db.String(32))
  ticks_played = db.Column(db.Integer)

class BillRecord(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  startDate = db.Column(db.DateTime)
  endDate = db.Column(db.DateTime)
  costCents = db.Column(db.Integer)

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

@app.before_first_request
def dbinit():
  global user_datastore

  # ensure db created
  db.create_all()
  db.session.commit()

  admin = user_datastore.get_user('admin')

  if admin is None:
    admin_user = user_datastore.create_user(email='admin', password=app.config['DEFAULT_ADMIN_PASS'])
    user_datastore.create_role(name='member', description='Member of this server')
    admin_group = user_datastore.create_role(name='admin', \
        description='Administrator of this server')
    user_datastore = user_datastore.add_role_to_user(admin_user, admin_group)
    db.session.commit()
